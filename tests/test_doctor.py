from tinytapeout.cli.environment import check_git, check_python


def test_python_always_available():
    result = check_python()
    assert result.available is True
    assert "." in result.version


def test_git_returns_tool_info():
    result = check_git()
    assert result.name == "Git"
