import os
from pathlib import Path

from tinytapeout.project_info import ProjectInfo, ProjectYamlError
from tinytapeout.tech import TechName, load_tile_sizes


def check_info_md(project_dir: str) -> list[str]:
    info_md = os.path.join(project_dir, "docs/info.md")
    if not os.path.exists(info_md):
        return ["Missing docs/info.md file"]

    with open(info_md) as fh:
        info_md_content = fh.read()

    errors = []
    if "# How it works\n\nExplain how your project works" in info_md_content:
        errors += ["Missing 'How it works' section in docs/info.md"]

    if "# How to test\n\nExplain how to use your project" in info_md_content:
        errors += ["Missing 'How to test' section in docs/info.md"]

    return errors


def check_info_yaml(
    project_dir: str, pdk: TechName, tt_tools_dir: str | Path
) -> list[str]:
    import yaml

    info_yaml = os.path.join(project_dir, "info.yaml")
    if not os.path.exists(info_yaml):
        return ["Missing info.yaml file"]

    with open(info_yaml) as fh:
        try:
            yaml_data = yaml.safe_load(fh)
        except yaml.YAMLError as e:
            return [f"Error parsing info.yaml: {e}"]

    tile_sizes = load_tile_sizes(pdk, tt_tools_dir)

    try:
        _ = ProjectInfo(yaml_data, tile_sizes, require_pinout=True)
    except Exception as e:
        if isinstance(e, ProjectYamlError):
            return e.errors

    return []  # No errors
