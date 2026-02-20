from pathlib import Path

import yaml

from tinytapeout.cli.context import detect_context, detect_tech
from tinytapeout.project_info import YAML_VERSION


def _make_info_yaml(tmp_path, **overrides):
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
            **overrides,
        },
        "pinout": {
            **{f"ui[{i}]": f"in_{i}" for i in range(8)},
            **{f"uo[{i}]": f"out_{i}" for i in range(8)},
            **{f"uio[{i}]": f"bio_{i}" for i in range(8)},
        },
    }
    (tmp_path / "info.yaml").write_text(yaml.dump(data))


class TestDetectTech:
    def test_defaults_to_sky130(self):
        assert detect_tech(Path("/nonexistent")) == "sky130A"

    def test_reads_from_yaml(self):
        yaml_data = {"project": {"pdk": "ihp-sg13g2"}}
        assert detect_tech(Path("/x"), yaml_data) == "ihp-sg13g2"

    def test_reads_from_env(self, monkeypatch):
        monkeypatch.setenv("TT_PDK", "gf180mcuD")
        assert detect_tech(Path("/x")) == "gf180mcuD"

    def test_yaml_beats_env(self, monkeypatch):
        monkeypatch.setenv("TT_PDK", "gf180mcuD")
        assert (
            detect_tech(Path("/x"), {"project": {"pdk": "ihp-sg13g2"}}) == "ihp-sg13g2"
        )


class TestDetectContext:
    def test_with_tt_tools(self, tmp_path, tt_tools_dir: Path):
        _make_info_yaml(tmp_path)
        (tmp_path / "tt").symlink_to(tt_tools_dir)
        ctx = detect_context(str(tmp_path))
        assert ctx.info is not None
        assert ctx.info.title == "Test"
        assert ctx.tt_tools_dir is not None

    def test_without_tt_tools(self, tmp_path):
        _make_info_yaml(tmp_path)
        ctx = detect_context(str(tmp_path))
        assert ctx.tt_tools_dir is None
        assert ctx.info is None  # can't parse without tile_sizes

    def test_empty_dir(self, tmp_path):
        ctx = detect_context(str(tmp_path))
        assert ctx.info is None
        assert ctx.tt_tools_dir is None
        assert ctx.has_gds is False

    def test_detects_gds(self, tmp_path, tt_tools_dir: Path):
        _make_info_yaml(tmp_path)
        (tmp_path / "tt").symlink_to(tt_tools_dir)
        gds_dir = tmp_path / "runs" / "wokwi" / "final" / "gds"
        gds_dir.mkdir(parents=True)
        (gds_dir / "test.gds").write_bytes(b"\x00")
        assert detect_context(str(tmp_path)).has_gds is True
