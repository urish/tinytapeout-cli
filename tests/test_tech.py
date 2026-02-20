from pathlib import Path

from tinytapeout.tech import (
    ASIC_TECHS,
    load_cells,
    load_tile_sizes,
    tech_map,
)


def test_all_asic_techs_in_map():
    for tech in ASIC_TECHS:
        assert tech in tech_map


def test_sky130_is_not_fpga():
    assert tech_map["sky130A"].is_fpga is False


def test_fpga_is_fpga():
    assert tech_map["fpgaUp5k"].is_fpga is True


def test_load_tile_sizes(tt_tools_dir: Path):
    for pdk in ASIC_TECHS:
        sizes = load_tile_sizes(pdk, tt_tools_dir)
        assert "1x1" in sizes
        assert len(sizes) > 1


def test_load_cells(tt_tools_dir: Path):
    for pdk in ASIC_TECHS:
        cells = load_cells(pdk, tt_tools_dir)
        assert len(cells) > 0
