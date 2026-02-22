# Tiny Tapeout CLI - Implementation Plan

## Context

Users currently interact with tt-support-tools by submoduling it as `tt/` in their project repos and running commands like `python tt/tt_tool.py --harden`. This requires manual setup of Python environments, PDK paths, LibreLane, and understanding a flat-flag CLI. The goal is to replace this with a pip-installable `tt` command that's easy to install, discover, and use.

**Key insight**: tt-support-tools mixes two concerns:
- **User-facing code**: `project_info.py`, `project_checks.py`, `tech.py`, parts of `project.py`
- **Shuttle-integration code**: `configure.py`, `shuttle.py`, `rom.py`, `logo.py`, `documentation.py`

It's submoduled in ~20+ shuttle repos. The user-facing code naturally belongs in the CLI.

---

## Architecture: Single Package `tinytapeout-cli`

**Repository**: `TinyTapeout/tinytapeout-cli`
**PyPI package**: `tinytapeout-cli`
**Python import**: `tinytapeout` (decoupled from PyPI name via pyproject.toml)
**CLI command**: `tt`

```bash
pip install tinytapeout-cli    # installs the tt command + library
```

The package contains two layers:
1. **`tinytapeout/` library** -- user-project library code, migrated from tt-support-tools. Handles info.yaml parsing, validation, tech definitions.
2. **`tinytapeout/cli/` commands** -- the Click CLI that exposes the library to users.

