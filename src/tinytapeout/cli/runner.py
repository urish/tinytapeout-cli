import os
import subprocess
from pathlib import Path

from tinytapeout.cli.context import ProjectContext, _tt_tools_python


def _tt_tools_env(tt_dir: Path) -> dict[str, str]:
    """Build an environment with the tt-support-tools venv bin on PATH."""
    env = os.environ.copy()
    venv_bin = tt_dir / ".venv" / "bin"
    if venv_bin.is_dir():
        env["PATH"] = str(venv_bin) + os.pathsep + env.get("PATH", "")
    return env


def run_tt_tool(
    ctx: ProjectContext,
    *args: str,
    capture: bool = False,
) -> subprocess.CompletedProcess:
    """Run tt_tool.py with the given arguments."""
    tt_dir = ctx.require_tt_tools()

    cmd = [_tt_tools_python(tt_dir), str(tt_dir / "tt_tool.py")]
    cmd.extend(["--project-dir", str(ctx.project_dir)])
    if ctx.tech == "ihp-sg13g2":
        cmd.append("--ihp")
    elif ctx.tech == "gf180mcuD":
        cmd.append("--gf")
    cmd.extend(args)
    return subprocess.run(
        cmd, capture_output=capture, text=True, env=_tt_tools_env(tt_dir)
    )


def _install_precheck_deps(tt_dir: Path) -> None:
    """Install precheck Python dependencies into the tt-support-tools venv."""
    from tinytapeout.cli.console import console

    req_file = tt_dir / "precheck" / "requirements.txt"
    if not req_file.exists():
        return

    venv_python = tt_dir / ".venv" / "bin" / "python"
    if not venv_python.exists():
        return

    # Fast path: check if deps are already satisfied
    result = subprocess.run(
        [str(venv_python), "-m", "pip", "install", "--dry-run", "-r", str(req_file)],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0 and "Would install" not in result.stdout:
        return

    console.print("Installing precheck dependencies ...")
    result = subprocess.run(
        [str(venv_python), "-m", "pip", "install", "-r", str(req_file)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        console.print(
            f"[red]Failed to install precheck dependencies:[/red]\n{result.stderr}"
        )
        raise SystemExit(2)
    console.print("Done.\n")


def run_precheck(
    ctx: ProjectContext,
    gds_path: str,
    *args: str,
    runner: str = "auto",
    capture: bool = False,
) -> subprocess.CompletedProcess:
    """Run precheck.py with the given arguments."""
    from tinytapeout.cli.precheck_env import detect_precheck_env, wrap_command

    tt_dir = ctx.require_tt_tools()

    precheck_script = tt_dir / "precheck" / "precheck.py"
    if not precheck_script.exists():
        from tinytapeout.cli.console import console

        console.print(
            f"[red]Precheck script not found at {precheck_script}.[/red]\n"
            "Try updating tt-support-tools: git -C tt pull"
        )
        raise SystemExit(2)

    # Install precheck Python deps into the venv
    _install_precheck_deps(tt_dir)

    # Detect execution environment
    env_info = detect_precheck_env(tt_dir, runner)

    precheck_dir = tt_dir / "precheck"
    cmd = [_tt_tools_python(tt_dir), str(precheck_script)]
    cmd.extend(["--gds", gds_path])
    cmd.extend(["--tech", ctx.tech])
    cmd.extend(args)

    # Wrap command for the detected environment (e.g. nix-shell)
    cmd = wrap_command(env_info, cmd)

    env = _tt_tools_env(tt_dir)
    env["PDK"] = ctx.tech  # precheck reads PDK env var at module level
    return subprocess.run(
        cmd,
        cwd=str(precheck_dir),
        capture_output=capture,
        text=True,
        env=env,
    )


def run_make(
    directory: str,
    *args: str,
    env: dict[str, str] | None = None,
    capture: bool = False,
) -> subprocess.CompletedProcess:
    """Run make in the given directory."""
    cmd = ["make", "-C", directory]
    cmd.extend(args)

    run_env = os.environ.copy()
    if env:
        run_env.update(env)

    return subprocess.run(cmd, capture_output=capture, text=True, env=run_env)
