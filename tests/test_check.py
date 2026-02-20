from pathlib import Path

import yaml

from tinytapeout.project_checks import check_info_md, check_info_yaml
from tinytapeout.project_info import YAML_VERSION


def _make_project(tmp_path):
    data = {
        "yaml_version": YAML_VERSION,
        "project": {
            "title": "Test",
            "author": "Author",
            "description": "Desc",
            "tiles": "1x1",
            "language": "Verilog",
            "top_module": "tt_um_test",
            "source_files": ["test.v"],
            "clock_hz": 10000000,
        },
        "pinout": {
            **{f"ui[{i}]": f"in_{i}" for i in range(8)},
            **{f"uo[{i}]": f"out_{i}" for i in range(8)},
            **{f"uio[{i}]": f"bio_{i}" for i in range(8)},
        },
    }
    (tmp_path / "info.yaml").write_text(yaml.dump(data))
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "info.md").write_text("# How it works\n\nReal content.\n")


def test_valid_project_passes(tmp_path, tt_tools_dir: Path):
    _make_project(tmp_path)
    assert check_info_yaml(str(tmp_path), "sky130A", tt_tools_dir) == []
    assert check_info_md(str(tmp_path)) == []


def test_missing_info_yaml(tmp_path, tt_tools_dir: Path):
    assert check_info_yaml(str(tmp_path), "sky130A", tt_tools_dir) == ["Missing info.yaml file"]


def test_invalid_yaml_reports_parse_error(tmp_path, tt_tools_dir: Path):
    (tmp_path / "info.yaml").write_text("{{bad")
    errors = check_info_yaml(str(tmp_path), "sky130A", tt_tools_dir)
    assert len(errors) == 1
    assert "Error parsing" in errors[0]


def test_missing_info_md(tmp_path):
    assert check_info_md(str(tmp_path)) == ["Missing docs/info.md file"]


def test_placeholder_text_detected(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "info.md").write_text(
        "# How it works\n\nExplain how your project works\n\n"
        "# How to test\n\nExplain how to use your project\n"
    )
    errors = check_info_md(str(tmp_path))
    assert len(errors) == 2
