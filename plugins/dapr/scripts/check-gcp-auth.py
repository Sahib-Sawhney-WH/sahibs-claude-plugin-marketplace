#!/usr/bin/env python3
"""
Google Cloud CLI Authentication Validator

Validates gcloud CLI installation and authentication status before GCP deployments.
Used as a PreToolUse hook for gcloud commands.

Usage: python check-gcp-auth.py [--strict]
"""

import subprocess
import sys
import json
import os
from typing import Dict, Any, Tuple


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


def check_gcloud_installed() -> Dict[str, Any]:
    """Check if gcloud CLI is installed."""
    success, output = run_command(["gcloud", "--version"])

    if not success:
        return {
            "installed": False,
            "error": "Google Cloud CLI is not installed",
            "fix": "Install gcloud: https://cloud.google.com/sdk/docs/install"
        }

    # Parse version from first line like "Google Cloud SDK 458.0.1"
    version = "unknown"
    for line in output.split("\n"):
        if "google cloud sdk" in line.lower():
            parts = line.split()
            if len(parts) >= 4:
                version = parts[3]
                break

    return {
        "installed": True,
        "version": version
    }


def check_gcloud_authenticated() -> Dict[str, Any]:
    """Check if user is authenticated with gcloud."""
    # Check active account
    success, output = run_command(["gcloud", "auth", "list", "--format=json"])

    if not success:
        return {
            "authenticated": False,
            "error": "Could not check gcloud authentication",
            "fix": "Run: gcloud auth login"
        }

    try:
        accounts = json.loads(output)
        active_account = None
        for account in accounts:
            if account.get("status") == "ACTIVE":
                active_account = account.get("account")
                break

        if active_account:
            return {
                "authenticated": True,
                "account": active_account
            }

        return {
            "authenticated": False,
            "error": "No active gcloud account",
            "fix": "Run: gcloud auth login"
        }
    except json.JSONDecodeError:
        return {
            "authenticated": False,
            "error": "Could not parse auth list",
            "fix": "Run: gcloud auth login"
        }


def check_gcloud_project() -> Dict[str, Any]:
    """Check if a GCP project is configured."""
    # Check environment variable first
    project = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("GCLOUD_PROJECT")

    if not project:
        # Try to get from gcloud config
        success, output = run_command(["gcloud", "config", "get-value", "project"])
        if success and output and output != "(unset)":
            project = output

    if project:
        return {
            "configured": True,
            "project": project
        }

    return {
        "configured": False,
        "error": "No GCP project configured",
        "fix": "Run: gcloud config set project <PROJECT_ID>  OR  Set GOOGLE_CLOUD_PROJECT"
    }


def check_gcloud_region() -> Dict[str, Any]:
    """Check if a default region/zone is configured."""
    success_region, region = run_command(["gcloud", "config", "get-value", "compute/region"])
    success_zone, zone = run_command(["gcloud", "config", "get-value", "compute/zone"])

    region = region if success_region and region != "(unset)" else None
    zone = zone if success_zone and zone != "(unset)" else None

    if region or zone:
        return {
            "configured": True,
            "region": region,
            "zone": zone
        }

    return {
        "configured": False,
        "warning": "No default region/zone configured",
        "fix": "Run: gcloud config set compute/region <REGION>"
    }


def check_gke_access() -> Dict[str, Any]:
    """Check if user has GKE access (for Kubernetes deployments)."""
    success, output = run_command([
        "gcloud", "container", "clusters", "list",
        "--format=json", "--limit=1"
    ])

    if not success:
        if "PERMISSION_DENIED" in output or "403" in output:
            return {
                "access": False,
                "error": "No GKE access - permissions required for Kubernetes deployments"
            }
        return {
            "access": False,
            "warning": "Could not check GKE access"
        }

    try:
        clusters = json.loads(output)
        return {
            "access": True,
            "has_clusters": len(clusters) > 0
        }
    except json.JSONDecodeError:
        return {
            "access": True,
            "warning": "Could not parse cluster list"
        }


def check_cloud_run_access() -> Dict[str, Any]:
    """Check if user has Cloud Run access."""
    success, output = run_command([
        "gcloud", "run", "services", "list",
        "--format=json", "--limit=1"
    ])

    if not success:
        if "PERMISSION_DENIED" in output or "403" in output:
            return {
                "access": False,
                "warning": "No Cloud Run access"
            }
        return {
            "access": False,
            "warning": "Could not check Cloud Run access"
        }

    return {"access": True}


def validate_for_gcp() -> Dict[str, Any]:
    """Validate environment for GCP deployment."""
    results = {
        "valid": True,
        "checks": [],
        "errors": [],
        "warnings": []
    }

    # Check CLI
    cli_check = check_gcloud_installed()
    results["checks"].append({"name": "Google Cloud CLI", "result": cli_check})
    if not cli_check.get("installed"):
        results["valid"] = False
        results["errors"].append(cli_check.get("error"))
        return results

    # Check authentication
    auth_check = check_gcloud_authenticated()
    results["checks"].append({"name": "GCloud Auth", "result": auth_check})
    if not auth_check.get("authenticated"):
        results["valid"] = False
        results["errors"].append(auth_check.get("error"))
        return results

    # Check project
    project_check = check_gcloud_project()
    results["checks"].append({"name": "GCP Project", "result": project_check})
    if not project_check.get("configured"):
        results["valid"] = False
        results["errors"].append(project_check.get("error"))
        return results

    # Check region (optional)
    region_check = check_gcloud_region()
    results["checks"].append({"name": "GCP Region", "result": region_check})
    if not region_check.get("configured"):
        results["warnings"].append(region_check.get("warning"))

    # Check GKE access (optional)
    gke_check = check_gke_access()
    results["checks"].append({"name": "GKE Access", "result": gke_check})
    if not gke_check.get("access") and gke_check.get("warning"):
        results["warnings"].append(gke_check.get("warning"))

    # Check Cloud Run access (optional)
    run_check = check_cloud_run_access()
    results["checks"].append({"name": "Cloud Run Access", "result": run_check})
    if not run_check.get("access") and run_check.get("warning"):
        results["warnings"].append(run_check.get("warning"))

    return results


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate Google Cloud CLI authentication for DAPR deployments"
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

    args = parser.parse_args()

    # Run validation
    results = validate_for_gcp()

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        # Print errors and warnings
        for error in results.get("errors", []):
            print(f"Error: {error}", file=sys.stderr)

        for warning in results.get("warnings", []):
            print(f"Warning: {warning}", file=sys.stderr)

        if results["valid"]:
            auth = next(
                (c["result"] for c in results["checks"] if c["name"] == "GCloud Auth"),
                {}
            )
            project = next(
                (c["result"] for c in results["checks"] if c["name"] == "GCP Project"),
                {}
            )
            if auth.get("authenticated"):
                print(f"GCP: Authenticated as {auth.get('account', 'unknown')} "
                      f"(project: {project.get('project', 'unknown')})")

    # Exit code
    if args.strict and not results["valid"]:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
