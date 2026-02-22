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


def run_precheck(
    ctx: ProjectContext,
    gds_path: str,
    *args: str,
    capture: bool = False,
) -> subprocess.CompletedProcess:
    """Run precheck.py with the given arguments."""
    tt_dir = ctx.require_tt_tools()

    precheck_script = tt_dir / "precheck" / "precheck.py"
    if not precheck_script.exists():
        from tinytapeout.cli.console import console

        console.print(
            f"[red]Precheck script not found at {precheck_script}.[/red]\n"
            "Try updating tt-support-tools: git -C tt pull"
        )
        raise SystemExit(2)

    cmd = [_tt_tools_python(tt_dir), str(precheck_script)]
    cmd.extend(["--gds", gds_path])
    cmd.extend(["--tech", ctx.tech])
    cmd.extend(args)
    return subprocess.run(
        cmd, capture_output=capture, text=True, env=_tt_tools_env(tt_dir)
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
