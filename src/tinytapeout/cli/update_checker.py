import json
import time
from pathlib import Path

from tinytapeout.cli.console import console, is_ci

CONFIG_DIR = Path.home() / ".config" / "tinytapeout"
CACHE_FILE = CONFIG_DIR / "update_check.json"
CHECK_INTERVAL = 86400  # 24 hours


def check_for_updates() -> None:
    """Check PyPI for a newer version. Runs at most once per day, never fails the CLI."""
    if is_ci():
        return

    try:
        _do_check()
    except Exception:
        pass  # Never fail the CLI due to update checking


def _do_check() -> None:
    # Read cache
    now = time.time()
    cache = _read_cache()
    if cache and now - cache.get("timestamp", 0) < CHECK_INTERVAL:
        # Show cached notification if there's an update
        if cache.get("update_available"):
            _show_update(cache["latest_version"])
        return

    # Fetch latest version from PyPI
    import requests
    from packaging.version import Version

    from tinytapeout import __version__

    if __version__ == "0.0.0-dev":
        return

    resp = requests.get(
        "https://pypi.org/pypi/tinytapeout-cli/json",
        timeout=3,
    )
    if resp.status_code != 200:
        return

    latest = resp.json()["info"]["version"]
    current = Version(__version__)
    latest_ver = Version(latest)
    update_available = latest_ver > current

    # Write cache
    _write_cache(
        {
            "timestamp": now,
            "latest_version": latest,
            "update_available": update_available,
        }
    )

    if update_available:
        _show_update(latest)


def _show_update(latest_version: str) -> None:
    from tinytapeout import __version__

    console.print(
        f"[dim]Update available: {__version__} -> {latest_version}. "
        f"Run: pip install --upgrade tinytapeout-cli[/dim]"
    )


def _read_cache() -> dict | None:
    try:
        if CACHE_FILE.exists():
            return json.loads(CACHE_FILE.read_text())
    except Exception:
        pass
    return None


def _write_cache(data: dict) -> None:
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps(data))
    except Exception:
        pass
