from pathlib import Path

import pytest

# The real tt-support-tools repo, used as single source of truth for tech data
TT_TOOLS_DIR = Path("/workspace/tt-support-tools")


@pytest.fixture
def tt_tools_dir() -> Path:
    """Path to tt-support-tools (single source of truth for tech data)."""
    if not TT_TOOLS_DIR.exists():
        pytest.skip("tt-support-tools not available")
    return TT_TOOLS_DIR
