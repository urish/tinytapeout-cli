"""Precheck execution environment detection and command wrapping."""

import json
import shlex
from dataclasses import dataclass
from pathlib import Path

from packaging.version import Version

from tinytapeout.cli.environment import check_klayout, check_magic, check_nix

# Fallback minimums (used when tool-versions.json is missing)
_FALLBACK_MIN_KLAYOUT = "0.28.17"
_FALLBACK_MIN_MAGIC = "8.3.460"

RUNNER_NATIVE = "native"
RUNNER_NIX = "nix"
RUNNER_DOCKER = "docker"


@dataclass
class ToolVersions:
    klayout: str
    magic: str


@dataclass
class PrecheckEnv:
    runner: str  # RUNNER_NATIVE | RUNNER_NIX | RUNNER_DOCKER
    nix_file: Path | None = None


def load_tool_versions(tt_dir: Path) -> ToolVersions:
    """Load minimum tool versions from tt/precheck/tool-versions.json, with fallbacks."""
    versions_file = tt_dir / "precheck" / "tool-versions.json"
    if versions_file.exists():
        data = json.loads(versions_file.read_text())
        return ToolVersions(
            klayout=data.get("klayout", _FALLBACK_MIN_KLAYOUT),
            magic=data.get("magic", _FALLBACK_MIN_MAGIC),
        )
    return ToolVersions(klayout=_FALLBACK_MIN_KLAYOUT, magic=_FALLBACK_MIN_MAGIC)


def _version_ok(actual: str | None, minimum: str) -> bool:
    """Check if actual version meets the minimum requirement."""
    if not actual:
        return False
    try:
        return Version(actual) >= Version(minimum)
    except Exception:
        return False


def detect_precheck_env(tt_dir: Path, requested: str = "auto") -> PrecheckEnv:
    """Detect or validate execution environment for precheck.

    Auto cascade: nix → native (with version check) → error.
    """
    from tinytapeout.cli.console import console

    nix_file = tt_dir / "precheck" / "default.nix"
    versions = load_tool_versions(tt_dir)

    if requested == "auto":
        # 1. Prefer Nix
        nix = check_nix()
        if nix.available and nix_file.exists():
            return PrecheckEnv(runner=RUNNER_NIX, nix_file=nix_file)

        # 2. Try native with version check
        klayout = check_klayout()
        magic = check_magic()
        if (
            klayout.available
            and magic.available
            and _version_ok(klayout.version, versions.klayout)
            and _version_ok(magic.version, versions.magic)
        ):
            return PrecheckEnv(runner=RUNNER_NATIVE)

        # 3. Error
        console.print(
            f"[red]Cannot run precheck: install Nix (recommended), "
            f"or install klayout >= {versions.klayout} and magic >= {versions.magic} natively.[/red]"
        )
        raise SystemExit(2)

    elif requested == RUNNER_NIX:
        nix = check_nix()
        if not nix.available:
            console.print("[red]nix-shell not found on PATH.[/red]")
            raise SystemExit(2)
        if not nix_file.exists():
            console.print(f"[red]Nix file not found: {nix_file}[/red]")
            raise SystemExit(2)
        return PrecheckEnv(runner=RUNNER_NIX, nix_file=nix_file)

    elif requested == RUNNER_NATIVE:
        klayout = check_klayout()
        magic = check_magic()
        errors = []
        if not klayout.available:
            errors.append(f"klayout not found (need >= {versions.klayout})")
        elif not _version_ok(klayout.version, versions.klayout):
            errors.append(
                f"klayout {klayout.version} too old (need >= {versions.klayout})"
            )
        if not magic.available:
            errors.append(f"magic not found (need >= {versions.magic})")
        elif not _version_ok(magic.version, versions.magic):
            errors.append(f"magic {magic.version} too old (need >= {versions.magic})")
        if errors:
            for err in errors:
                console.print(f"[red]{err}[/red]")
            raise SystemExit(2)
        return PrecheckEnv(runner=RUNNER_NATIVE)

    else:
        console.print(f"[red]Unknown runner: {requested}[/red]")
        raise SystemExit(2)


def wrap_command(env: PrecheckEnv, cmd: list[str]) -> list[str]:
    """Wrap a command for the resolved environment."""
    if env.runner == RUNNER_NIX:
        return ["nix-shell", str(env.nix_file), "--run", shlex.join(cmd)]
    return cmd
