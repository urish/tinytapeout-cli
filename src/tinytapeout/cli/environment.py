import os
import shutil
import subprocess
from dataclasses import dataclass


@dataclass
class ToolInfo:
    name: str
    available: bool
    version: str | None = None
    path: str | None = None


def check_python() -> ToolInfo:
    import sys

    return ToolInfo(
        name="Python",
        available=True,
        version=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        path=sys.executable,
    )


def check_docker() -> ToolInfo:
    path = shutil.which("docker")
    if not path:
        return ToolInfo(name="Docker", available=False)
    try:
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        version = result.stdout.strip().removeprefix("Docker version ").split(",")[0]
        # Check if daemon is running
        daemon_result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        running = daemon_result.returncode == 0
        return ToolInfo(
            name="Docker",
            available=True,
            version=f"{version}{' (running)' if running else ' (not running)'}",
            path=path,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ToolInfo(name="Docker", available=False, path=path)


def check_git() -> ToolInfo:
    path = shutil.which("git")
    if not path:
        return ToolInfo(name="Git", available=False)
    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        version = result.stdout.strip().removeprefix("git version ")
        return ToolInfo(name="Git", available=True, version=version, path=path)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ToolInfo(name="Git", available=False, path=path)


def check_pdk() -> ToolInfo:
    pdk_root = os.environ.get("PDK_ROOT")
    if not pdk_root:
        return ToolInfo(name="PDK", available=False)
    if os.path.isdir(pdk_root):
        # Try to detect which PDKs are installed
        pdks = []
        for name in ["sky130A", "ihp-sg13g2", "gf180mcuD"]:
            if os.path.isdir(os.path.join(pdk_root, name)):
                pdks.append(name)
        return ToolInfo(
            name="PDK",
            available=len(pdks) > 0,
            version=", ".join(pdks) if pdks else "empty",
            path=pdk_root,
        )
    return ToolInfo(name="PDK", available=False, path=pdk_root)


def check_iverilog() -> ToolInfo:
    path = shutil.which("iverilog")
    if not path:
        return ToolInfo(name="iverilog", available=False)
    try:
        result = subprocess.run(
            ["iverilog", "-V"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        # First line: "Icarus Verilog version 13.0 (stable) ()"
        import re

        match = re.search(r"version\s+(\S+)", result.stdout)
        version = match.group(1) if match else "unknown"
        return ToolInfo(name="iverilog", available=True, version=version, path=path)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ToolInfo(name="iverilog", available=False, path=path)


# Minimum iverilog version for gate-level simulation
IVERILOG_MIN_VERSION = "13.0"


def is_ci() -> bool:
    return os.environ.get("CI") == "true" or os.environ.get("GITHUB_ACTIONS") == "true"
