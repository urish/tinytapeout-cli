import os

from rich.console import Console

_is_ci = os.environ.get("CI") == "true" or os.environ.get("GITHUB_ACTIONS") == "true"

console = Console(force_terminal=not _is_ci)


def is_ci() -> bool:
    return _is_ci


def step_summary_path() -> str | None:
    """Return the path to GITHUB_STEP_SUMMARY if running in GitHub Actions."""
    return os.environ.get("GITHUB_STEP_SUMMARY")


def write_step_summary(markdown: str) -> None:
    """Append markdown to the GitHub Actions step summary."""
    path = step_summary_path()
    if path:
        with open(path, "a") as f:
            f.write(markdown + "\n")


def print_status(label: str, message: str, style: str = "green") -> None:
    """Print a status line like:  OK  message"""
    if _is_ci:
        # Plain output for CI
        console.print(f"  {label:4s} {message}")
    else:
        console.print(f"  [{style}]{label:4s}[/{style}] {message}")
