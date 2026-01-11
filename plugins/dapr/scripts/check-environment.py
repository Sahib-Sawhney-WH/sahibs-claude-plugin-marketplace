#!/usr/bin/env python3
"""
Cross-Platform DAPR Environment Checker

Performs silent validation of DAPR and cloud CLI installations.
Designed for SessionStart hooks - never blocks the session (always exits 0).
Prints warnings to stderr for visibility without blocking.

Works on: Windows, macOS, Linux
Usage: python check-environment.py [--verbose] [--json]
"""

import subprocess
import sys
import platform
import json
import os
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict


@dataclass
class CheckResult:
    """Result of an environment check."""
    name: str
    installed: bool
    version: Optional[str] = None
    message: Optional[str] = None
    install_hint: Optional[str] = None


def run_command(cmd: List[str], timeout: int = 10) -> Tuple[bool, str]:
    """
    Run a command in a cross-platform manner.

    Args:
        cmd: Command and arguments as list
        timeout: Timeout in seconds

    Returns:
        Tuple of (success, output/error)
    """
    try:
        # Use shell=False for security and cross-platform compatibility
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            # Don't use shell=True to avoid platform-specific issues
        )
        return result.returncode == 0, result.stdout.strip() or result.stderr.strip()
    except FileNotFoundError:
        return False, "Command not found"
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except PermissionError:
        return False, "Permission denied"
    except Exception as e:
        return False, str(e)


def get_install_hint(tool: str) -> str:
    """Get platform-specific installation hint."""
    system = platform.system()

    hints = {
        "dapr": {
            "Windows": "winget install Dapr.CLI",
            "Darwin": "brew install dapr/tap/dapr-cli",
            "Linux": "curl -fsSL https://raw.githubusercontent.com/dapr/cli/master/install/install.sh | bash"
        },
        "az": {
            "Windows": "winget install Microsoft.AzureCLI",
            "Darwin": "brew install azure-cli",
            "Linux": "curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash"
        },
        "aws": {
            "Windows": "msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi",
            "Darwin": "brew install awscli",
            "Linux": "curl https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip -o awscliv2.zip && unzip awscliv2.zip && sudo ./aws/install"
        },
        "gcloud": {
            "Windows": "See https://cloud.google.com/sdk/docs/install",
            "Darwin": "brew install google-cloud-sdk",
            "Linux": "curl https://sdk.cloud.google.com | bash"
        },
        "docker": {
            "Windows": "winget install Docker.DockerDesktop",
            "Darwin": "brew install --cask docker",
            "Linux": "curl -fsSL https://get.docker.com | bash"
        },
        "kubectl": {
            "Windows": "winget install Kubernetes.kubectl",
            "Darwin": "brew install kubectl",
            "Linux": "curl -LO https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl && sudo install kubectl /usr/local/bin/"
        }
    }

    tool_hints = hints.get(tool, {})
    return tool_hints.get(system, f"See documentation for {tool}")


def check_dapr_cli() -> CheckResult:
    """Check DAPR CLI installation."""
    success, output = run_command(["dapr", "--version"])

    if success:
        # Parse version from output like "CLI version: 1.12.0"
        version = "unknown"
        for line in output.split("\n"):
            if "version" in line.lower():
                parts = line.split(":")
                if len(parts) >= 2:
                    version = parts[-1].strip()
                    break
        return CheckResult(
            name="DAPR CLI",
            installed=True,
            version=version,
            message="DAPR CLI is installed"
        )

    return CheckResult(
        name="DAPR CLI",
        installed=False,
        message="DAPR CLI not found",
        install_hint=get_install_hint("dapr")
    )


def check_dapr_runtime() -> CheckResult:
    """Check if DAPR runtime is initialized."""
    success, output = run_command(["dapr", "status"])

    if success:
        return CheckResult(
            name="DAPR Runtime",
            installed=True,
            message="DAPR runtime is initialized"
        )

    return CheckResult(
        name="DAPR Runtime",
        installed=False,
        message="DAPR runtime not initialized. Run: dapr init"
    )


def check_azure_cli() -> CheckResult:
    """Check Azure CLI installation."""
    success, output = run_command(["az", "--version"])

    if success:
        # Parse version from first line like "azure-cli 2.55.0"
        version = "unknown"
        for line in output.split("\n"):
            if "azure-cli" in line.lower():
                parts = line.split()
                if len(parts) >= 2:
                    version = parts[1]
                    break
        return CheckResult(
            name="Azure CLI",
            installed=True,
            version=version,
            message="Azure CLI is installed"
        )

    return CheckResult(
        name="Azure CLI",
        installed=False,
        message="Azure CLI not found (optional, needed for Azure deployments)",
        install_hint=get_install_hint("az")
    )


