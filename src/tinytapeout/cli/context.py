import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml

from tinytapeout.project_info import ProjectInfo, ProjectYamlError
from tinytapeout.tech import TechName, load_tile_sizes

TT_SUPPORT_TOOLS_REPO = "https://github.com/TinyTapeout/tt-support-tools"


@dataclass
class ProjectContext:
    project_dir: Path
    tt_tools_dir: Path | None
    info: ProjectInfo | None
    tech: TechName
    has_gds: bool
    info_errors: list[str] | None = None

    @property
    def info_yaml_path(self) -> Path:
        return self.project_dir / "info.yaml"

    @property
    def gds_dir(self) -> Path:
        return self.project_dir / "runs" / "wokwi" / "final" / "gds"

    def require_tt_tools(self) -> Path:
        """Return tt_tools_dir, cloning or updating tt-support-tools as needed."""
        if self.tt_tools_dir is not None:
            _update_tt_tools(self.tt_tools_dir)
            _install_tt_tools_deps(self.tt_tools_dir)
            return self.tt_tools_dir
        tt_dir = _clone_tt_tools(self.project_dir)
        _install_tt_tools_deps(tt_dir)
        self.tt_tools_dir = tt_dir
        return tt_dir


def _clone_tt_tools(project_dir: Path) -> Path:
    """Clone tt-support-tools into project_dir/tt/."""
    from tinytapeout.cli.console import console

    tt_dir = project_dir / "tt"
    console.print(f"Cloning tt-support-tools into {tt_dir} ...")
    result = subprocess.run(
        ["git", "clone", "--depth=1", TT_SUPPORT_TOOLS_REPO, str(tt_dir)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        console.print(f"[red]Failed to clone tt-support-tools:[/red]\n{result.stderr}")
        raise SystemExit(2)
    console.print("Done.\n")
    return tt_dir


def _update_tt_tools(tt_dir: Path) -> None:
    """Pull latest main in an existing tt-support-tools checkout."""
    from tinytapeout.cli.console import console

    console.print("Updating tt-support-tools ...")
    result = subprocess.run(
        ["git", "-C", str(tt_dir), "pull", "--ff-only", "--depth=1"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        console.print("[yellow]Could not update tt-support-tools, using existing version.[/yellow]")
    else:
        console.print("Done.\n")


def _tt_tools_python(tt_dir: Path) -> str:
    """Return the Python interpreter for tt-support-tools."""
    venv_python = tt_dir / ".venv" / "bin" / "python"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


def _install_tt_tools_deps(tt_dir: Path) -> None:
    """Create a venv and install tt-support-tools dependencies if needed."""
    from tinytapeout.cli.console import console

    req_file = tt_dir / "requirements.txt"
    if not req_file.exists():
        return

    venv_dir = tt_dir / ".venv"
    venv_python = venv_dir / "bin" / "python"

    # Check if existing venv is broken (e.g. Python version changed)
    if venv_python.exists():
        result = subprocess.run(
            [str(venv_python), "-c", "import sys"],
            capture_output=True,
        )
        if result.returncode != 0:
            import shutil

            console.print("Removing broken tt-support-tools venv ...")
            shutil.rmtree(venv_dir)

    # Create venv if it doesn't exist
    if not venv_python.exists():
        console.print("Creating tt-support-tools venv ...")
        result = subprocess.run(
            [sys.executable, "-m", "venv", str(venv_dir)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            console.print(
                f"[red]Failed to create venv:[/red]\n{result.stderr}"
            )
            raise SystemExit(2)

    # Check if deps are already satisfied (fast path)
    result = subprocess.run(
        [str(venv_python), "-m", "pip", "install", "--dry-run", "-r", str(req_file)],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0 and "Would install" not in result.stdout:
        return

    console.print("Installing tt-support-tools dependencies ...")
    result = subprocess.run(
        [str(venv_python), "-m", "pip", "install", "-r", str(req_file)],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        console.print(
            f"[red]Failed to install tt-support-tools dependencies:[/red]\n{result.stderr}"
        )
        raise SystemExit(2)
    console.print("Done.\n")


def detect_tech(project_dir: Path, yaml_data: dict | None = None) -> TechName:
    """Detect the PDK tech from info.yaml, env var, or default."""
    # 1. Check info.yaml for pdk field (Phase 1 forward-compat)
    if yaml_data and "project" in yaml_data:
        pdk = yaml_data["project"].get("pdk")
        if pdk in ("sky130A", "ihp-sg13g2", "gf180mcuD"):
            return pdk

    # 2. Check TT_PDK environment variable
    env_pdk = os.environ.get("TT_PDK")
    if env_pdk in ("sky130A", "ihp-sg13g2", "gf180mcuD"):
        return env_pdk  # type: ignore[return-value]

    # 3. Default to sky130A
    return "sky130A"


def detect_context(project_dir: str = ".") -> ProjectContext:
    """Detect project context from the working directory."""
    project_path = Path(project_dir).resolve()

    # Look for info.yaml
    info_yaml_path = project_path / "info.yaml"
    yaml_data = None
    info = None
    if info_yaml_path.exists():
        with open(info_yaml_path) as f:
            yaml_data = yaml.safe_load(f)

    # Detect tech
    tech = detect_tech(project_path, yaml_data)

    # Look for tt/
    tt_tools_dir: Path | None = project_path / "tt"
    if not (tt_tools_dir / "tt_tool.py").exists():
        tt_tools_dir = None

    # Parse project info if yaml and tt-support-tools are available
    info_errors = None
    if yaml_data and tt_tools_dir:
        try:
            tile_sizes = load_tile_sizes(tech, tt_tools_dir)
            info = ProjectInfo(yaml_data, tile_sizes)
        except ProjectYamlError as e:
            info_errors = e.args[0] if isinstance(e.args[0], list) else [str(e)]
        except Exception as e:
            info_errors = [str(e)]

    # Check for existing GDS
    gds_dir = project_path / "runs" / "wokwi" / "final" / "gds"
    has_gds = gds_dir.exists() and any(gds_dir.glob("*.gds"))

    return ProjectContext(
        project_dir=project_path,
        tt_tools_dir=tt_tools_dir,
        info=info,
        tech=tech,
        has_gds=has_gds,
        info_errors=info_errors,
    )
