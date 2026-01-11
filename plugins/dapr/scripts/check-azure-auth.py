#!/usr/bin/env python3
"""
Azure CLI Authentication Validator

Validates Azure CLI installation and authentication status before Azure deployments.
Used as a PreToolUse hook for az commands.

Usage: python check-azure-auth.py [--strict]
"""

import subprocess
import sys
import json
from typing import Dict, Any, Optional, Tuple


def run_command(cmd: list, timeout: int = 30) -> Tuple[bool, str]:
    """Run a command and return success status and output."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        return result.returncode == 0, result.stdout.strip() or result.stderr.strip()
    except FileNotFoundError:
        return False, "Command not found"
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


def check_azure_cli_installed() -> Dict[str, Any]:
    """Check if Azure CLI is installed."""
    success, output = run_command(["az", "--version"])

    if not success:
        return {
            "installed": False,
            "error": "Azure CLI is not installed",
            "fix": "Install Azure CLI: https://docs.microsoft.com/cli/azure/install-azure-cli"
        }

    # Parse version
    version = "unknown"
    for line in output.split("\n"):
        if "azure-cli" in line.lower():
            parts = line.split()
            if len(parts) >= 2:
                version = parts[1]
                break

    return {
        "installed": True,
        "version": version
    }


def check_azure_logged_in() -> Dict[str, Any]:
    """Check if user is logged into Azure."""
    success, output = run_command(["az", "account", "show", "-o", "json"])

    if not success:
        return {
            "logged_in": False,
            "error": "Not logged into Azure",
            "fix": "Run: az login"
        }

    try:
        account = json.loads(output)
        return {
            "logged_in": True,
            "subscription_name": account.get("name", "unknown"),
            "subscription_id": account.get("id", "unknown"),
            "tenant_id": account.get("tenantId", "unknown"),
            "user": account.get("user", {}).get("name", "unknown")
        }
    except json.JSONDecodeError:
        return {
            "logged_in": True,
            "warning": "Could not parse account details"
        }


def check_containerapp_extension() -> Dict[str, Any]:
    """Check if containerapp extension is installed."""
    success, output = run_command(["az", "extension", "list", "-o", "json"])

    if not success:
        return {
            "installed": False,
            "warning": "Could not check extensions"
        }

    try:
        extensions = json.loads(output)
        for ext in extensions:
            if ext.get("name") == "containerapp":
                return {
                    "installed": True,
                    "version": ext.get("version", "unknown")
                }

        return {
            "installed": False,
            "fix": "Run: az extension add --name containerapp --upgrade"
        }
    except json.JSONDecodeError:
        return {
            "installed": False,
            "warning": "Could not parse extension list"
        }


def check_resource_group_access(resource_group: Optional[str] = None) -> Dict[str, Any]:
    """Check if user has access to resource groups."""
    if resource_group:
        success, output = run_command([
            "az", "group", "show",
            "--name", resource_group,
            "-o", "json"
        ])

        if not success:
            return {
                "access": False,
                "error": f"Cannot access resource group: {resource_group}",
                "fix": f"Check permissions or create: az group create -n {resource_group} -l <location>"
            }

        return {"access": True, "resource_group": resource_group}

    # Check general access
    success, output = run_command(["az", "group", "list", "-o", "json", "--query", "[0]"])

    if not success:
        return {
            "access": False,
            "error": "Cannot list resource groups",
            "fix": "Check subscription permissions"
        }

    return {"access": True}


def validate_for_container_apps() -> Dict[str, Any]:
    """Validate environment for Azure Container Apps deployment."""
    results = {
        "valid": True,
        "checks": [],
        "errors": [],
        "warnings": []
    }

    # Check CLI
    cli_check = check_azure_cli_installed()
    results["checks"].append({"name": "Azure CLI", "result": cli_check})
    if not cli_check.get("installed"):
        results["valid"] = False
        results["errors"].append(cli_check.get("error"))
        return results

    # Check login
    login_check = check_azure_logged_in()
    results["checks"].append({"name": "Azure Login", "result": login_check})
    if not login_check.get("logged_in"):
        results["valid"] = False
        results["errors"].append(login_check.get("error"))
        return results

    # Check containerapp extension
    ext_check = check_containerapp_extension()
    results["checks"].append({"name": "Container Apps Extension", "result": ext_check})
    if not ext_check.get("installed"):
        results["warnings"].append("Container Apps extension not installed")
        results["warnings"].append(ext_check.get("fix", "Run: az extension add --name containerapp"))

    # Check resource group access
    rg_check = check_resource_group_access()
    results["checks"].append({"name": "Resource Group Access", "result": rg_check})
    if not rg_check.get("access"):
        results["warnings"].append(rg_check.get("error", "Limited resource group access"))

    return results


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate Azure CLI authentication for DAPR deployments"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with code 1 if validation fails"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )
    parser.add_argument(
        "--resource-group", "-g",
        type=str,
        help="Check access to specific resource group"
    )

    args = parser.parse_args()

    # Run validation
    results = validate_for_container_apps()

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        # Print errors and warnings
        for error in results.get("errors", []):
            print(f"Error: {error}", file=sys.stderr)

        for warning in results.get("warnings", []):
            print(f"Warning: {warning}", file=sys.stderr)

        if results["valid"]:
            login = next(
                (c["result"] for c in results["checks"] if c["name"] == "Azure Login"),
                {}
            )
            if login.get("logged_in"):
                print(f"Azure: Logged in as {login.get('user', 'unknown')} "
                      f"(subscription: {login.get('subscription_name', 'unknown')})")

    # Exit code
    if args.strict and not results["valid"]:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
