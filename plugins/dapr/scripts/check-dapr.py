#!/usr/bin/env python3
"""
DAPR Installation Checker

Checks DAPR CLI and runtime installation status.
Usage: python check-dapr.py
"""
import subprocess
import sys
import json
from typing import Dict, Any, Optional


def run_command(cmd: list) -> tuple[bool, str]:
    """Run a command and return success status and output."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        return result.returncode == 0, result.stdout.strip()
    except FileNotFoundError:
        return False, "Command not found"
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


def check_dapr_cli() -> Dict[str, Any]:
    """Check DAPR CLI installation."""
    success, output = run_command(["dapr", "--version"])
    if success:
        return {
            "installed": True,
            "version": output.split()[-1] if output else "unknown"
        }
    return {"installed": False, "error": output}


def check_dapr_runtime() -> Dict[str, Any]:
    """Check DAPR runtime status."""
    success, output = run_command(["dapr", "status"])
    if success:
        return {
            "initialized": True,
            "status": output
        }
    return {"initialized": False, "error": output}


def check_dapr_components() -> Dict[str, Any]:
    """Check loaded DAPR components."""
    success, output = run_command(["dapr", "components", "-o", "json"])
    if success:
        try:
            components = json.loads(output) if output else []
            return {
                "success": True,
                "count": len(components),
                "components": components
            }
        except json.JSONDecodeError:
            return {"success": False, "error": "Invalid JSON output"}
    return {"success": False, "error": output}


def check_running_apps() -> Dict[str, Any]:
    """Check running DAPR applications."""
    success, output = run_command(["dapr", "list", "-o", "json"])
    if success:
        try:
            apps = json.loads(output) if output else []
            return {
                "success": True,
                "count": len(apps),
                "apps": apps
            }
        except json.JSONDecodeError:
            return {"success": False, "error": "Invalid JSON output"}
    return {"success": False, "error": output}


def check_docker() -> Dict[str, Any]:
    """Check Docker installation (needed for local DAPR)."""
    success, output = run_command(["docker", "--version"])
    if success:
        return {"installed": True, "version": output}
    return {"installed": False, "error": output}


def check_sidecar_health(port: int = 3500) -> Dict[str, Any]:
    """Check DAPR sidecar health endpoint."""
    try:
        import urllib.request
        url = f"http://localhost:{port}/v1.0/healthz"
        with urllib.request.urlopen(url, timeout=5) as response:
            return {
                "healthy": response.status == 200,
                "status": response.status
            }
    except Exception as e:
        return {"healthy": False, "error": str(e)}


def print_status(name: str, status: Dict[str, Any]):
    """Print formatted status."""
    success = status.get("installed", status.get("initialized", status.get("healthy", status.get("success", False))))
    icon = "✓" if success else "✗"
    print(f"  {icon} {name}")

    for key, value in status.items():
        if key in ["installed", "initialized", "healthy", "success"]:
            continue
        if key == "error":
            print(f"      Error: {value}")
        elif key not in ["components", "apps"]:
            print(f"      {key}: {value}")


def main():
    """Main entry point."""
    print("\nDAPR Environment Check")
    print("=" * 50)

    # Check CLI
    print("\n1. DAPR CLI:")
    cli_status = check_dapr_cli()
    print_status("CLI", cli_status)

    if not cli_status.get("installed"):
        print("\n  To install DAPR CLI:")
        print("    Windows: winget install Dapr.CLI")
        print("    macOS:   brew install dapr/tap/dapr-cli")
        print("    Linux:   wget -q https://raw.githubusercontent.com/dapr/cli/master/install/install.sh -O - | /bin/bash")
        sys.exit(1)

    # Check Docker
    print("\n2. Docker:")
    docker_status = check_docker()
    print_status("Docker", docker_status)

    # Check Runtime
    print("\n3. DAPR Runtime:")
    runtime_status = check_dapr_runtime()
    print_status("Runtime", runtime_status)

    if not runtime_status.get("initialized"):
        print("\n  To initialize DAPR runtime:")
        print("    dapr init")
        print("    dapr init -k  (for Kubernetes)")

    # Check Running Apps
    print("\n4. Running Applications:")
    apps_status = check_running_apps()
    if apps_status.get("success"):
        print(f"  ✓ {apps_status['count']} app(s) running")
        for app in apps_status.get("apps", []):
            print(f"      - {app.get('appId', 'unknown')} (port {app.get('appPort', '?')})")
    else:
        print(f"  ✗ Unable to list apps: {apps_status.get('error', 'unknown error')}")

    # Check Sidecar (if apps running)
    if apps_status.get("count", 0) > 0:
        print("\n5. Sidecar Health:")
        sidecar_status = check_sidecar_health()
        print_status("Sidecar", sidecar_status)

    print("\n" + "=" * 50)

    # Summary
    all_ok = (
        cli_status.get("installed", False) and
        runtime_status.get("initialized", False)
    )

    if all_ok:
        print("✓ DAPR environment is ready")
        sys.exit(0)
    else:
        print("✗ DAPR environment needs configuration")
        sys.exit(1)


if __name__ == "__main__":
    main()
