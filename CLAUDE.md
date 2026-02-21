# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Tiny Tapeout CLI (`tt`) — a Python CLI for designing, testing, and hardening ASIC projects for [Tiny Tapeout](https://tinytapeout.com). It wraps `tt-support-tools` with a user-friendly interface. Entry point: `tt = tinytapeout.cli.app:cli`.

## Commands

```bash
# Run tests
hatch test

# Run a single test file or test
hatch test -- tests/test_project_info.py
hatch test -- tests/test_project_info.py::test_valid_yaml -v

# Run the CLI locally
hatch run tt -- doctor

# Lint (runs ruff + pre-commit hooks)
pre-commit run --all-files
```

## Architecture

Two-layer design under `src/tinytapeout/`:

**Library layer** (no CLI dependencies):
- `project_info.py` — Parses and validates `info.yaml` (YAML version 6). `ProjectInfo` collects all validation errors before raising `ProjectYamlError`.
- `tech.py` — PDK technology definitions (sky130A, ihp-sg13g2, gf180mcuD, fpgaUp5k). Loads tile sizes from tt-support-tools.
- `project_checks.py` — Validates `docs/info.md` content.

**CLI layer** (`cli/`):
- `app.py` — Click group, registers commands.
- `commands/` — Command implementations: `init` (project scaffolding), `doctor` (env checks), `check` (project validation), `gds` (build/stats/validate/view subcommands).
- `context.py` — `ProjectContext` dataclass: detects project from working directory, manages tt-support-tools clone/update/venv.
- `environment.py` — Checks for Python, Docker, Git, PDK.
- `runner.py` — Subprocess wrappers for `tt_tool.py` and precheck.
- `console.py` — Rich console singleton.
- `update_checker.py` — PyPI update notifications (24h cache).

Heavy operations (hardening, DRC) delegate to `tt-support-tools` via subprocess (`runner.py`), not in-process.

## Key Conventions

- Python >= 3.11, type hints with `X | Y` union syntax
- Ruff for linting (rules: E, F, I, UP, B) and formatting; max line length 120
- Hatch build system with `hatch-vcs` for versioning from git tags (fallback: `0.0.0-dev`)
- Source layout: `src/tinytapeout/`
- Tests in `tests/` using pytest; CI tests against Python 3.11, 3.12, 3.13
- Top modules must start with `tt_um_` (except Wokwi projects)
- Tech detection: info.yaml `project.pdk` → `TT_PDK` env var → default `sky130A`
