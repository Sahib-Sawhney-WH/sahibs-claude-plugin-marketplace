#!/usr/bin/env python3
"""
DAPR Cross-File Dependency Analyzer

Analyzes dependencies across DAPR configuration files to detect:
- Circular dependencies between components
- Missing component references
- Service dependency chains
- Secret store reference validation
- Scope misconfigurations

Usage: python dependency-analyzer.py [--path <config-dir>] [--json] [--strict]
"""

import os
import sys
import json
import argparse
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional
from collections import defaultdict
from dataclasses import dataclass, field

try:
    import yaml
except ImportError:
    print("Error: PyYAML is required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


@dataclass
class Component:
    """Represents a DAPR component."""
    name: str
    component_type: str
    version: str
    file_path: str
    scopes: List[str] = field(default_factory=list)
    secret_refs: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class App:
    """Represents an app in dapr.yaml."""
    app_id: str
    app_port: int
    app_dir: str
    file_path: str


@dataclass
class DependencyGraph:
    """Dependency graph for DAPR components and services."""
    nodes: Dict[str, Component] = field(default_factory=dict)
    edges: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))
    reverse_edges: Dict[str, Set[str]] = field(default_factory=lambda: defaultdict(set))

    def add_node(self, component: Component):
        """Add a component node to the graph."""
        self.nodes[component.name] = component

    def add_edge(self, from_node: str, to_node: str):
        """Add a dependency edge from one component to another."""
        self.edges[from_node].add(to_node)
        self.reverse_edges[to_node].add(from_node)

    def get_dependents(self, node: str) -> Set[str]:
        """Get all components that depend on the given node."""
        return self.reverse_edges.get(node, set())

    def get_dependencies(self, node: str) -> Set[str]:
        """Get all components that the given node depends on."""
        return self.edges.get(node, set())


