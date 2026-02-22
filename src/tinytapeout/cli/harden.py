"""Hardening logic — calls LibreLane directly instead of going through tt_tool.py."""

import json
import os
import shutil
import subprocess
from pathlib import Path

from tinytapeout.cli.context import ProjectContext, _tt_tools_python
from tinytapeout.cli.runner import _tt_tools_env
from tinytapeout.tech import tech_map


def run_harden(ctx: ProjectContext, *, no_docker: bool = False) -> None:
    """Run LibreLane hardening directly, bypassing tt_tool.py --harden."""
    project_dir = ctx.project_dir
    tt_dir = ctx.require_tt_tools()
    tech = tech_map[ctx.tech]

    # Collect git metadata (for commit_id.json — does not affect the design)
    repo_url = _get_git_remote_url(project_dir)
    commit_hash = _get_git_commit_hash(project_dir)
    tt_version = _get_tt_tools_version(tt_dir)
    workflow_url = _get_workflow_url()

    # Merge configs
    _create_merged_config(project_dir)

    # Clean and create run directory
    run_dir = project_dir / "runs" / "wokwi"
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    # Build LibreLane command
    python = _tt_tools_python(tt_dir)
    cmd: list[str] = [python, "-m", "librelane"]

    pdk_root = os.environ.get("PDK_ROOT")

    if not no_docker:
        if pdk_root:
            cmd.extend(["--pdk-root", pdk_root])
        cmd.extend(["--docker-no-tty", "--dockerized"])

    if pdk_root:
        cmd.extend(["--pdk-root", pdk_root])

    if tech.librelane_pdk_args:
        cmd.extend(tech.librelane_pdk_args.split())

    cmd.extend(["--run-tag", "wokwi"])
    cmd.extend(["--force-run-dir", str(run_dir)])

    if os.environ.get("CI"):
        cmd.append("--hide-progress-bar")

    cmd.append(str(project_dir / "src" / "config_merged.json"))

    # Run LibreLane
    env = _tt_tools_env(tt_dir)
    result = subprocess.run(cmd, env=env)
    if result.returncode != 0:
        raise SystemExit(1)

    # Write commit_id.json
    final_dir = run_dir / "final"
    commit_id_data = {
        "app": f"Tiny Tapeout {tt_version}",
        "repo": repo_url,
        "commit": commit_hash,
        "workflow_url": workflow_url,
    }
    with open(final_dir / "commit_id.json", "w") as f:
        json.dump(commit_id_data, f, indent=2)
        f.write("\n")

    # Write pdk.json from resolved.json
    with open(run_dir / "resolved.json") as f:
        ll_config = json.load(f)
    librelane_version = ll_config["meta"]["librelane_version"]
    pdk_version_info = tech.read_pdk_version(ll_config["PDK_ROOT"])
    pdk_json = {
        "FLOW_NAME": "LibreLane",
        "FLOW_VERSION": librelane_version,
        "PDK": ll_config["PDK"],
        "PDK_SOURCE": pdk_version_info["source"],
        "PDK_VERSION": pdk_version_info["version"],
    }
    with open(run_dir / "pdk.json", "w") as f:
        json.dump(pdk_json, f, indent=2)


# ---------------------------------------------------------------------------
# Git metadata helpers (plain subprocess, no GitPython dependency)
# ---------------------------------------------------------------------------


def _get_git_remote_url(project_dir: Path) -> str:
    """Get the origin remote URL, falling back to 'unknown'."""
    result = subprocess.run(
        ["git", "-C", str(project_dir), "remote", "get-url", "origin"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def _get_git_commit_hash(project_dir: Path) -> str:
    """Get the current HEAD commit hash."""
    result = subprocess.run(
        ["git", "-C", str(project_dir), "rev-parse", "HEAD"],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def _get_tt_tools_version(tt_tools_dir: Path) -> str:
    """Get the tt-support-tools version string (branch/tag + short hash)."""
    # Get branch name
    result = subprocess.run(
        ["git", "-C", str(tt_tools_dir), "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True,
        text=True,
    )
    ref = result.stdout.strip() if result.returncode == 0 else "unknown"
    if ref == "HEAD":
        # Detached HEAD — try describe
        result = subprocess.run(
            ["git", "-C", str(tt_tools_dir), "describe", "--tags", "--always"],
            capture_output=True,
            text=True,
        )
        ref = result.stdout.strip() if result.returncode == 0 else "(detached)"

    # Get short hash
    result = subprocess.run(
        ["git", "-C", str(tt_tools_dir), "rev-parse", "--short=8", "HEAD"],
        capture_output=True,
        text=True,
    )
    short_hash = result.stdout.strip() if result.returncode == 0 else "unknown"

    return f"{ref} {short_hash}"


def _get_workflow_url() -> str | None:
    """Build GitHub Actions workflow URL from environment variables."""
    server = os.environ.get("GITHUB_SERVER_URL")
    repo = os.environ.get("GITHUB_REPOSITORY")
    run_id = os.environ.get("GITHUB_RUN_ID")
    if server and repo and run_id:
        return f"{server}/{repo}/actions/runs/{run_id}"
    return None


# ---------------------------------------------------------------------------
# Config merging
# ---------------------------------------------------------------------------


def _create_merged_config(project_dir: Path) -> None:
    """Merge src/config.json and src/user_config.json into src/config_merged.json."""
    src_dir = project_dir / "src"

    with open(src_dir / "config.json") as f:
        config = json.load(f)
    config.pop("//", None)

    with open(src_dir / "user_config.json") as f:
        user_config = json.load(f)
    user_config.pop("//", None)

    config.update(user_config)

    with open(src_dir / "config_merged.json", "w") as f:
        json.dump(config, f, indent=2)
