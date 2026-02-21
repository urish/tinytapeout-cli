import sys
import webbrowser
from pathlib import Path

import click

from tinytapeout.cli.console import console, is_ci, write_step_summary
from tinytapeout.cli.context import detect_context
from tinytapeout.cli.runner import run_librelane_nix, run_precheck, run_tt_tool


@click.group()
def gds():
    """GDS commands - build, view, and validate hardened designs."""
    pass


@gds.command()
@click.option("--project-dir", default=".", help="Project directory.")
@click.option("--no-docker", is_flag=True, help="Do not use Docker for LibreLane.")
@click.option("--nix", is_flag=True, help="Use nix-portable to run LibreLane.")
@click.option(
    "--librelane-version",
    default="3.0.0.dev52",
    show_default=True,
    help="LibreLane version for --nix builds.",
)
@click.option(
    "--no-validate",
    is_flag=True,
    help="Skip precheck validation after hardening.",
)
def build(
    project_dir: str,
    no_docker: bool,
    nix: bool,
    librelane_version: str,
    no_validate: bool,
):
    """Harden the project (generate GDS)."""
    if nix and no_docker:
        console.print("[red]Cannot use --nix and --no-docker together.[/red]")
        sys.exit(2)

    ctx = detect_context(project_dir)

    if not ctx.info_yaml_path.exists():
        console.print("[red]No info.yaml found. Are you in a Tiny Tapeout project directory?[/red]")
        sys.exit(2)

    console.print("[bold]Building GDS...[/bold]\n")

    # Step 1: Create user config
    console.print("Creating user config...")
    result = run_tt_tool(ctx, "--create-user-config")
    if result.returncode != 0:
        console.print("[red]Failed to create user config.[/red]")
        sys.exit(1)

    # Step 2: Harden
    if nix:
        console.print("Hardening design via nix-portable...")
        result = run_librelane_nix(
            ctx,
            version=librelane_version,
            hide_progress=is_ci(),
        )
    else:
        console.print("Hardening design...")
        harden_args = ["--harden"]
        if no_docker:
            harden_args.append("--no-docker")
        result = run_tt_tool(ctx, *harden_args)

    if result.returncode != 0:
        console.print("[red]Hardening failed.[/red]")
        sys.exit(1)

    console.print("[green]Hardening complete.[/green]\n")

    # Step 3: Print warnings and stats
    run_tt_tool(ctx, "--print-warnings")
    result = run_tt_tool(ctx, "--print-stats", "--print-cell-category", capture=True)
    if result.stdout:
        console.print(result.stdout)
        if is_ci():
            write_step_summary(f"## GDS Build Stats\n\n```\n{result.stdout}\n```")

    # Step 4: Validate (unless skipped)
    if not no_validate:
        # Find the GDS file
        gds_files = list(ctx.gds_dir.glob("*.gds")) if ctx.gds_dir.exists() else []
        if gds_files:
            console.print("Running precheck validation...")
            result = run_precheck(ctx, str(gds_files[0]))
            if result.returncode != 0:
                console.print("[red]Precheck validation failed.[/red]")
                sys.exit(1)
            console.print("[green]Precheck validation passed.[/green]")

    # Step 5: Create submission
    console.print("Creating submission...")
    result = run_tt_tool(ctx, "--create-tt-submission")
    if result.returncode != 0:
        console.print("[red]Failed to create submission.[/red]")
        sys.exit(1)

    console.print("\n[green bold]GDS build complete![/green bold]")


@gds.command()
@click.option("--project-dir", default=".", help="Project directory.")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON.")
def stats(project_dir: str, json_output: bool):
    """Print design statistics."""
    ctx = detect_context(project_dir)

    if not ctx.has_gds:
        console.print("[red]No GDS file found. Run 'tt gds build' first.[/red]")
        sys.exit(2)

    result = run_tt_tool(
        ctx, "--print-stats", "--print-cell-summary", capture=json_output
    )

    if json_output and result.stdout:
        console.print(result.stdout)

    if result.returncode != 0:
        console.print("[red]Failed to get stats.[/red]")
        sys.exit(1)


