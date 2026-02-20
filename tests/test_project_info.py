import pytest
import yaml

from tinytapeout.project_info import YAML_VERSION, ProjectInfo, ProjectYamlError


@pytest.fixture
def valid_yaml_data():
    return {
        "yaml_version": YAML_VERSION,
        "project": {
            "title": "Test Project",
            "author": "Test Author",
            "description": "Test Description",
            "tiles": "1x1",
            "analog_pins": 0,
            "uses_3v3": False,
            "language": "Verilog",
            "top_module": "tt_um_test_project",
            "source_files": ["test.v"],
            "clock_hz": 10000000,
        },
        "pinout": {
            **{f"ui[{i}]": f"input_{i}" for i in range(8)},
            **{f"uo[{i}]": f"output_{i}" for i in range(8)},
            **{f"uio[{i}]": f"bidir_{i}" for i in range(8)},
        },
    }


@pytest.fixture
def tile_sizes():
    return {
        "1x1": "0 0 161 111.52",
        "1x2": "0 0 161 225.76",
        "2x2": "0 0 322 225.76",
        "8x2": "0 0 1292 225.76",
    }


class TestProjectInfoValid:
    def test_valid_digital_project(self, valid_yaml_data, tile_sizes):
        info = ProjectInfo(valid_yaml_data, tile_sizes)
        assert info.title == "Test Project"
        assert info.top_module == "tt_um_test_project"
        assert info.tiles == "1x1"
        assert info.is_analog is False
        assert info.clock_hz == 10000000

    def test_valid_wokwi_project(self, valid_yaml_data, tile_sizes):
        valid_yaml_data["project"]["language"] = "Wokwi"
        valid_yaml_data["project"]["wokwi_id"] = 123456789
        del valid_yaml_data["project"]["top_module"]
        del valid_yaml_data["project"]["source_files"]
        info = ProjectInfo(valid_yaml_data, tile_sizes)
        assert info.top_module == "tt_um_wokwi_123456789"
        assert info.source_files == ["tt_um_wokwi_123456789.v", "cells.v"]

    def test_valid_analog_project(self, valid_yaml_data, tile_sizes):
        valid_yaml_data["project"]["analog_pins"] = 2
        valid_yaml_data["project"]["uses_3v3"] = True
        for i in range(6):
            valid_yaml_data["pinout"][f"ua[{i}]"] = f"analog_{i}" if i < 2 else ""
        info = ProjectInfo(valid_yaml_data, tile_sizes)
        assert info.analog_pins == 2
        assert info.is_analog is True
        assert info.uses_3v3 is True
        assert info.pinout.ua == ["analog_0", "analog_1", "", "", "", ""]

    def test_optional_fields_default(self, valid_yaml_data, tile_sizes):
        del valid_yaml_data["project"]["analog_pins"]
        del valid_yaml_data["project"]["uses_3v3"]
        info = ProjectInfo(valid_yaml_data, tile_sizes)
        assert info.analog_pins == 0
        assert info.uses_3v3 is False
        assert info.discord is None

    def test_empty_pin_descriptions_allowed(self, valid_yaml_data, tile_sizes):
        valid_yaml_data["pinout"]["ui[0]"] = ""
        info = ProjectInfo(valid_yaml_data, tile_sizes)
        assert info.pinout.ui[0] == ""

    def test_require_pinout_rejects_all_empty(self, valid_yaml_data, tile_sizes):
        for pin in valid_yaml_data["pinout"]:
            valid_yaml_data["pinout"][pin] = ""
        with pytest.raises(ProjectYamlError, match="fill in the 'pinout' section"):
            ProjectInfo(valid_yaml_data, tile_sizes, require_pinout=True)
        # But passes without require_pinout
        ProjectInfo(valid_yaml_data, tile_sizes)


class TestProjectInfoErrors:
    def test_missing_project_section(self, valid_yaml_data, tile_sizes):
        del valid_yaml_data["project"]
        with pytest.raises(ProjectYamlError, match="Missing 'project' section"):
            ProjectInfo(valid_yaml_data, tile_sizes)

    def test_wrong_yaml_version(self, valid_yaml_data, tile_sizes):
        valid_yaml_data["yaml_version"] = 999
        with pytest.raises(ProjectYamlError, match="Unsupported YAML version"):
            ProjectInfo(valid_yaml_data, tile_sizes)

    def test_invalid_tiles(self, valid_yaml_data, tile_sizes):
        valid_yaml_data["project"]["tiles"] = "99x99"
        with pytest.raises(ProjectYamlError, match="Invalid value for 'tiles'"):
            ProjectInfo(valid_yaml_data, tile_sizes)

    def test_top_module_must_start_with_tt_um(self, valid_yaml_data, tile_sizes):
        valid_yaml_data["project"]["top_module"] = "bad_name"
        with pytest.raises(ProjectYamlError, match="must start with 'tt_um_'"):
            ProjectInfo(valid_yaml_data, tile_sizes)

    def test_uses_3v3_requires_analog_pins(self, valid_yaml_data, tile_sizes):
        valid_yaml_data["project"]["uses_3v3"] = True
        with pytest.raises(
            ProjectYamlError, match="3v3 power need at least one analog pin"
        ):
            ProjectInfo(valid_yaml_data, tile_sizes)

    def test_invalid_pinout_keys_rejected(self, valid_yaml_data, tile_sizes):
        valid_yaml_data["pinout"]["bogus"] = "value"
        with pytest.raises(ProjectYamlError, match="Invalid keys"):
            ProjectInfo(valid_yaml_data, tile_sizes)

    def test_multiple_errors_collected(self, valid_yaml_data, tile_sizes):
        del valid_yaml_data["project"]["title"]
        del valid_yaml_data["project"]["author"]
        valid_yaml_data["project"]["tiles"] = "invalid"
        with pytest.raises(ProjectYamlError) as exc_info:
            ProjectInfo(valid_yaml_data, tile_sizes)
        errors = exc_info.value.errors
        assert len(errors) == 3
        assert any("title" in e for e in errors)
        assert any("author" in e for e in errors)
        assert any("tiles" in e for e in errors)


class TestProjectInfoIntegration:
    def test_roundtrip_from_yaml_string(self, tile_sizes):
        yaml_content = f"""
yaml_version: {YAML_VERSION}
project:
  title: "Integration Test"
  author: "Test Author"
  description: "A test"
  tiles: "1x1"
  language: "Verilog"
  top_module: "tt_um_integration_test"
  source_files: ["integration_test.v"]
  clock_hz: 25000000
pinout:
  ui[0]: "clk"
  ui[1]: "rst_n"
  ui[2]: ""
  ui[3]: ""
  ui[4]: ""
  ui[5]: ""
  ui[6]: ""
  ui[7]: ""
  uo[0]: "data_out"
  uo[1]: ""
  uo[2]: ""
  uo[3]: ""
  uo[4]: ""
  uo[5]: ""
  uo[6]: ""
  uo[7]: ""
  uio[0]: ""
  uio[1]: ""
  uio[2]: ""
  uio[3]: ""
  uio[4]: ""
  uio[5]: ""
  uio[6]: ""
  uio[7]: ""
"""
        info = ProjectInfo(yaml.safe_load(yaml_content), tile_sizes)
        assert info.title == "Integration Test"
        assert info.top_module == "tt_um_integration_test"
        assert info.clock_hz == 25000000