For heavy operations (hardening, precheck, FPGA), the CLI delegates to tt-support-tools via subprocess (the `tt/` submodule in the user's project). This keeps the package lightweight.

Over time, tt-support-tools adds `tinytapeout-cli` as a pip dependency and imports the shared library code, eliminating duplication.

### What moves to the `tinytapeout` library (Phase 1)

> Note: the PyPI package is `tinytapeout-cli` but the Python package directory is `tinytapeout/`, so imports are `from tinytapeout.xxx import ...`

These modules have minimal dependencies (PyYAML, stdlib) and are needed by many CLI commands:

| Module | Lines | Dependencies | Why move it |
|--------|-------|-------------|-------------|
| `project_info.py` | 200 | PyYAML | Core to `tt check`, `tt init`, context detection |
| `project_checks.py` | 70 | PyYAML + project_info | `tt check` uses this directly |
| `tech.py` | 285 | json, os (stdlib) | PDK constants needed everywhere; no heavy deps |
| tile_sizes YAML + cells.json | ~50 | - | Referenced by project_info for validation |

### What the CLI handles directly (absorbed from tt-support-tools)

| Operation | Module | Notes |
|-----------|--------|-------|
| **Hardening** | `cli/harden.py` | Calls `python -m librelane` directly. Git metadata via plain `git` subprocess (no GitPython). Config merging, `commit_id.json`, `pdk.json` writing. |

### What stays in tt-support-tools (delegated via subprocess)

These have heavy dependencies (klayout, gdstk, CairoSVG) or complex logic we don't need to absorb yet:

| Module | Heavy Deps | CLI delegates via |
|--------|-----------|-------------------|
| `project.py` (user config, stats, submission) | klayout, gdstk, CairoSVG, GitPython | `python tt/tt_tool.py --create-user-config` etc. |
| `precheck/` | klayout, gdstk, Magic | `python tt/precheck/precheck.py --gds ...` |
| `render_utils.py` | gdstk, CairoSVG | `python tt/tt_tool.py --create-png` |
| `tt_fpga.py` | yowasp-yosys, mpremote | `python tt/tt_fpga.py harden` |

### Migration path for tt-support-tools (Phase 3+)

tt-support-tools adds `tinytapeout-cli` as a pip dependency:
```python
# Before: from project_info import ProjectInfo
# After:  from tinytapeout.project_info import ProjectInfo
```
Backward-compat shim files at root keep submodule usage working.

---

## Package Structure

```
tinytapeout-cli/                     # GitHub: TinyTapeout/tinytapeout-cli
├── pyproject.toml
├── README.md
├── CHANGELOG.md                     # Keep a Changelog format for the CLI package
├── LICENSE
├── .pre-commit-config.yaml          # ruff, pre-commit-hooks
├── .github/
│   └── workflows/
│       ├── test.yaml                # pytest + JUnit XML + test-summary
│       ├── lint.yaml                # pre-commit run --all-files
│       ├── e2e.yaml                 # E2E: tt init → check → test → gds build → validate → test --gl (matrix: sky130A, ihp-sg13g2)
│       └── publish.yaml             # on release → PyPI (trusted publishing)
├── src/
│   └── tinytapeout/
│       ├── __init__.py              # Package version
│       ├── project_info.py          # Migrated from tt-support-tools
│       ├── project_checks.py        # Migrated from tt-support-tools
│       ├── tech.py                  # Migrated from tt-support-tools
│       ├── tech_data/               # Migrated tech data files
│       │   ├── sky130A/
│       │   │   ├── tile_sizes.yaml
│       │   │   └── cells.json
│       │   ├── ihp-sg13g2/
│       │   │   ├── tile_sizes.yaml
│       │   │   └── cells.json
│       │   └── gf180mcuD/
│       │       ├── tile_sizes.yaml
│       │       └── cells.json
│       ├── cli/
│       │   ├── __init__.py
│       │   ├── app.py               # Root Click group, update check
│       │   ├── commands/
│       │   │   ├── __init__.py
│       │   │   ├── setup.py         # tt setup <tech>
│       │   │   ├── doctor.py        # tt doctor
│       │   │   ├── init.py          # tt init [tech]
│       │   │   ├── check.py         # tt check
│       │   │   ├── test.py          # tt test / tt test-gl
│       │   │   ├── gds.py           # tt gds build|stats|validate + tt gds view [2d|3d|klayout]
│       │   │   ├── fpga.py          # tt fpga build|upload
│       │   │   ├── publish.py       # tt publish (Phase 4)
│       │   │   ├── login.py         # tt login (Phase 4)
│       │   │   ├── submit.py        # tt submit (Phase 4)
│       │   │   └── submissions.py   # tt submissions (Phase 4)
│       │   ├── context.py           # Detect project dir, tt/ submodule, PDK
│       │   ├── runner.py            # Execute tt-support-tools scripts
│       │   ├── environment.py       # Docker, platform, tool detection
│       │   ├── update_checker.py    # Daily PyPI update check
│       │   ├── templates.py         # Project scaffolding (tt init)
│       │   └── console.py           # Rich console helpers
│       └── __main__.py              # python -m tinytapeout
└── tests/
    ├── test_project_info.py         # Migrated from tt-support-tools
    ├── test_doctor.py
    ├── test_check.py
    ├── test_context.py
    └── ...
```

---

## CLI Framework: Click + Rich

**Click** for command parsing (mature, native nested groups, already a transitive dep).
**Rich** for terminal output (colors, progress bars, tables, panels).

```python
# src/tinytapeout/cli/app.py
import click
from tinytapeout.cli.update_checker import check_for_updates

@click.group()
@click.version_option()
def cli():
    """Tiny Tapeout CLI - Design, test, and harden ASIC projects."""
    check_for_updates()

from tinytapeout.cli.commands import setup, doctor, init, check, test, gds, fpga
cli.add_command(setup.setup)
cli.add_command(doctor.doctor)
cli.add_command(init.init)
cli.add_command(check.check)
cli.add_command(test.test)
cli.add_command(gds.gds)          # includes: build, stats, validate, view [2d|3d|klayout]
cli.add_command(fpga.fpga)
# Future: cli.add_command(switch_tech.switch_tech)
# Future: cli.add_command(publish.publish)
# Future: cli.add_command(login.login)
# Future: cli.add_command(submit.submit)
# Future: cli.add_command(submissions.submissions)
```

---

## Design Decision: `tt gds` naming

The project is migrating from GDSII to OASIS (OAS) as the submission format. We considered renaming `tt gds ...` to `tt layout ...` or `tt harden ...`, but decided to **keep `tt gds`**:

- **"GDS" is EDA jargon, not just a file format.** Engineers say "generate GDS" regardless of whether the output is `.gds` or `.oas`, the same way "tape out" persists. Users searching for help will search "GDS."
- **Ecosystem consistency.** `tt-gds-action`, `gds-viewer.tinytapeout.com`, `gds_render.svg`, `final/gds/` directories — the entire TT ecosystem uses "gds." The CLI shouldn't be the lone outlier.
- **The format migration is invisible to users.** Whether `tt gds build` produces a `.gds` or `.oas` file is an implementation detail in tt-support-tools, not a user-facing concern. The CLI abstracts this away.
- **Alternatives aren't better enough.** `tt layout` is more technically correct but less recognizable. `tt harden` only fits the build step, not view/stats/validate.

If the ecosystem later renames holistically (action, viewer, directories), the CLI can follow. For now, consistency wins over precision.

---

## Command Implementation Details

### `tt doctor`
Checks system readiness. Uses the library directly (no tt/ submodule needed).

```
$ tt doctor
  OK   Python 3.11.5
  OK   Docker 24.0.7 (running)
  OK   Git 2.42.0
  WARN PDK not installed (run 'tt setup sky130' to install)
  OK   pip packages: PyYAML, cocotb
  INFO Project directory: ./my-project (info.yaml found)
  OK   tt-support-tools: tt/ submodule present (commit abc1234)
```

### `tt init [tech]`
Interactive wizard OR fully non-interactive via CLI flags (for AI agents / CI).

**Interactive mode** (default when flags are missing):
```
$ tt init
? Project name: my_counter
? Project type: Digital (default) / Analog / Mixed Signal
? Technology: Sky130 (default)
? HDL language: Verilog  (for digital/mixed signal)
? Tile size: 1x1
? Author: Jane Doe
? Description: A simple 8-bit counter
? Clock frequency (Hz): 50000000

Cloning template...
Project created at ./tt_um_my_counter
```

**Non-interactive mode** (all flags provided -- for AI agents and CI):
```bash
tt init --name my_counter --type digital --tech sky130 --language Verilog \
  --tiles 1x1 --author "Jane Doe" --description "A counter" --clock-hz 50000000
```

If all required flags are provided, the wizard is skipped entirely. If some are missing, only the missing ones are prompted interactively.

**Implementation**: Use `click.option()` with `prompt=True` for each field. Click natively supports this -- if a value is passed as a flag, the prompt is skipped; if not, the user is prompted. For choice fields (type, tech, language, tile size), use `click.Choice`.

**Project types** (3 types, not to be confused with HDL language):

| Type | Template | Hardening | Analog pins | Notes |
|------|----------|-----------|-------------|-------|
| **Digital** (default) | Per-tech verilog template | LibreLane (via `tt gds build`) | 0 | Standard flow. Tiles vary by tech |
| **Analog** | Analog template + DEF + Magic/KLayout init | Manual (Magic/KLayout) | 1-6 | No digital synthesis. Min tile: 1x2. User creates .mag or .gds manually |
| **Mixed Signal** | Digital template + analog macros | LibreLane | 0-6 | Digital top with analog sub-blocks, or analog template with digital IO |

**Template repos are per-tech** (currently separate GitHub repos):
- Sky130: `TinyTapeout/tt-verilog-template`
- IHP: `TinyTapeout/ttihp-verilog-template`
- GF180: `TinyTapeout/ttgf-verilog-template`

The templates are nearly identical. Tech-specific differences are confined to:
- `info.yaml`: tile size comment and valid tile values (sky130 ~160x225um, IHP ~167x108um, GF180 ~340x160um)
- `test/Makefile`: GL simulation PDK library paths and compile flags (GF180 needs `-DUSE_POWER_PINS -DUNIT_DELAY=\#1`)
- `test/tb.v`: GF180 needs `VPWR`/`VGND` power port wiring in GL test ifdef
- `.github/workflows/*.yaml`: action tags (`@tt10` / `@ttihp26a` / `@ttgf0p2`) and PDK name
- `.devcontainer/Dockerfile`: PDK, LibreLane version, Ubuntu base version

**Digital template flow** (Phase 2):
1. Clone the tech-appropriate template: `git clone --depth=1 https://github.com/TinyTapeout/{template-repo}`
2. Patch info.yaml with user answers
3. Rename `tt_um_example` → `tt_um_{name}` in `info.yaml`, `src/project.v`, `test/tb.v`
4. Remove template .git, init fresh repo

**`tt switch-tech <new-tech>`** -- switch an existing project's tech:
Since the tech-specific differences are well-defined, switching tech is a targeted set of file modifications:
1. Update `test/Makefile` GL simulation section (PDK paths, compile flags)
2. Update `test/tb.v` (add/remove VPWR/VGND ifdef for GF180)
3. Update `.github/workflows/*.yaml` (action tags, PDK name)
4. Update `.devcontainer/Dockerfile` (PDK, versions)
5. Update info.yaml tile size comment and validate current tile value against new tech
6. Warn if tile size is not valid for new tech

**Analog project initialization** (Phase 3):
For `--type analog`, `tt init` will additionally:
- Prompt for: number of analog pins (1-6), 3v3 power, layout tool preference (Magic or KLayout)
- Enforce min tile size of 1x2
- Download the appropriate DEF template from tt-support-tools (`tt_analog_{tiles}.def` or `tt_analog_{tiles}_3v3.def`)
- Generate a customized `magic_init_project.tcl` (or KLayout equivalent) with the user's top module name, template file, and power stripe configuration
- Existing TCL templates per-tech: `tech/sky130A/def/analog/magic_init_project.tcl`, `tech/ihp-sg13g2/def/analog/magic_init_project.tcl`
- Supported techs for analog: sky130A, ihp-sg13g2 (not gf180mcuD yet)

### `tt check`
Validates info.yaml and docs/info.md. Uses the library directly -- no subprocess needed.

```python
from tinytapeout.project_checks import check_info_yaml, check_info_md
errors = check_info_yaml(project_dir, tech) + check_info_md(project_dir)
# Format with Rich
```

### `tt test [--gl]`
Runs cocotb tests from the `test/` directory.

```python
@cli.command()
@click.option("--gl", is_flag=True, help="Run gate-level simulation (requires hardened design)")
def test(gl):
    """Run project tests."""
    # Runs: make -C test/
    # For --gl: sets GATES=yes environment variable, checks GDS exists first
    # Captures and formats output
```

### `tt gds build`
Hardens the project (build-only, no validation). The hardening step calls LibreLane directly via the CLI's own `harden.py` module — no longer delegated to `tt_tool.py --harden`. Other steps (user config, stats, submission) still delegate to tt-support-tools.

```python
# Step 1: python tt/tt_tool.py --create-user-config [--ihp|--gf]
# Step 2: run_harden(ctx) — calls `python -m librelane` directly
# Step 3: python tt/tt_tool.py --print-warnings / --print-stats
# Step 4: python tt/tt_tool.py --create-tt-submission [--ihp|--gf]
# CLI adds: Rich progress spinner, elapsed time, formatted errors, summary
```

**Hardening works without a git remote.** The CLI adds a placeholder remote if none exists, and falls back gracefully for git metadata (remote URL, commit hash) — these only affect `commit_id.json` metadata, not the hardened design.

**Validation is separate.** Run `tt gds validate` after building to run DRC precheck. This is intentionally decoupled because digital projects produce valid GDS from hardening; precheck is more relevant for analog/mixed-signal designs where users may go through a different flow.

### `tt gds stats`
```python
# Delegates to: python tt/tt_tool.py --print-stats --print-cell-summary [--ihp|--gf]
# Reformats output as a Rich table
```

### `tt gds validate`
```python
# Delegates to: python tt/precheck/precheck.py --gds <gds_path> --tech <tech>
# Formats results as a checklist with pass/fail indicators
```

### `tt gds view [2d|3d|klayout]`
Subcommand group for viewing the hardened GDS. Default (no subcommand) opens the 2D PNG render.

```python
@gds.group(invoke_without_command=True)
@click.pass_context
def view(ctx):
    """View the hardened GDS layout."""
    if ctx.invoked_subcommand is None:
        # Default: same as `tt gds view 2d`
        view_2d()

@view.command(name="2d")
def view_2d():
    """Open a 2D PNG render of the layout."""
    # python tt/tt_tool.py --create-png, then open with system viewer

@view.command(name="3d")
def view_3d():
    """Open the 3D GDS viewer in your browser."""
    # Opens the Tiny Tapeout 3D GDS viewer
    webbrowser.open(viewer_url)

@view.command(name="klayout")
def view_klayout():
    """Open the layout in KLayout GUI."""
    # python tt/tt_tool.py --open-in-klayout
```

Usage:
- `tt gds view` or `tt gds view 2d` → PNG render opened in system viewer
- `tt gds view 3d` → Tiny Tapeout 3D viewer in browser
- `tt gds view klayout` → Opens KLayout GUI

### `tt fpga build` / `tt fpga upload`
```python
# Delegates to: python tt/tt_fpga.py harden [--breakout-target fabricfox]
# Delegates to: python tt/tt_fpga.py configure --upload [--port /dev/ttyUSB0]
```

### `tt setup <tech>`
Guides user through PDK installation. CLI-native (no tt/ submodule needed).

For native Linux: guides through volare PDK installation.
For Mac/Windows: guides through Docker setup + pulling a pre-built image.

### `tt publish` (Phase 4)
Publishes the project to GitHub and configures it for the Tiny Tapeout workflow.

```
$ tt publish
Publishing tt_um_my_counter to GitHub...
  Creating repository TinyTapeout/tt_um_my_counter...
  Pushing project files...
  Enabling GitHub Pages (deploy from Actions)...
  Done! https://github.com/youruser/tt_um_my_counter
```

**Steps**:
1. Validate project locally first (`tt check` equivalent)
2. Create GitHub repo via GitHub API (uses `gh` CLI or `requests` + user's GitHub token)
3. `git push` the project to the new repo
4. Enable GitHub Pages with "deploy from GitHub Actions" source via GitHub API
5. Optionally trigger first GDS build workflow

**Authentication**: Uses GitHub token from `gh auth status` (GitHub CLI) or `GITHUB_TOKEN` env var.

**Non-interactive mode**:
```bash
tt publish --repo youruser/tt_um_my_counter --public --enable-pages
```

### `tt submit` (Phase 4)
Submits a project version to the Tiny Tapeout shuttle via the TT web app API.

```
$ tt submit
Submitting tt_um_my_counter to Tiny Tapeout...
  Shuttle: TT10
  Commit: abc1234
  Version: 2 (previous: 1)
  Status: Submitted
  View at: https://app.tinytapeout.com/projects/123
```

**Integration with tinytapeout-app**:
- The TT web app (SolidJS + Supabase) has a project submission API at `POST /api/projects/submit`
- Submissions are versioned: each submit creates a new row in the `submissions` table with commit SHA, PR number, and workflow run ID
- Project states flow: Draft → Assigned → Submitted
- Authentication: Supabase auth with GitHub OAuth (user must be logged in to app.tinytapeout.com)

**Implementation**:
- CLI authenticates via a token obtained from app.tinytapeout.com (stored in `~/.config/tinytapeout/auth.json`)
- Calls the submission API with: repo URL, commit SHA, shuttle ID
- The API triggers a GitHub PR creation in the shuttle repo (server-side)
- CLI streams the SSE response showing submission progress
- On success, displays the project URL and submission version

**Non-interactive mode**:
```bash
tt submit --shuttle tt10 --commit HEAD --token $TT_API_TOKEN
```

### `tt submissions` (Phase 4)
Lists all submitted revisions for the current project.

```
$ tt submissions
Submissions for tt_um_my_counter (TT10):

  #  Commit   Date         Status     PR    Workflow
  1  abc1234  2025-11-01   Submitted  #42   https://github.com/...
  2  def5678  2025-11-15   Submitted  #57   https://github.com/...
  3  ghi9012  2025-12-01   Pending    #71   https://github.com/...
```

**Implementation**:
- Fetches from TT web app API (uses stored auth token from `tt login`)
- Displays: revision number, commit SHA, submission date, status, PR number, workflow run URL
- `--json` flag for machine-readable output
- Mirrors the submissions page on app.tinytapeout.com

---

## Tech/PDK as Single Source of Truth

### Current State (the problem)

PDK is currently specified in **multiple places** with no single source of truth at the project level:

1. **`.github/workflows/gds.yaml`** — hardcoded per template: `pdk: ihp-sg13g2` as input to tt-gds-action
2. **tt-gds-action `action.yml`** — accepts `pdk` as required input (choice: sky130A | ihp-sg13g2 | gf180mcuD)
3. **tt_tool.py CLI flags** — `--ihp` / `--gf` / default sky130A
4. **Action version tag** — `@tt10` (sky130), `@ttihp26a` (IHP), `@ttgf0p2` (GF180)
5. **Post-hardening `pdk.json`** — written to `runs/wokwi/pdk.json` and `tt_submission/pdk.json`

**info.yaml has no PDK field.** The PDK is implicit to the template choice and workflow file.

This is problematic for the CLI: commands like `tt check`, `tt gds build`, `tt doctor` need to know the tech but have no canonical place to read it from.

### Alternatives

#### Option A: Add `pdk` to `info.yaml` (recommended)

```yaml
yaml_version: 6

project:
  pdk: "sky130A"           # NEW field — single source of truth
  title: "My Project"
  tiles: "1x1"
  # ...
```

| Aspect | Details |
|--------|---------|
| **Pros** | info.yaml is already THE project definition; CLI reads it directly via project_info.py; `tt init` sets it; `tt switch-tech` updates it; project is self-describing; enables cross-validation (tiles valid for PDK) |
| **Cons** | Existing projects need migration (add field); still need to keep workflow `pdk:` input in sync; tt-support-tools needs updating |
| **Migration** | Optional in YAML_VERSION 6 (backward compat: missing = sky130A). Required in future YAML_VERSION 7. `tt check` warns if missing. |
| **tt-support-tools compat** | project_info.py updated to parse optional `pdk` field. tt_tool.py: `--ihp`/`--gf` flags still work as overrides. If info.yaml has `pdk`, flags become optional. |
| **tt-gds-action compat** | `pdk` input becomes optional — if omitted, action reads from info.yaml. Existing workflows with explicit `pdk:` keep working (override). |

#### Option B: Dedicated config file (e.g. `tt.yaml` or `.tinytapeout.yaml`)

```yaml
# tt.yaml
pdk: sky130A
```

| Aspect | Details |
|--------|---------|
| **Pros** | Clean separation from project metadata; no YAML_VERSION change; can hold CLI-specific config |
| **Cons** | Another file to maintain; two sources of project metadata; tt-support-tools needs to learn about it too |

#### Option C: CLI reads from workflow file

```python
# Parse .github/workflows/gds.yaml to find pdk input
```

| Aspect | Details |
|--------|---------|
| **Pros** | No changes to any config files; zero migration |
| **Cons** | Fragile (depends on workflow structure); doesn't work for projects without .github; feels architecturally wrong |

#### Option D: Environment variable only (TT_PDK)

| Aspect | Details |
|--------|---------|
| **Pros** | Simple; works everywhere |
| **Cons** | Not persistent; easy to forget; not self-documenting; no validation |

### Recommendation: Option A — `pdk` in `info.yaml`

**Why**: info.yaml is already the project definition file that every tool reads. Adding `pdk` there makes the project fully self-describing. The CLI, tt-support-tools, and tt-gds-action all already parse info.yaml.

**Exact PDK name spelling**: `sky130A`, `ihp-sg13g2`, `gf180mcuD` (matches `TechName` in tech.py).

**Detailed migration plan**:

1. **Phase 1 (YAML_VERSION 6, backward compat)**:
   - Add optional `pdk` field to `ProjectInfo` (defaults to `sky130A` if missing)
   - CLI reads `pdk` from info.yaml; falls back to `TT_PDK` env var, then `sky130A`
   - `tt init` always writes `pdk` to info.yaml
   - `tt check` warns if `pdk` is missing: "Consider adding 'pdk: sky130A' to info.yaml"
   - tt_tool.py `--ihp`/`--gf` flags still work and override info.yaml value

2. **Phase 2 (tt-gds-action migration)**:
   - tt-gds-action `pdk` input becomes optional (default: read from info.yaml)
   - If both action input and info.yaml specify PDK, action input wins (override for CI)
   - Existing workflows with explicit `pdk:` keep working unchanged

3. **Phase 3 (YAML_VERSION 7)**:
   - `pdk` becomes required in info.yaml
   - Templates updated to include `pdk` field
   - `tt check` errors (not warns) if `pdk` is missing
   - `tt_tool.py` flags become optional overrides only

**What about the action version tag** (`@tt10`, `@ttihp26a`, `@ttgf0p2`)?
The action tag is shuttle-specific, not PDK-specific (a shuttle implies a PDK). This stays in the workflow file — it's not project metadata, it's CI configuration for which shuttle to target. The `pdk` field in info.yaml is the project's tech target; the action tag is which shuttle's tooling to use.

---

## Core Modules

### Project Context Detection
```python
# src/tinytapeout/cli/context.py
@dataclass
class ProjectContext:
    project_dir: Path
    tt_tools_dir: Path | None    # tt/ submodule path
    info: ProjectInfo | None     # Parsed info.yaml (our library)
    tech: str                    # sky130A | ihp-sg13g2 | gf180mcuD
    has_gds: bool

def detect_context(project_dir: str = ".") -> ProjectContext:
    # 1. Look for info.yaml → parse with tinytapeout.project_info.ProjectInfo
    # 2. Look for tt/ submodule
    # 3. Detect tech: info.yaml pdk field → TT_PDK env var → default sky130A
    # 4. Check for existing GDS in runs/
```

### Script Runner
```python
# src/tinytapeout/cli/runner.py
def run_tt_tool(ctx: ProjectContext, *args: str, capture=False):
    """Run tt_tool.py with the given arguments."""
    cmd = [sys.executable, str(ctx.tt_tools_dir / "tt_tool.py")]
    cmd.extend(["--project-dir", str(ctx.project_dir)])
    if ctx.tech == "ihp-sg13g2":
        cmd.append("--ihp")
    elif ctx.tech == "gf180mcuD":
        cmd.append("--gf")
    cmd.extend(args)
    return subprocess.run(cmd, capture_output=capture, text=True)
```

### Auto-Update Checking
```python
# src/tinytapeout/cli/update_checker.py
# Check PyPI once per day, cache in ~/.config/tinytapeout/update_check.json
# 3-second timeout, never fails the CLI
# Shows: "Update available: 0.1.0 → 0.2.0. Run: pip install --upgrade tinytapeout-cli"
```

---

## Build & Distribution

### pyproject.toml
```toml
[build-system]
requires = ["hatchling", "hatch-vcs"]
build-backend = "hatchling.api"

[project]
name = "tinytapeout-cli"
dynamic = ["version"]
description = "Tiny Tapeout CLI - Design, test, and harden ASIC projects"
requires-python = ">=3.11"
classifiers = [
    "Development Status :: 3 - Alpha",
    "Environment :: Console",
    "Intended Audience :: Developers",
    "Programming Language :: Python :: 3",
    "Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)",
]
dependencies = [
    "click>=8.0",
    "rich>=13.0",
    "PyYAML>=6.0",
    "requests>=2.28",
    "packaging",
]

[project.scripts]
tt = "tinytapeout.cli.app:cli"

[tool.hatch.version]
source = "vcs"

[tool.hatch.build.targets.wheel]
packages = ["src/tinytapeout"]
```

Lightweight base: ~5 pip deps (~15MB). Heavy deps are optional groups, only needed when the corresponding code is migrated into this package (future phases):

```toml
[project.optional-dependencies]
gds = ["klayout>=0.29,<0.30", "gdstk", "CairoSVG", "numpy<2", "matplotlib", "GitPython"]
fpga = ["yowasp-yosys", "mpremote", "configupdater"]
all = ["tinytapeout-cli[gds,fpga]"]
```

Install only what you need:
```bash
pip install tinytapeout-cli          # CLI + light deps (~15MB)
pip install tinytapeout-cli[gds]     # + GDS/hardening deps (~350MB)
pip install tinytapeout-cli[fpga]    # + FPGA deps (~50MB)
pip install tinytapeout-cli[all]     # everything
```

Commands that need heavy deps use **lazy imports** with helpful error messages:
```python
try:
    from tinytapeout.gds import harden_project
except ImportError:
    console.print("[red]Missing dependencies.[/red] Install with: pip install tinytapeout-cli[gds]")
    raise SystemExit(1)
```

This means `tt check`, `tt init`, `tt doctor`, `tt test` all work with zero heavy deps. A user who only does FPGA work never downloads klayout.

### Version management
`hatch-vcs`: version from git tags (`v0.1.0` → `0.1.0`).

### CHANGELOG
Maintain a `CHANGELOG.md` for the tinytapeout-cli package itself (Keep a Changelog format). Updated with each release to document new commands, bug fixes, and breaking changes.

### Project Hygiene (from day 1)

**Pre-commit hooks** (`.pre-commit-config.yaml`):
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.9.6
    hooks:
      - id: ruff          # linting (replaces flake8 + isort)
        args: [--fix]
      - id: ruff-format   # formatting (replaces black)
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
```

**Ruff config** in `pyproject.toml`:
```toml
[tool.ruff]
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]  # pyflakes, pycodestyle, isort, pyupgrade, bugbear
```

**GitHub Actions workflows**:
```
.github/workflows/
├── test.yaml       # pytest + JUnit XML + test-summary/action@v2.4
├── lint.yaml       # pre-commit run --all-files
├── e2e.yaml        # E2E: tt init → check → test → gds build → stats → validate → test --gl (matrix: sky130A, ihp-sg13g2)
└── publish.yaml    # on release → build wheel → publish to PyPI (trusted publishing)
```

All workflows use latest action versions:
- `actions/checkout@v4`
- `actions/setup-python@v6`
- `actions/upload-artifact@v4`
- `test-summary/action@v2.4`

### CI/CD
GitHub Actions: on release → build wheel → publish to PyPI via trusted publishing.

---

## CI / GitHub Actions Migration (tt-gds-action)

**Goal**: `tt-gds-action` (TinyTapeout/tt-gds-action) should migrate to use the `tt` CLI as the single source of truth for hardening, testing, and validation. Today it directly invokes `python tt/tt_tool.py --harden`, `python tt/precheck/precheck.py`, etc. After migration, it calls `tt gds build`, `tt gds validate`, `tt test --gl`, etc.

### Current tt-gds-action structure (8 composite actions)

| Action | Current invocation | CLI equivalent |
|--------|-------------------|----------------|
| Main (harden) | `python tt/tt_tool.py --create-user-config && --harden` | `tt gds build` (calls LibreLane directly) |
| Precheck | `python tt/precheck/precheck.py --gds ... --tech ...` | `tt gds validate` (separate step, requires Nix for klayout/magic) |
| GL Test | `cd test && GATES=yes make` | `tt test --gl` |
| EQY Test | `eqy -f equivalence.eqy` | Future: `tt test --eqy` |
| Docs | `python tt/tt_tool.py --check-docs && --create-pdf` | `tt check` + future `tt docs` |
| Viewer | Copy GDS + redirect to gds-viewer.tinytapeout.com | `tt gds view 3d` (local); action handles Pages deploy |
| Custom GDS | `strm2oas`, copy files, render PNG | Future: `tt gds import` |
| FPGA | `python tt/tt_fpga.py harden` | `tt fpga build` |

### CLI design considerations for CI compatibility

The CLI must work identically in CI and locally. Key considerations:

1. **CI detection**: Auto-detect `GITHUB_ACTIONS=true` or `CI=true` env vars.
   - Suppress Rich spinners/animations in CI (use simple log output)
   - Skip update checks in CI
   - Never prompt interactively in CI (fail with clear error if input needed)

2. **GitHub Step Summary**: When `GITHUB_STEP_SUMMARY` env var is set, write formatted markdown to it.
   - `tt gds build` → writes linter output, routing stats, cell usage to step summary
   - `tt gds validate` → writes precheck results table to step summary
   - `tt test --gl` → writes test results to step summary

3. **Exit codes**: Clear, documented exit codes:
   - 0 = success
   - 1 = command failed (design error, test failure, precheck violation)
   - 2 = environment error (missing tool, bad config)

4. **Machine-readable output**: Support `--json` flag for CI parsing:
   - `tt gds stats --json` → JSON output instead of Rich table
   - `tt gds validate --json` → JSON precheck results

5. **Version pinning**: CI needs reproducible builds:
   - `tt gds build --librelane-version 2.4.2` (pin LibreLane)
   - PDK version tracking via `pdk.json` in submission artifacts

6. **Artifact paths**: Commands should output well-known paths:
   - `tt gds build` → outputs GDS at predictable location
   - `tt gds validate` → writes reports to known directory

### Migration plan for tt-gds-action

**Phase 2** (alongside Init + Testing):
- tt-gds-action starts using `pip install tinytapeout-cli` alongside existing tt-support-tools checkout
- Gradually replace individual `python tt/tt_tool.py` calls with `tt` commands
- Both paths work in parallel during transition

**Phase 3+** (alongside tt-support-tools migration):
- tt-gds-action fully migrates to `tt` CLI commands
- tt-support-tools checkout may still be needed for shuttle-specific actions, but user-facing operations go through `tt`
- The `tools-repo` and `tools-ref` inputs still work (the CLI's runner uses whatever `tt/` submodule is present)

---

## Implementation Phases

### Phase 1: Core CLI + End-to-End Proof (MVP) ✅

**Goal**: Close the loop — every command needed for the full hardening + testing flow works, proven by an E2E GitHub Actions workflow.

**Status: Complete.** All items below are implemented and passing in CI.

1. ✅ Scaffold repo with pyproject.toml, package structure, README, LICENSE, CHANGELOG.md
2. ✅ **Project hygiene from day 1**:
   - Pre-commit hooks: ruff formatter + linter, pre-commit-hooks (trailing-whitespace, end-of-file-fixer, check-yaml, check-toml)
   - GitHub Actions workflows: `test.yaml`, `lint.yaml`, `publish.yaml`, `e2e.yaml`
   - Latest action versions: `actions/checkout@v4`, `actions/setup-python@v6`, `actions/upload-artifact@v4`, `test-summary/action@v2.4`
3. ✅ Migrate `project_info.py`, `project_checks.py`, `tech.py` + tech data files into `tinytapeout/`
4. ✅ Migrate tests; add tests for context detection, tech module (41 tests across 5 test files)
5. ✅ Implement `cli/context.py` (project detection, tech detection from info.yaml → `TT_PDK` → default) and `cli/runner.py` (subprocess wrappers with venv PATH)
6. ✅ Implement CI detection: suppress Rich animations, skip update checks, `write_step_summary()` helper
7. ✅ Implement `tt doctor` (Python, Docker, Git, iverilog version check, PDK, project detection, tt-support-tools)
8. ✅ Implement `tt init` (interactive wizard + non-interactive flags + per-tech template cloning, writes `pdk` to info.yaml)
9. ✅ Implement `tt check` (uses own library directly)
10. ✅ Implement `tt test` + `--gl` (invokes make; iverilog version pre-flight check; test-summary/action in E2E)
11. ✅ Implement `tt gds build` (calls LibreLane directly via `harden.py`; writes stats to step summary)
12. ✅ Implement `tt gds stats` (`--json` for CI)
13. ✅ Implement `tt gds validate` (`--json` for CI; writes to step summary; separate from build)
14. ✅ Implement `tt gds view` subgroup: `2d` (PNG), `3d` (TT viewer in browser), `klayout` (KLayout GUI)
15. ✅ Auto-update checking (24h cache, skipped in CI, 3s timeout)
16. ✅ **End-to-end CI workflow** (`e2e.yaml`): `tt init` → `tt test` → `tt gds build` → `tt test --gl` → `tt gds validate` (via Nix), matrix: sky130A + ihp-sg13g2, both passing

### Phase 2: Polish + Hardening-without-remote + CI Migration

**Goal**: Harden the CLI for real-world usage, add missing validation, and begin migrating tt-gds-action.

17. `tt check` warns if `pdk` field is missing from info.yaml: *"Consider adding 'pdk: sky130A' to info.yaml"*
18. Add `tt check` step to E2E workflow (between init and test)
19. ✅ **Hardening without git remote**: `tt gds build` works immediately after `tt init` — the CLI adds a placeholder git remote if none exists, and `harden.py` falls back gracefully for git metadata (only affects `commit_id.json`, not the design).
20. Add `__main__.py` so `python -m tinytapeout` works
21. Rich progress spinners for long operations (`tt gds build`, `tt test`)
22. **Begin tt-gds-action migration**: tt-gds-action starts using `pip install tinytapeout-cli` alongside tt-support-tools. Gradually replace `python tt/tt_tool.py` calls with `tt` commands (both paths work in parallel).

### Phase 3: FPGA + Setup + Analog Init + Switch Tech + Full Migration
23. Implement `tt setup <tech>` (guided PDK installation)
24. Implement `tt fpga build` (delegates to tt_fpga.py)
25. Implement `tt fpga upload` (delegates to tt_fpga.py)
26. Implement `tt switch-tech <new-tech>` (modifies Makefile GL section, tb.v, workflows, devcontainer, validates tile sizes)
27. Implement `tt init --type analog` (analog project scaffolding):
    - Clone analog template repo
    - Generate customized `magic_init_project.tcl` from tech-specific templates
    - Download appropriate DEF template (`tt_analog_{tiles}.def` or `tt_analog_{tiles}_3v3.def`)
    - Configure analog pins, power stripes, tile size in the TCL script
    - Optionally generate KLayout equivalent setup
    - Supported techs: sky130A, ihp-sg13g2 (not gf180mcuD yet)
28. Shell completion generation
29. **Complete tt-gds-action migration**: all user-facing operations go through `tt` CLI. tt-support-tools checkout only needed for shuttle-specific code.
30. **Begin tt-support-tools migration**: tt-support-tools adds `tinytapeout-cli` as pip dependency and imports shared code. Backward-compat shims at root for submodule users.

### Phase 4: GitHub Publishing + TT App Integration
31. Implement `tt publish` (create GitHub repo via API, push project, enable GH Pages):
    - Use `gh` CLI or GitHub API with user's token
    - Create repo, push, enable Pages with "deploy from Actions" source
    - Non-interactive mode with `--repo`, `--public`, `--enable-pages` flags
32. Implement `tt login` -- authenticate with app.tinytapeout.com (opens browser, stores token locally)
33. Implement `tt submit` (submit project version to TT shuttle via web app API):
    - Authenticate via token from app.tinytapeout.com (stored in `~/.config/tinytapeout/auth.json`)
    - Call `POST /api/projects/submit` with repo URL, commit SHA, shuttle ID
    - Stream SSE response showing submission progress
    - Display project URL and submission version on success
34. Implement `tt submissions` (list all submitted revisions and their details):
    - Fetches submission history from TT web app API
    - Displays: revision number, commit SHA, submission date, status, PR number, workflow run URL
    - Supports `--json` for machine-readable output
    - Mirrors the submissions page on app.tinytapeout.com

### Phase 5: Polish
35. Comprehensive test suite
36. Documentation (README, examples)
37. Error message improvements, edge case handling

---

## Key Files Reference (tt-support-tools)

Files to migrate into `tinytapeout/` library:
- `/workspace/tt-support-tools/project_info.py` (200 lines) -- `ProjectInfo`, `PinoutSection`, `ProjectYamlError`
- `/workspace/tt-support-tools/project_checks.py` (70 lines) -- `check_info_yaml()`, `check_info_md()`
- `/workspace/tt-support-tools/tech.py` (285 lines) -- `TechName`, `Tech` protocol, `Sky130Tech`, `IHPTech`, `GF180MCUDTech`, `tech_map`
- `/workspace/tt-support-tools/tech/sky130A/tile_sizes.yaml` + `cells.json`
- `/workspace/tt-support-tools/tech/ihp-sg13g2/tile_sizes.yaml` + `cells.json`
- `/workspace/tt-support-tools/tech/gf180mcuD/tile_sizes.yaml` + `cells.json`
- `/workspace/tt-support-tools/test_project_info.py` -- existing tests

Analog template files (used by `tt init --type analog` in Phase 3):
- `/workspace/tt-support-tools/tech/sky130A/def/analog/magic_init_project.tcl` -- Magic init for sky130A (met4, 1.2um min width)
- `/workspace/tt-support-tools/tech/ihp-sg13g2/def/analog/magic_init_project.tcl` -- Magic init for IHP (met6, 2.1um min width)
- `/workspace/tt-support-tools/tech/sky130A/def/analog/tt_analog_{1x2,2x2}{,_3v3}.def` -- DEF templates
- `/workspace/tt-support-tools/tech/ihp-sg13g2/def/analog/tt_analog_{1x2,2x2}.def` -- DEF templates

Files the CLI delegates to (via subprocess):
- `/workspace/tt-support-tools/tt_tool.py` -- hardening, stats, rendering, submission
- `/workspace/tt-support-tools/tt_fpga.py` -- FPGA build/upload
- `/workspace/tt-support-tools/precheck/precheck.py` -- DRC validation

tt-gds-action files (to migrate to use `tt` CLI):
- `/workspace/tt-gds-action/action.yml` -- main harden action (15 steps → `tt gds build`)
- `/workspace/tt-gds-action/precheck/action.yml` -- DRC validation (→ `tt gds validate`)
- `/workspace/tt-gds-action/gl_test/action.yml` -- gate-level sim (→ `tt test --gl`)
- `/workspace/tt-gds-action/eqy_test/action.yml` -- formal equivalence (→ future `tt test --eqy`)
- `/workspace/tt-gds-action/docs/action.yml` -- docs generation (→ `tt check` + future `tt docs`)
- `/workspace/tt-gds-action/viewer/action.yml` -- 3D viewer deploy (→ `tt gds view 3d` + Pages deploy)
- `/workspace/tt-gds-action/fpga/ice40up5k/action.yml` -- FPGA bitstream (→ `tt fpga build`)
- `/workspace/tt-gds-action/custom_gds/action.yml` -- pre-made GDS import (→ future `tt gds import`)

---

## tinytapeout-app API Reference (for Phase 4)

The Tiny Tapeout web app (`/workspace/tinytapeout-app/`) is a SolidJS app with Supabase backend:

**Key API endpoints**:
- `POST /api/projects/submit` -- Submit a project version to a shuttle. Returns an SSE stream with progress updates. Creates a GitHub PR in the shuttle repo server-side.
- Authentication: Supabase auth with GitHub OAuth. CLI will need to obtain and store a session token.

**Data model**:
- **Projects**: Have states `Draft → Assigned → Submitted`. Linked to GitHub repos.
- **Submissions**: Versioned per project. Each submission tracks: commit SHA, PR number, workflow run ID, status.
- **Shuttles**: Named runs (e.g. TT10). Projects are assigned to shuttles.

**Key files**:
- `/workspace/tinytapeout-app/src/server/api/projects/submit.ts` -- Submission endpoint (SSE stream)
- `/workspace/tinytapeout-app/src/model/` -- TypeScript types for projects, submissions, shuttles
- `/workspace/tinytapeout-app/src/server/supabase/` -- Database access layer

**CLI integration approach**:
- `tt login` opens browser to `app.tinytapeout.com/cli-auth`, user authorizes, token returned via localhost callback
- Token stored in `~/.config/tinytapeout/auth.json`
- `tt submit` calls the API with the stored token
- Eventually the web app will expose a proper REST API; for now, the CLI uses the same endpoints as the web frontend

---

## Verification Plan

1. **Unit tests**: Test ProjectInfo, project_checks, tech (migrated tests), context detection, update checker
2. **Integration tests**: Create a test project, run `tt check` against it (no heavy deps needed)
3. **E2E tests**: In CI with PDK installed, run `tt gds build` on a sample project
4. **Manual testing**: `pip install -e .` in dev, run full workflow on a real TT project
5. **Cross-platform**: Test on Linux natively, Mac/Windows via Docker