@gds.command()
@click.option("--project-dir", default=".", help="Project directory.")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON.")
def validate(project_dir: str, json_output: bool):
    """Run DRC precheck on the hardened design."""
    ctx = detect_context(project_dir)

    # Find the GDS file
    gds_files = list(ctx.gds_dir.glob("*.gds")) if ctx.gds_dir.exists() else []
    if not gds_files:
        console.print("[red]No GDS file found. Run 'tt gds build' first.[/red]")
        sys.exit(2)

    console.print("[bold]Running precheck validation...[/bold]\n")

    result = run_precheck(ctx, str(gds_files[0]), capture=json_output)

    if json_output and result.stdout:
        console.print(result.stdout)

    if is_ci():
        summary = result.stdout or result.stderr or ""
        if summary:
            write_step_summary(f"## Precheck Results\n\n```\n{summary}\n```")

    if result.returncode != 0:
        console.print("[red]Precheck validation failed.[/red]")
        sys.exit(1)
    else:
        console.print("[green]Precheck validation passed.[/green]")


@gds.group(invoke_without_command=True)
@click.option("--project-dir", default=".", help="Project directory.")
@click.pass_context
def view(click_ctx: click.Context, project_dir: str):
    """View the hardened GDS layout."""
    click_ctx.ensure_object(dict)
    click_ctx.obj["project_dir"] = project_dir
    if click_ctx.invoked_subcommand is None:
        # Default: same as `tt gds view 2d`
        click_ctx.invoke(view_2d, project_dir=project_dir)


@view.command(name="2d")
@click.option("--project-dir", default=".", help="Project directory.")
def view_2d(project_dir: str):
    """Open a 2D PNG render of the layout."""
    ctx = detect_context(project_dir)

    if not ctx.has_gds:
        console.print("[red]No GDS file found. Run 'tt gds build' first.[/red]")
        sys.exit(2)

    console.print("Rendering 2D PNG...")
    result = run_tt_tool(ctx, "--create-png")
    if result.returncode != 0:
        console.print("[red]Failed to render PNG.[/red]")
        sys.exit(1)

    # Try to find and open the PNG
    png_files = list(ctx.project_dir.glob("runs/wokwi/final/gds/*.png"))
    if png_files:
        import subprocess

        subprocess.run(["xdg-open", str(png_files[0])], check=False)
        console.print(f"Opened: {png_files[0]}")
    else:
        console.print("[yellow]PNG rendered but file not found for display.[/yellow]")


@view.command(name="3d")
@click.option("--project-dir", default=".", help="Project directory.")
def view_3d(project_dir: str):
    """Open the 3D GDS viewer in your browser."""
    ctx = detect_context(project_dir)

    # Look for the GDS file to construct the viewer URL
    gds_files = list(ctx.gds_dir.glob("*.gds")) if ctx.gds_dir.exists() else []
    if not gds_files:
        console.print("[red]No GDS file found. Run 'tt gds build' first.[/red]")
        sys.exit(2)

    viewer_url = "https://gds-viewer.tinytapeout.com/"
    console.print(f"Opening 3D viewer: {viewer_url}")
    webbrowser.open(viewer_url)


@view.command(name="klayout")
@click.option("--project-dir", default=".", help="Project directory.")
def view_klayout(project_dir: str):
    """Open the layout in KLayout GUI."""
    ctx = detect_context(project_dir)

    if not ctx.has_gds:
        console.print("[red]No GDS file found. Run 'tt gds build' first.[/red]")
        sys.exit(2)

    console.print("Opening in KLayout...")
    result = run_tt_tool(ctx, "--open-in-klayout")
    if result.returncode != 0:
        console.print("[red]Failed to open in KLayout.[/red]")
        sys.exit(1)
