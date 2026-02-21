import sys
from pathlib import Path

import click

from tinytapeout.cli.console import console
from tinytapeout.cli.context import detect_context
from tinytapeout.cli.environment import IVERILOG_MIN_VERSION, check_iverilog
from tinytapeout.cli.runner import run_make


@click.command()
@click.option("--project-dir", default=".", help="Project directory.")
@click.option(
    "--gl",
    is_flag=True,
    help="Run gate-level simulation (requires hardened design).",
)
def test(project_dir: str, gl: bool):
    """Run project tests."""
    ctx = detect_context(project_dir)
    test_dir = ctx.project_dir / "test"

    if not test_dir.exists():
        console.print("[red]No test/ directory found.[/red]")
        sys.exit(2)

    _check_iverilog(gl)

    if gl:
        _run_gl_test(ctx, test_dir)
    else:
        _run_rtl_test(test_dir)


def _check_iverilog(gl: bool):
    """Check that iverilog is installed and warn if outdated for GL sim."""
    ivl = check_iverilog()
    if not ivl.available:
        console.print(
            "[red]iverilog not found. Install it with:[/red]\n"
            "  sudo apt-get install iverilog"
        )
        sys.exit(2)

    if gl:
        from packaging.version import Version

        try:
            if Version(ivl.version) < Version(IVERILOG_MIN_VERSION):
                console.print(
                    f"[yellow]Warning: iverilog {ivl.version} detected, "
                    f">= {IVERILOG_MIN_VERSION} recommended for gate-level simulation.[/yellow]"
                )
        except Exception:
            pass


def _run_rtl_test(test_dir: Path):
    """Run RTL simulation tests."""
    console.print("[bold]Running RTL tests...[/bold]\n")

    result = run_make(str(test_dir), "clean")
    if result.returncode != 0:
        console.print("[red]make clean failed.[/red]")
        sys.exit(1)

    result = run_make(str(test_dir))
    if result.returncode != 0:
        console.print("[red]RTL tests failed.[/red]")
        sys.exit(1)

    if _has_failures(test_dir):
        console.print("[red]RTL tests reported failures.[/red]")
        sys.exit(1)

    console.print("[green]RTL tests passed.[/green]")


def _run_gl_test(ctx, test_dir: Path):
    """Run gate-level simulation tests."""
    # Copy gate-level netlist into test directory
    submission_dir = ctx.project_dir / "tt_submission"
    if not submission_dir.exists():
        console.print(
            "[red]No tt_submission/ directory found. Run 'tt gds build' first.[/red]"
        )
        sys.exit(2)

    netlists = list(submission_dir.glob("*.v"))
    if not netlists:
        console.print(
            "[red]No gate-level netlist found in tt_submission/. "
            "Run 'tt gds build' first.[/red]"
        )
        sys.exit(2)

    console.print("[bold]Running gate-level tests...[/bold]\n")

    dest = test_dir / "gate_level_netlist.v"
    # Concatenate all .v files into one netlist
    with open(dest, "w") as out:
        for v_file in netlists:
            out.write(v_file.read_text())

    # Clean previous results
    results_xml = test_dir / "results.xml"
    if results_xml.exists():
        results_xml.unlink()

    result = run_make(str(test_dir), "clean")
    if result.returncode != 0:
        console.print("[red]make clean failed.[/red]")
        sys.exit(1)

    result = run_make(str(test_dir), env={"GATES": "yes"})
    if result.returncode != 0:
        console.print("[red]Gate-level tests failed.[/red]")
        sys.exit(1)

    if _has_failures(test_dir):
        console.print("[red]Gate-level tests reported failures.[/red]")
        sys.exit(1)

    console.print("[green]Gate-level tests passed.[/green]")


def _has_failures(test_dir: Path) -> bool:
    """Check results.xml for test failures."""
    results_xml = test_dir / "results.xml"
    if not results_xml.exists():
        return False
    content = results_xml.read_text()
    return "failure" in content
