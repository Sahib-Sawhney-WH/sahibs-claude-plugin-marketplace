#!/usr/bin/env python3
"""
AWS CLI Authentication Validator

Validates AWS CLI installation and authentication status before AWS deployments.
Used as a PreToolUse hook for aws commands.

Usage: python check-aws-auth.py [--strict]
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


def check_aws_cli_installed() -> Dict[str, Any]:
    """Check if AWS CLI is installed."""
    success, output = run_command(["aws", "--version"])

    if not success:
        return {
            "installed": False,
            "error": "AWS CLI is not installed",
            "fix": "Install AWS CLI: https://aws.amazon.com/cli/"
        }

    # Parse version from output like "aws-cli/2.15.0 Python/3.11"
    version = "unknown"
    if "/" in output:
        version = output.split("/")[1].split()[0]

    return {
        "installed": True,
        "version": version
    }


def check_aws_credentials() -> Dict[str, Any]:
    """Check if AWS credentials are configured."""
    # Check environment variables
    env_creds = {
        "AWS_ACCESS_KEY_ID": os.environ.get("AWS_ACCESS_KEY_ID"),
        "AWS_SECRET_ACCESS_KEY": os.environ.get("AWS_SECRET_ACCESS_KEY"),
        "AWS_SESSION_TOKEN": os.environ.get("AWS_SESSION_TOKEN"),
        "AWS_PROFILE": os.environ.get("AWS_PROFILE"),
    }

    has_env_creds = bool(env_creds["AWS_ACCESS_KEY_ID"] and env_creds["AWS_SECRET_ACCESS_KEY"])
    has_profile = bool(env_creds["AWS_PROFILE"])

    # Try to get caller identity
    success, output = run_command(["aws", "sts", "get-caller-identity", "--output", "json"])

    if success:
        try:
            identity = json.loads(output)
            return {
                "authenticated": True,
                "account": identity.get("Account", "unknown"),
                "arn": identity.get("Arn", "unknown"),
                "user_id": identity.get("UserId", "unknown"),
                "method": "environment" if has_env_creds else ("profile" if has_profile else "default")
            }
        except json.JSONDecodeError:
            return {
                "authenticated": True,
                "warning": "Could not parse identity details"
            }

    return {
        "authenticated": False,
        "error": "AWS credentials not configured or expired",
        "fix": "Run: aws configure  OR  Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY"
    }


def check_aws_region() -> Dict[str, Any]:
    """Check if AWS region is configured."""
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")

    if region:
        return {
            "configured": True,
            "region": region,
            "source": "environment"
        }

    # Try to get from config
    success, output = run_command(["aws", "configure", "get", "region"])

    if success and output:
        return {
            "configured": True,
            "region": output,
            "source": "config"
        }

    return {
        "configured": False,
        "warning": "No default region configured",
        "fix": "Set AWS_REGION or run: aws configure"
    }


def check_eks_access() -> Dict[str, Any]:
    """Check if user has EKS access (for Kubernetes deployments)."""
    success, output = run_command(["aws", "eks", "list-clusters", "--output", "json"])

    if not success:
        if "AccessDenied" in output:
            return {
                "access": False,
                "error": "No EKS access - permissions required for Kubernetes deployments"
            }
        return {
            "access": False,
            "warning": "Could not check EKS access"
        }

    try:
        clusters = json.loads(output)
        return {
            "access": True,
            "cluster_count": len(clusters.get("clusters", []))
        }
    except json.JSONDecodeError:
        return {
            "access": True,
            "warning": "Could not parse cluster list"
        }


def validate_for_aws() -> Dict[str, Any]:
    """Validate environment for AWS deployment."""
    results = {
        "valid": True,
        "checks": [],
        "errors": [],
        "warnings": []
    }

    # Check CLI
    cli_check = check_aws_cli_installed()
    results["checks"].append({"name": "AWS CLI", "result": cli_check})
    if not cli_check.get("installed"):
        results["valid"] = False
        results["errors"].append(cli_check.get("error"))
        return results

    # Check credentials
    creds_check = check_aws_credentials()
    results["checks"].append({"name": "AWS Credentials", "result": creds_check})
    if not creds_check.get("authenticated"):
        results["valid"] = False
        results["errors"].append(creds_check.get("error"))
        return results

    # Check region
    region_check = check_aws_region()
    results["checks"].append({"name": "AWS Region", "result": region_check})
    if not region_check.get("configured"):
        results["warnings"].append(region_check.get("warning"))

    # Check EKS access (optional)
    eks_check = check_eks_access()
    results["checks"].append({"name": "EKS Access", "result": eks_check})
    if not eks_check.get("access") and eks_check.get("warning"):
        results["warnings"].append(eks_check.get("warning"))

    return results


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate AWS CLI authentication for DAPR deployments"
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
    results = validate_for_aws()

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        # Print errors and warnings
        for error in results.get("errors", []):
            print(f"Error: {error}", file=sys.stderr)

        for warning in results.get("warnings", []):
            print(f"Warning: {warning}", file=sys.stderr)

        if results["valid"]:
            creds = next(
                (c["result"] for c in results["checks"] if c["name"] == "AWS Credentials"),
                {}
            )
            if creds.get("authenticated"):
                print(f"AWS: Authenticated as {creds.get('arn', 'unknown')}")

    # Exit code
    if args.strict and not results["valid"]:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
