#!/usr/bin/env python3
"""
DAPR Configuration Validator

Validates DAPR component YAML files and dapr.yaml configuration.
Usage: python validate-config.py [path]
"""
import sys
import os
import yaml
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Valid DAPR component types
VALID_COMPONENT_TYPES = {
    # State stores
    "state.redis", "state.azure.cosmosdb", "state.postgresql", "state.mongodb",
    "state.azure.tablestorage", "state.mysql", "state.cassandra",
    # Pub/Sub
    "pubsub.redis", "pubsub.azure.servicebus.topics", "pubsub.kafka",
    "pubsub.rabbitmq", "pubsub.azure.eventhubs", "pubsub.gcp.pubsub",
    # Secret stores
    "secretstores.azure.keyvault", "secretstores.local.file",
    "secretstores.kubernetes", "secretstores.hashicorp.vault",
    # Bindings
    "bindings.azure.blobstorage", "bindings.azure.eventgrid",
    "bindings.azure.cosmosdb", "bindings.cron", "bindings.http",
    "bindings.kafka", "bindings.rabbitmq", "bindings.redis",
    # Configuration
    "configuration.azure.appconfig", "configuration.redis",
}

# Required metadata fields for common components
REQUIRED_METADATA = {
    "state.redis": ["redisHost"],
    "state.azure.cosmosdb": ["url", "database", "collection"],
    "pubsub.redis": ["redisHost"],
    "pubsub.azure.servicebus.topics": [],  # Connection string or managed identity
    "secretstores.azure.keyvault": ["vaultName"],
    "secretstores.local.file": ["secretsFile"],
}


class ValidationError:
    def __init__(self, file: str, message: str, severity: str = "error"):
        self.file = file
        self.message = message
        self.severity = severity

    def __str__(self):
        icon = "✗" if self.severity == "error" else "⚠"
        return f"{icon} {self.file}: {self.message}"


def validate_yaml_syntax(file_path: Path) -> Tuple[bool, Any, str]:
    """Validate YAML syntax and return parsed content."""
    try:
        with open(file_path, 'r') as f:
            content = yaml.safe_load(f)
        return True, content, ""
    except yaml.YAMLError as e:
        return False, None, str(e)


def validate_component(file_path: Path, content: Dict[str, Any]) -> List[ValidationError]:
    """Validate a DAPR component YAML file."""
    errors = []
    file_name = file_path.name

    # Check apiVersion
    if content.get("apiVersion") != "dapr.io/v1alpha1":
        errors.append(ValidationError(
            file_name,
            f"Invalid apiVersion '{content.get('apiVersion')}'. Expected 'dapr.io/v1alpha1'"
        ))

    # Check kind
    if content.get("kind") != "Component":
        errors.append(ValidationError(
            file_name,
            f"Invalid kind '{content.get('kind')}'. Expected 'Component'"
        ))

    # Check metadata.name
    metadata = content.get("metadata", {})
    name = metadata.get("name")
    if not name:
        errors.append(ValidationError(file_name, "Missing 'metadata.name'"))
    elif not re.match(r"^[a-z][a-z0-9-]*$", name):
        errors.append(ValidationError(
            file_name,
            f"Invalid component name '{name}'. Must be lowercase, alphanumeric with hyphens"
        ))

    # Check spec
    spec = content.get("spec", {})
    if not spec:
        errors.append(ValidationError(file_name, "Missing 'spec' section"))
        return errors

    # Check spec.type
    comp_type = spec.get("type")
    if not comp_type:
        errors.append(ValidationError(file_name, "Missing 'spec.type'"))
    elif comp_type not in VALID_COMPONENT_TYPES:
        errors.append(ValidationError(
            file_name,
            f"Unknown component type '{comp_type}'",
            severity="warning"
        ))

    # Check spec.version
    if not spec.get("version"):
        errors.append(ValidationError(file_name, "Missing 'spec.version'"))

    # Check required metadata
    comp_metadata = spec.get("metadata", [])
    metadata_names = {m.get("name") for m in comp_metadata if isinstance(m, dict)}

    if comp_type in REQUIRED_METADATA:
        for required in REQUIRED_METADATA[comp_type]:
            if required not in metadata_names:
                errors.append(ValidationError(
                    file_name,
                    f"Missing required metadata '{required}' for {comp_type}"
                ))

    # Check for secrets in plain text
    for m in comp_metadata:
        if isinstance(m, dict):
            name = m.get("name", "").lower()
            value = m.get("value", "")

            # Check if it looks like a secret but is not using secretKeyRef
            if any(s in name for s in ["password", "key", "secret", "token", "credential"]):
                if "secretKeyRef" not in m and value:
                    errors.append(ValidationError(
                        file_name,
                        f"'{m.get('name')}' appears to contain a secret. Use 'secretKeyRef' instead of 'value'",
                        severity="warning"
                    ))

    return errors