class DependencyAnalyzer:
    """Analyzes DAPR configuration dependencies."""

    def __init__(self, config_dir: str):
        self.config_dir = Path(config_dir)
        self.components: Dict[str, Component] = {}
        self.apps: Dict[str, App] = {}
        self.graph = DependencyGraph()
        self.issues: List[Dict[str, Any]] = []
        self.warnings: List[Dict[str, Any]] = []

    def analyze(self) -> Dict[str, Any]:
        """Run full dependency analysis."""
        # Load all configurations
        self._load_components()
        self._load_apps()

        # Build dependency graph
        self._build_dependency_graph()

        # Run analyses
        self._detect_circular_dependencies()
        self._validate_secret_references()
        self._validate_scope_references()
        self._validate_service_dependencies()
        self._analyze_component_chains()

        return {
            "components": len(self.components),
            "apps": len(self.apps),
            "issues": self.issues,
            "warnings": self.warnings,
            "graph_summary": self._get_graph_summary()
        }

    def _load_components(self):
        """Load all component YAML files."""
        component_dirs = [
            self.config_dir / "components",
            self.config_dir / "middleware",
            self.config_dir / "bindings",
        ]

        for comp_dir in component_dirs:
            if not comp_dir.exists():
                continue

            for yaml_file in comp_dir.glob("**/*.yaml"):
                self._parse_component_file(yaml_file)
            for yaml_file in comp_dir.glob("**/*.yml"):
                self._parse_component_file(yaml_file)

    def _parse_component_file(self, file_path: Path):
        """Parse a single component YAML file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = yaml.safe_load(f)

            if not content or content.get("kind") != "Component":
                return

            metadata = content.get("metadata", {})
            spec = content.get("spec", {})

            name = metadata.get("name", "")
            if not name:
                return

            # Extract secret references
            secret_refs = []
            for item in spec.get("metadata", []):
                secret_ref = item.get("secretKeyRef", {})
                if secret_ref:
                    secret_refs.append(secret_ref.get("name", ""))

            # Extract scopes
            scopes = metadata.get("scopes", []) or []

            component = Component(
                name=name,
                component_type=spec.get("type", "unknown"),
                version=spec.get("version", "v1"),
                file_path=str(file_path),
                scopes=scopes,
                secret_refs=secret_refs,
                metadata=spec.get("metadata", [])
            )

            self.components[name] = component
            self.graph.add_node(component)

        except yaml.YAMLError as e:
            self.warnings.append({
                "type": "parse_error",
                "file": str(file_path),
                "message": f"YAML parse error: {e}"
            })
        except Exception as e:
            self.warnings.append({
                "type": "load_error",
                "file": str(file_path),
                "message": str(e)
            })

    def _load_apps(self):
        """Load apps from dapr.yaml."""
        dapr_yaml = self.config_dir / "dapr.yaml"

        if not dapr_yaml.exists():
            return

        try:
            with open(dapr_yaml, 'r', encoding='utf-8') as f:
                content = yaml.safe_load(f)

            if not content:
                return

            for app_config in content.get("apps", []):
                app_id = app_config.get("appId", app_config.get("appID", ""))
                if not app_id:
                    continue

                app = App(
                    app_id=app_id,
                    app_port=app_config.get("appPort", 0),
                    app_dir=app_config.get("appDirPath", ""),
                    file_path=str(dapr_yaml)
                )
                self.apps[app_id] = app

        except Exception as e:
            self.warnings.append({
                "type": "dapr_yaml_error",
                "file": str(dapr_yaml),
                "message": str(e)
            })

    def _build_dependency_graph(self):
        """Build dependency graph from components."""
        # Map secret stores
        secret_stores = {
            name: comp for name, comp in self.components.items()
            if "secretstores" in comp.component_type.lower()
        }

        # Add edges for secret dependencies
        for name, comp in self.components.items():
            for secret_ref in comp.secret_refs:
                # Find secret store that provides this secret
                for store_name in secret_stores:
                    # Component depends on its secret store
                    self.graph.add_edge(name, store_name)
                    comp.depends_on.append(store_name)

    def _detect_circular_dependencies(self):
        """Detect circular dependencies using DFS."""
        visited = set()
        rec_stack = set()
        cycles = []

        def dfs(node: str, path: List[str]) -> bool:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in self.graph.get_dependencies(node):
                if neighbor not in visited:
                    if dfs(neighbor, path):
                        return True
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    cycle = path[cycle_start:] + [neighbor]
                    cycles.append(cycle)
                    return True

            path.pop()
            rec_stack.remove(node)
            return False

        for node in self.graph.nodes:
            if node not in visited:
                dfs(node, [])

        for cycle in cycles:
            self.issues.append({
                "type": "circular_dependency",
                "severity": "error",
                "cycle": cycle,
                "message": f"Circular dependency detected: {' -> '.join(cycle)}"
            })

    def _validate_secret_references(self):
        """Validate that secret references point to existing stores."""
        secret_stores = {
            name for name, comp in self.components.items()
            if "secretstores" in comp.component_type.lower()
        }

        for name, comp in self.components.items():
            if "secretstores" in comp.component_type.lower():
                continue  # Skip secret stores themselves

            if comp.secret_refs and not secret_stores:
                self.issues.append({
                    "type": "missing_secret_store",
                    "severity": "error",
                    "component": name,
                    "file": comp.file_path,
                    "message": f"Component '{name}' uses secretKeyRef but no secret store is defined"
                })
            elif comp.secret_refs:
                # Check if referenced secrets exist in any store
                # (This is a simplified check - full validation would require store-specific APIs)
                self.warnings.append({
                    "type": "secret_ref_check",
                    "component": name,
                    "secrets": comp.secret_refs,
                    "message": f"Component '{name}' references secrets: {comp.secret_refs}. Verify these exist in your secret store."
                })

    def _validate_scope_references(self):
        """Validate that component scopes reference existing apps."""
        for name, comp in self.components.items():
            if not comp.scopes:
                continue

            for scope in comp.scopes:
                if self.apps and scope not in self.apps:
                    self.warnings.append({
                        "type": "unknown_scope",
                        "component": name,
                        "scope": scope,
                        "file": comp.file_path,
                        "message": f"Component '{name}' scoped to '{scope}' which is not defined in dapr.yaml"
                    })

    def _validate_service_dependencies(self):
        """Validate service-to-service dependencies from code patterns."""
        # Look for common invoke patterns in app directories
        invoke_pattern = re.compile(
            r'invoke\s*\(\s*["\']([a-zA-Z0-9_-]+)["\']'
        )

        for app_id, app in self.apps.items():
            app_dir = self.config_dir / app.app_dir if app.app_dir else None
            if not app_dir or not app_dir.exists():
                continue

            invoked_services = set()

            # Search Python and JavaScript files for invoke calls
            for pattern in ["**/*.py", "**/*.js", "**/*.ts"]:
                for code_file in app_dir.glob(pattern):
                    try:
                        with open(code_file, 'r', encoding='utf-8') as f:
                            content = f.read()
                            matches = invoke_pattern.findall(content)
                            invoked_services.update(matches)
                    except Exception:
                        continue

            # Check if invoked services exist
            for service_id in invoked_services:
                if service_id not in self.apps and service_id != app_id:
                    self.warnings.append({
                        "type": "unknown_service",
                        "app": app_id,
                        "invoked_service": service_id,
                        "message": f"App '{app_id}' invokes service '{service_id}' which is not defined in dapr.yaml"
                    })

    def _analyze_component_chains(self):
        """Analyze dependency chains for depth warnings."""
        def get_chain_depth(node: str, visited: Set[str]) -> int:
            if node in visited:
                return 0
            visited.add(node)

            deps = self.graph.get_dependencies(node)
            if not deps:
                return 1

            return 1 + max(get_chain_depth(dep, visited.copy()) for dep in deps)

        for name in self.graph.nodes:
            depth = get_chain_depth(name, set())
            if depth > 3:
                self.warnings.append({
                    "type": "deep_dependency_chain",
                    "component": name,
                    "depth": depth,
                    "message": f"Component '{name}' has dependency chain depth of {depth}. Consider simplifying."
                })

    def _get_graph_summary(self) -> Dict[str, Any]:
        """Get summary statistics of the dependency graph."""
        total_edges = sum(len(deps) for deps in self.graph.edges.values())

        # Find most connected components
        connection_counts = {
            name: len(self.graph.edges.get(name, set())) + len(self.graph.reverse_edges.get(name, set()))
            for name in self.graph.nodes
        }

        most_connected = sorted(
            connection_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        return {
            "total_nodes": len(self.graph.nodes),
            "total_edges": total_edges,
            "most_connected": [{"name": n, "connections": c} for n, c in most_connected],
            "isolated_components": [
                name for name, count in connection_counts.items() if count == 0
            ]
        }


def find_config_root(start_path: str) -> Optional[Path]:
    """Find DAPR configuration root by looking for dapr.yaml or components directory."""
    current = Path(start_path).resolve()

    while current != current.parent:
        if (current / "dapr.yaml").exists():
            return current
        if (current / "components").exists():
            return current
        current = current.parent

    return Path(start_path).resolve()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze DAPR configuration dependencies"
    )
    parser.add_argument(
        "--path", "-p",
        type=str,
        default=".",
        help="Path to DAPR configuration directory"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with code 1 if any issues are found"
    )
    parser.add_argument(
        "--warnings-as-errors",
        action="store_true",
        help="Treat warnings as errors in strict mode"
    )

    args = parser.parse_args()

    # Find config root
    config_path = find_config_root(args.path)

    # Run analysis
    analyzer = DependencyAnalyzer(str(config_path))
    results = analyzer.analyze()

    if args.json:
        print(json.dumps(results, indent=2, default=str))
    else:
        # Print summary
        print(f"\nDARP Dependency Analysis")
        print(f"========================")
        print(f"Config path: {config_path}")
        print(f"Components: {results['components']}")
        print(f"Apps: {results['apps']}")
        print()

        # Print issues
        if results['issues']:
            print(f"Issues ({len(results['issues'])}):")
            for issue in results['issues']:
                print(f"  [{issue['severity'].upper()}] {issue['type']}: {issue['message']}")
            print()

        # Print warnings
        if results['warnings']:
            print(f"Warnings ({len(results['warnings'])}):")
            for warning in results['warnings']:
                print(f"  [WARN] {warning['type']}: {warning['message']}")
            print()

        # Print graph summary
        summary = results['graph_summary']
        if summary['most_connected']:
            print("Most connected components:")
            for item in summary['most_connected']:
                print(f"  - {item['name']}: {item['connections']} connections")

        if summary['isolated_components']:
            print(f"\nIsolated components (no dependencies): {', '.join(summary['isolated_components'])}")

        # Final status
        if not results['issues'] and not results['warnings']:
            print("\nNo issues found.")

    # Exit code
    has_issues = bool(results['issues'])
    has_warnings = bool(results['warnings'])

    if args.strict:
        if has_issues or (args.warnings_as_errors and has_warnings):
            sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
