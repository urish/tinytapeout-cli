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

# Text file extensions to scan for tt_um_example replacement
_TEXT_EXTENSIONS = {".v", ".sv", ".yaml", ".yml", ".md", ".py", ".json", ".txt", ".tcl"}


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

    # Replace tt_um_example with actual top_module in all text files
    _replace_in_tree(project_dir, "tt_um_example", top_module)

    # Remove template .git and init fresh repo
    _reinit_git(project_dir)

    console.print(f"\n[green]Project created at ./{project_dir}[/green]")
    console.print(f"  Top module: [bold]{top_module}[/bold]")
    console.print(f"  Technology: [bold]{tech}[/bold]")
    console.print("\nNext steps:")
    console.print(f"  cd {project_dir}")
    console.print("  tt check")


def _replace_in_tree(root: Path, old: str, new: str):
    """Replace `old` with `new` in all text files under `root`."""
    for path in root.rglob("*"):
        if path.is_file() and path.suffix in _TEXT_EXTENSIONS:
            content = path.read_text(errors="ignore")
            if old in content:
                path.write_text(content.replace(old, new))


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

    def _git(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
        )

    _git("init")
    _git("add", ".")
    result = _git(
        "commit", "-m", "Initial commit (from Tiny Tapeout template)"
    )
    if result.returncode != 0:
        console.print(
            "[dim]Hint: set git user.name and user.email to create an initial commit.[/dim]"
        )