def check_aws_cli() -> CheckResult:
    """Check AWS CLI installation."""
    success, output = run_command(["aws", "--version"])

    if success:
        # Parse version from output like "aws-cli/2.15.0 Python/3.11"
        version = "unknown"
        if "/" in output:
            version = output.split("/")[1].split()[0]
        return CheckResult(
            name="AWS CLI",
            installed=True,
            version=version,
            message="AWS CLI is installed"
        )

    return CheckResult(
        name="AWS CLI",
        installed=False,
        message="AWS CLI not found (optional, needed for AWS deployments)",
        install_hint=get_install_hint("aws")
    )


def check_gcloud_cli() -> CheckResult:
    """Check Google Cloud CLI installation."""
    success, output = run_command(["gcloud", "--version"])

    if success:
        # Parse version from first line like "Google Cloud SDK 458.0.1"
        version = "unknown"
        for line in output.split("\n"):
            if "google cloud sdk" in line.lower():
                parts = line.split()
                if len(parts) >= 4:
                    version = parts[3]
                    break
        return CheckResult(
            name="Google Cloud CLI",
            installed=True,
            version=version,
            message="Google Cloud CLI is installed"
        )

    return CheckResult(
        name="Google Cloud CLI",
        installed=False,
        message="Google Cloud CLI not found (optional, needed for GCP deployments)",
        install_hint=get_install_hint("gcloud")
    )


def check_docker() -> CheckResult:
    """Check Docker installation."""
    success, output = run_command(["docker", "--version"])

    if success:
        # Parse version from output like "Docker version 24.0.7, build ..."
        version = "unknown"
        if "version" in output.lower():
            parts = output.split()
            for i, part in enumerate(parts):
                if part.lower() == "version":
                    if i + 1 < len(parts):
                        version = parts[i + 1].rstrip(",")
                        break
        return CheckResult(
            name="Docker",
            installed=True,
            version=version,
            message="Docker is installed"
        )

    return CheckResult(
        name="Docker",
        installed=False,
        message="Docker not found (needed for local DAPR development)",
        install_hint=get_install_hint("docker")
    )


def check_kubectl() -> CheckResult:
    """Check kubectl installation."""
    success, output = run_command(["kubectl", "version", "--client", "--short"])

    if not success:
        # Try without --short for newer versions
        success, output = run_command(["kubectl", "version", "--client"])

    if success:
        version = "unknown"
        if "v" in output:
            # Parse version like "Client Version: v1.28.0"
            for part in output.split():
                if part.startswith("v"):
                    version = part
                    break
        return CheckResult(
            name="kubectl",
            installed=True,
            version=version,
            message="kubectl is installed"
        )

    return CheckResult(
        name="kubectl",
        installed=False,
        message="kubectl not found (optional, needed for Kubernetes deployments)",
        install_hint=get_install_hint("kubectl")
    )


def run_all_checks(verbose: bool = False) -> Dict[str, Any]:
    """
    Run all environment checks.

    Args:
        verbose: If True, include optional checks

    Returns:
        Dictionary with all check results
    """
    results = {
        "platform": platform.system(),
        "python_version": platform.python_version(),
        "checks": []
    }

    # Critical checks
    results["checks"].append(asdict(check_dapr_cli()))

    # Check DAPR runtime only if CLI is installed
    if results["checks"][-1]["installed"]:
        results["checks"].append(asdict(check_dapr_runtime()))

    # Docker (important for local development)
    results["checks"].append(asdict(check_docker()))

    # Cloud CLIs (optional but helpful)
    if verbose or os.environ.get("DAPR_PLUGIN_CHECK_ALL", ""):
        results["checks"].append(asdict(check_azure_cli()))
        results["checks"].append(asdict(check_aws_cli()))
        results["checks"].append(asdict(check_gcloud_cli()))
        results["checks"].append(asdict(check_kubectl()))

    return results


def print_results(results: Dict[str, Any], output_json: bool = False):
    """Print check results in human-readable or JSON format."""
    if output_json:
        print(json.dumps(results, indent=2))
        return

    warnings = []

    for check in results["checks"]:
        if not check["installed"]:
            warning = f"{check['name']}: {check['message']}"
            if check.get("install_hint"):
                warning += f"\n  Install: {check['install_hint']}"
            warnings.append(warning)

    # Only print warnings, don't spam with success messages
    for warning in warnings:
        print(f"Warning: {warning}", file=sys.stderr)


def main():
    """Main entry point - designed for SessionStart hooks."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Check DAPR and cloud CLI environment"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Include all optional checks (cloud CLIs, kubectl)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with code 1 if DAPR CLI is not installed"
    )

    args = parser.parse_args()

    results = run_all_checks(verbose=args.verbose)
    print_results(results, output_json=args.json)

    # Check if DAPR CLI is installed (the only critical requirement)
    dapr_check = next(
        (c for c in results["checks"] if c["name"] == "DAPR CLI"),
        None
    )

    if args.strict and dapr_check and not dapr_check["installed"]:
        sys.exit(1)

    # Always exit 0 for hook compatibility (don't block sessions)
    sys.exit(0)


if __name__ == "__main__":
    main()
