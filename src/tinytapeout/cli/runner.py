import os
import shutil
import subprocess
from pathlib import Path

from tinytapeout.cli.context import ProjectContext, _tt_tools_python


def run_tt_tool(
    ctx: ProjectContext,
    *args: str,
    capture: bool = False,
) -> subprocess.CompletedProcess:
    """Run tt_tool.py with the given arguments."""
    tt_dir = ctx.require_tt_tools()

    cmd = [_tt_tools_python(tt_dir), str(tt_dir / "tt_tool.py")]
    cmd.extend(["--project-dir", str(ctx.project_dir)])
    if ctx.tech == "ihp-sg13g2":
        cmd.append("--ihp")
    elif ctx.tech == "gf180mcuD":
        cmd.append("--gf")
    cmd.extend(args)
    return subprocess.run(cmd, capture_output=capture, text=True, cwd=str(ctx.project_dir))


def run_precheck(
    ctx: ProjectContext,
    gds_path: str,
    *args: str,
    capture: bool = False,
) -> subprocess.CompletedProcess:
    """Run precheck.py with the given arguments."""
    tt_dir = ctx.require_tt_tools()

    precheck_script = tt_dir / "precheck" / "precheck.py"
    if not precheck_script.exists():
        from tinytapeout.cli.console import console

        console.print(
            f"[red]Precheck script not found at {precheck_script}.[/red]\n"
            "Try updating tt-support-tools: git -C tt pull"
        )
        raise SystemExit(2)

    cmd = [_tt_tools_python(tt_dir), str(precheck_script)]
    cmd.extend(["--gds", gds_path])
    cmd.extend(args)
    return subprocess.run(cmd, capture_output=capture, text=True)


def run_make(
    directory: str,
    *args: str,
    env: dict[str, str] | None = None,
    capture: bool = False,
) -> subprocess.CompletedProcess:
    """Run make in the given directory."""
    cmd = ["make", "-C", directory]
    cmd.extend(args)

    run_env = os.environ.copy()
    if env:
        run_env.update(env)

    return subprocess.run(cmd, capture_output=capture, text=True, env=run_env)


_NIX_CONF_REQUIRED = {
    "experimental-features": "nix-command flakes",
    "sandbox": "false",
    "extra-substituters": "https://nix-cache.fossi-foundation.org",
    "extra-trusted-public-keys": "nix-cache.fossi-foundation.org:3+K59iFwXqKsL7BNu6Guy0v+uTlwsxYQxjspXzqLYQs=",
}


def ensure_nix_config() -> None:
    """Ensure ~/.nix-portable/conf/nix.conf has required settings."""
    conf_dir = Path.home() / ".nix-portable" / "conf"
    conf_file = conf_dir / "nix.conf"

    existing = {}
    if conf_file.exists():
        for line in conf_file.read_text().splitlines():
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                key, _, value = line.partition("=")
                existing[key.strip()] = value.strip()

    missing = {k: v for k, v in _NIX_CONF_REQUIRED.items() if existing.get(k) != v}
    if not missing:
        return

    from tinytapeout.cli.console import console

    conf_dir.mkdir(parents=True, exist_ok=True)
    # Merge: update existing with required values
    existing.update(missing)
    lines = [f"{k} = {v}" for k, v in existing.items()]
    conf_file.write_text("\n".join(lines) + "\n")
    console.print(f"Updated {conf_file} with FOSSi cache settings.")


def _fix_nix_store_permissions() -> None:
    """Work around proot not being able to set permissions on nix store paths.

    When nix-portable uses proot (no user namespaces), nix builds fail with
    'cp: setting permissions' because proot can't intercept chmod on the
    FUSE-mounted store.  Pre-setting u+w on read-only source directories fixes this.
    """
    store_dir = Path.home() / ".nix-portable" / "nix" / "store"
    if not store_dir.is_dir():
        return
    for entry in store_dir.iterdir():
        # Only fix read-only directories (source archives fetched by nix)
        # Skip files, symlinks, and already-writable directories
        if not entry.is_dir() or entry.is_symlink():
            continue
        try:
            st = entry.stat()
            if not (st.st_mode & 0o200):  # not owner-writable
                subprocess.run(
                    ["chmod", "-R", "u+w", str(entry)],
                    capture_output=True,
                )
        except OSError:
            pass


def run_librelane_nix(
    ctx: ProjectContext,
    version: str,
    hide_progress: bool = False,
) -> subprocess.CompletedProcess:
    """Run librelane via nix-portable nix run."""
    from tinytapeout.cli.console import console

    # Verify nix-portable is available
    if not shutil.which("nix-portable"):
        console.print("[red]nix-portable not found. Install it first.[/red]")
        raise SystemExit(2)

    ensure_nix_config()

    # Clean and recreate runs/wokwi
    runs_dir = ctx.project_dir / "runs" / "wokwi"
    if runs_dir.exists():
        shutil.rmtree(runs_dir)
    runs_dir.mkdir(parents=True)

    # Build the command
    flake_ref = f"github:librelane/librelane/{version}"

    # Fetch the flake first (downloads sources to nix store)
    console.print(f"Fetching LibreLane {version} ...")
    subprocess.run(
        [
            "nix-portable", "nix", "flake", "prefetch", flake_ref,
            "--extra-substituters", "https://nix-cache.fossi-foundation.org",
            "--extra-trusted-public-keys",
            "nix-cache.fossi-foundation.org:3+K59iFwXqKsL7BNu6Guy0v+uTlwsxYQxjspXzqLYQs=",
        ],
        capture_output=True,
    )

    # Workaround: proot can't chmod in the nix store, so pre-fix permissions
    _fix_nix_store_permissions()

    cmd = [
        "nix-portable", "nix", "run", flake_ref,
        "--extra-substituters", "https://nix-cache.fossi-foundation.org",
        "--extra-trusted-public-keys",
        "nix-cache.fossi-foundation.org:3+K59iFwXqKsL7BNu6Guy0v+uTlwsxYQxjspXzqLYQs=",
        "--",
    ]

    # PDK args
    if ctx.tech == "ihp-sg13g2":
        cmd.extend(["--pdk", "ihp-sg13g2"])
    elif ctx.tech == "gf180mcuD":
        cmd.extend(["--pdk", "gf180mcuD"])

    cmd.extend(["--run-tag", "wokwi", "--force-run-dir", str(runs_dir)])

    if hide_progress:
        cmd.append("--hide-progress-bar")

    # Config file produced by --create-user-config
    config_file = ctx.project_dir / "src" / "config_merged.json"
    if not config_file.exists():
        console.print(f"[red]Config file not found: {config_file}[/red]")
        raise SystemExit(1)
    cmd.append(str(config_file))

    console.print(f"Running: nix-portable nix run {flake_ref} ...")
    return subprocess.run(cmd, cwd=str(ctx.project_dir))
