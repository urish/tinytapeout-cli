import click

from tinytapeout.cli.console import console, print_status
from tinytapeout.cli.context import detect_context
from tinytapeout.cli.environment import (
    IVERILOG_MIN_VERSION,
    check_docker,
    check_git,
    check_iverilog,
    check_pdk,
    check_python,
)


@click.command()
@click.option("--project-dir", default=".", help="Project directory to check.")
def doctor(project_dir: str):
    """Check system readiness for Tiny Tapeout development."""
    console.print("[bold]Tiny Tapeout Doctor[/bold]\n")
    all_ok = True

    # Python (requires-python >= 3.11, so if we're running, it's OK)
    py = check_python()
    print_status("OK", f"Python {py.version}")

    # Docker
    docker = check_docker()
    if docker.available:
        print_status("OK", f"Docker {docker.version}")
    else:
        print_status("WARN", "Docker not found", style="yellow")
        all_ok = False

    # Git
    git = check_git()
    if git.available:
        print_status("OK", f"Git {git.version}")
    else:
        print_status("FAIL", "Git not found", style="red")
        all_ok = False

    # Icarus Verilog
    ivl = check_iverilog()
    if ivl.available:
        from packaging.version import Version

        try:
            ver = Version(ivl.version)
            min_ver = Version(IVERILOG_MIN_VERSION)
            if ver >= min_ver:
                print_status("OK", f"iverilog {ivl.version}")
            else:
                print_status(
                    "WARN",
                    f"iverilog {ivl.version} (>= {IVERILOG_MIN_VERSION} recommended for GL sim)",
                    style="yellow",
                )
        except Exception:
            print_status("OK", f"iverilog {ivl.version}")
    else:
        print_status("WARN", "iverilog not found (needed for simulation)", style="yellow")

    # PDK
    pdk = check_pdk()
    if pdk.available:
        print_status("OK", f"PDK installed: {pdk.version}")
    else:
        print_status(
            "WARN",
            "PDK not installed (run 'tt setup sky130' to install)",
            style="yellow",
        )

    # Project detection
    ctx = detect_context(project_dir)
    if ctx.info:
        print_status(
            "INFO",
            f"Project: {ctx.info.title} ({ctx.info_yaml_path})",
            style="blue",
        )
    elif ctx.info_yaml_path.exists() and ctx.info_errors:
        print_status(
            "WARN",
            f"info.yaml found but has errors ({ctx.info_yaml_path})",
            style="yellow",
        )
        for err in ctx.info_errors:
            console.print(f"         {err}")
    elif ctx.info_yaml_path.exists():
        print_status("INFO", f"Project: {ctx.info_yaml_path}", style="blue")
    else:
        print_status("INFO", "No project detected in current directory", style="blue")

    # tt-support-tools
    if ctx.tt_tools_dir:
        print_status("OK", f"tt-support-tools: {ctx.tt_tools_dir}")
        # Verify tt_tool.py can actually run
        import subprocess

        from tinytapeout.cli.context import _tt_tools_python

        tt_python = _tt_tools_python(ctx.tt_tools_dir)
        tt_tool_py = ctx.tt_tools_dir / "tt_tool.py"
        result = subprocess.run(
            [tt_python, str(tt_tool_py), "--help"],
            capture_output=True,
            timeout=10,
        )
        if result.returncode == 0:
            print_status("OK", "tt_tool.py runs successfully")
        else:
            stderr = (
                result.stderr.decode()
                if isinstance(result.stderr, bytes)
                else result.stderr
            )
            print_status(
                "WARN",
                "tt_tool.py failed to run (dependencies may be missing or venv broken)",
                style="yellow",
            )
            if stderr:
                for line in stderr.strip().splitlines()[-3:]:
                    console.print(f"         {line}")
    else:
        print_status(
            "WARN",
            "tt-support-tools not found (will be cloned on first use)",
            style="yellow",
        )

    # GDS
    if ctx.has_gds:
        print_status("OK", "Hardened GDS found")

    console.print()
    if all_ok:
        console.print("[green]All checks passed.[/green]")
    else:
        console.print("[yellow]Some checks need attention.[/yellow]")
