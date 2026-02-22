# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `tt init` command for creating new projects from per-tech templates (sky130A, ihp-sg13g2)
- `tt test` command for RTL simulation tests
- `tt test --gl` command for gate-level simulation tests
- iverilog version checking in `tt doctor` and `tt test` (warns if < 13.0 for GL sim)
- Writes `pdk` field to info.yaml during `tt init` (single source of truth for tech detection)

## [0.1.0] - 2026-02-20

### Added

- Initial CLI framework with Click + Rich
- `tt doctor` command for system readiness checks (Python, Docker, Git, PDK, tt-support-tools)
- `tt check` command for info.yaml and docs/info.md validation
- `tt gds build` command (delegates to tt-support-tools)
- `tt gds stats` command with `--json` flag
- `tt gds validate` command with `--json` flag
- `tt gds view` command group (2d, 3d, klayout)
- Auto-update checking from PyPI (24h cache, skipped in CI)
- CI detection: suppresses Rich animations, writes to GitHub step summary
- Project context detection from info.yaml, tt/ submodule, PDK environment
- Library layer: `project_info`, `project_checks`, `tech` (migrated from tt-support-tools)