def validate_dapr_yaml(file_path: Path, content: Dict[str, Any]) -> List[ValidationError]:
    """Validate dapr.yaml configuration file."""
    errors = []
    file_name = file_path.name

    # Check version
    if "version" not in content:
        errors.append(ValidationError(file_name, "Missing 'version' field"))

    # Check apps
    apps = content.get("apps", [])
    if not apps:
        errors.append(ValidationError(file_name, "No apps defined"))
        return errors

    seen_app_ids = set()
    seen_ports = set()

    for i, app in enumerate(apps):
        app_id = app.get("appId")
        if not app_id:
            errors.append(ValidationError(
                file_name,
                f"App at index {i} missing 'appId'"
            ))
        elif app_id in seen_app_ids:
            errors.append(ValidationError(
                file_name,
                f"Duplicate appId '{app_id}'"
            ))
        else:
            seen_app_ids.add(app_id)

        app_port = app.get("appPort")
        if app_port:
            if app_port in seen_ports:
                errors.append(ValidationError(
                    file_name,
                    f"Port {app_port} used by multiple apps",
                    severity="warning"
                ))
            else:
                seen_ports.add(app_port)

    return errors


def find_config_files(base_path: Path) -> Tuple[List[Path], Path | None]:
    """Find all DAPR configuration files."""
    component_files = []
    dapr_yaml = None

    # Look for dapr.yaml
    for name in ["dapr.yaml", "dapr.yml"]:
        path = base_path / name
        if path.exists():
            dapr_yaml = path
            break

    # Look for component files
    components_dir = base_path / "components"
    if components_dir.exists():
        for ext in ["*.yaml", "*.yml"]:
            component_files.extend(components_dir.glob(ext))
            component_files.extend(components_dir.glob(f"**/{ext}"))

    return component_files, dapr_yaml


def main():
    """Main entry point."""
    base_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()

    print(f"\nDARP Configuration Validator")
    print(f"============================")
    print(f"Scanning: {base_path}\n")

    all_errors: List[ValidationError] = []

    # Find configuration files
    component_files, dapr_yaml = find_config_files(base_path)

    # Validate dapr.yaml
    if dapr_yaml:
        print(f"Validating: {dapr_yaml.name}")
        valid, content, error = validate_yaml_syntax(dapr_yaml)
        if not valid:
            all_errors.append(ValidationError(dapr_yaml.name, f"YAML syntax error: {error}"))
        elif content:
            all_errors.extend(validate_dapr_yaml(dapr_yaml, content))
    else:
        print("No dapr.yaml found (optional)")

    # Validate component files
    for comp_file in component_files:
        print(f"Validating: {comp_file.name}")
        valid, content, error = validate_yaml_syntax(comp_file)
        if not valid:
            all_errors.append(ValidationError(comp_file.name, f"YAML syntax error: {error}"))
        elif content:
            all_errors.extend(validate_component(comp_file, content))

    # Print results
    print("\n" + "=" * 50)

    errors = [e for e in all_errors if e.severity == "error"]
    warnings = [e for e in all_errors if e.severity == "warning"]

    if errors:
        print("\nErrors:")
        for e in errors:
            print(f"  {e}")

    if warnings:
        print("\nWarnings:")
        for w in warnings:
            print(f"  {w}")

    total_files = len(component_files) + (1 if dapr_yaml else 0)
    print(f"\nSummary: {total_files} files, {len(errors)} errors, {len(warnings)} warnings")

    if errors:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
