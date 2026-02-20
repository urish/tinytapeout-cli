import sys

import click

from tinytapeout.cli.console import console, is_ci, print_status, write_step_summary
from tinytapeout.cli.context import detect_context
from tinytapeout.project_checks import check_info_md, check_info_yaml


@click.command()
@click.option("--project-dir", default=".", help="Project directory to check.")
def check(project_dir: str):
    """Validate info.yaml and docs/info.md."""
    ctx = detect_context(project_dir)

    if not ctx.info_yaml_path.exists():
        console.print("[red]No info.yaml found. Are you in a Tiny Tapeout project directory?[/red]")
        sys.exit(2)

    tt_dir = ctx.require_tt_tools()

    console.print("[bold]Checking project...[/bold]\n")

    info_yaml_errors = check_info_yaml(str(ctx.project_dir), ctx.tech, tt_dir)
    info_md_errors = check_info_md(str(ctx.project_dir))

    # Display results
    if not info_yaml_errors:
        print_status("OK", "info.yaml is valid")
    else:
        print_status("FAIL", "info.yaml has errors:", style="red")
        for error in info_yaml_errors:
            console.print(f"       - {error}")

    if not info_md_errors:
        print_status("OK", "docs/info.md is valid")
    else:
        print_status("FAIL", "docs/info.md has errors:", style="red")
        for error in info_md_errors:
            console.print(f"       - {error}")

    all_errors = info_yaml_errors + info_md_errors

    # Write step summary for CI
    if is_ci() and all_errors:
        lines = ["## Project Check Results\n"]
        if info_yaml_errors:
            lines.append("### info.yaml errors\n")
            for e in info_yaml_errors:
                lines.append(f"- {e}")
        if info_md_errors:
            lines.append("\n### docs/info.md errors\n")
            for e in info_md_errors:
                lines.append(f"- {e}")
        write_step_summary("\n".join(lines))

    console.print()
    if all_errors:
        console.print(f"[red]Found {len(all_errors)} error(s).[/red]")
        sys.exit(1)
    else:
        console.print("[green]All checks passed.[/green]")
