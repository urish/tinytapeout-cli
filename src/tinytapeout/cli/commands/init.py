import re
import subprocess
from pathlib import Path

import click
import yaml

from tinytapeout.cli.console import console

# Template repos per tech (digital Verilog only for now)
TEMPLATE_REPOS: dict[str, str] = {
    "sky130A": "https://github.com/TinyTapeout/ttsky-verilog-template",
    "ihp-sg13g2": "https://github.com/TinyTapeout/ttihp-verilog-template",
}

VALID_TECHS = list(TEMPLATE_REPOS.keys())

# Files where tt_um_example must be replaced with the actual top_module name
RENAME_FILES = [
    "src/project.v",
    "test/tb.v",
]


def _validate_name(ctx, param, value):
    if not re.match(r"^[a-zA-Z][a-zA-Z0-9_]*$", value):
        raise click.BadParameter(
            "Name must start with a letter and contain only letters, digits, and underscores."
        )
    return value


@click.command()
@click.option(
    "--name",
    prompt="Project name",
    help="Project name (used in top_module as tt_um_<name>).",
    callback=_validate_name,
)
@click.option(
    "--tech",
    prompt="Technology",
    type=click.Choice(VALID_TECHS, case_sensitive=True),
    default="sky130A",
    help="PDK technology.",
)
@click.option(
    "--tiles",
    prompt="Tile size",
    type=click.Choice(["1x1", "1x2", "2x2", "3x2", "4x2", "6x2", "8x2"]),
    default="1x1",
    help="Number of tiles.",
)
@click.option(
    "--author",
    prompt="Author",
    help="Project author name.",
)
@click.option(
    "--description",
    prompt="Description",
    default="",
    help="One-line project description.",
)
@click.option(
    "--clock-hz",
    prompt="Clock frequency (Hz)",
    type=int,
    default=0,
    help="Clock frequency in Hz (0 if not applicable).",
)
@click.option(
    "--language",
    prompt="HDL language",
    default="Verilog",
    help="HDL language (Verilog, SystemVerilog, VHDL, Amaranth, etc.).",
)
def init(name, tech, tiles, author, description, clock_hz, language):
    """Create a new Tiny Tapeout project from a template."""
    top_module = f"tt_um_{name}"
    project_dir = Path(top_module)

    if project_dir.exists():
        console.print(f"[red]Directory {project_dir} already exists.[/red]")
        raise SystemExit(1)

    # Clone template
    repo_url = TEMPLATE_REPOS[tech]
    console.print(f"Cloning template from {repo_url} ...")
    result = subprocess.run(
        ["git", "clone", "--depth=1", repo_url, str(project_dir)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        console.print(f"[red]Failed to clone template:[/red]\n{result.stderr}")
        raise SystemExit(2)

    # Patch info.yaml
    _patch_info_yaml(
        project_dir, top_module, tiles, author, description, clock_hz, language
    )

    # Rename tt_um_example in source files
    for rel_path in RENAME_FILES:
        filepath = project_dir / rel_path
        if filepath.exists():
            content = filepath.read_text()
            filepath.write_text(content.replace("tt_um_example", top_module))

    # Remove template .git and init fresh repo
    _reinit_git(project_dir)

    console.print(f"\n[green]Project created at ./{project_dir}[/green]")
    console.print(f"  Top module: [bold]{top_module}[/bold]")
    console.print(f"  Technology: [bold]{tech}[/bold]")
    console.print("\nNext steps:")
    console.print(f"  cd {project_dir}")
    console.print("  tt check")


def _patch_info_yaml(
    project_dir: Path,
    top_module: str,
    tiles: str,
    author: str,
    description: str,
    clock_hz: int,
    language: str,
):
    """Patch the template info.yaml with user-provided values."""
    info_yaml_path = project_dir / "info.yaml"
    with open(info_yaml_path) as f:
        data = yaml.safe_load(f)

    project = data["project"]
    project["title"] = top_module
    project["author"] = author
    project["description"] = description
    project["language"] = language
    project["clock_hz"] = clock_hz
    project["tiles"] = tiles
    project["top_module"] = top_module

    with open(info_yaml_path, "w") as f:
        yaml.dump(
            data, f, default_flow_style=False, sort_keys=False, allow_unicode=True
        )


def _reinit_git(project_dir: Path):
    """Remove template .git and initialize a fresh repository."""
    import shutil

    git_dir = project_dir / ".git"
    if git_dir.exists():
        shutil.rmtree(git_dir)

    subprocess.run(
        ["git", "init"],
        cwd=str(project_dir),
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "add", "."],
        cwd=str(project_dir),
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [
            "git",
            "commit",
            "--no-gpg-sign",
            "-m",
            "Initial commit (from Tiny Tapeout template)",
        ],
        cwd=str(project_dir),
        capture_output=True,
        text=True,
    )
