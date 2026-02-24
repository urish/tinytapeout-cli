import json
from unittest.mock import patch

import pytest

from tinytapeout.cli.environment import ToolInfo
from tinytapeout.cli.precheck_env import (
    RUNNER_NATIVE,
    RUNNER_NIX,
    PrecheckEnv,
    _version_ok,
    detect_precheck_env,
    load_tool_versions,
    wrap_command,
)


class TestLoadToolVersions:
    def test_loads_from_file(self, tmp_path):
        precheck_dir = tmp_path / "precheck"
        precheck_dir.mkdir()
        (precheck_dir / "tool-versions.json").write_text(
            json.dumps({"klayout": "0.29.0", "magic": "8.3.500"})
        )
        result = load_tool_versions(tmp_path)
        assert result.klayout == "0.29.0"
        assert result.magic == "8.3.500"

    def test_errors_when_missing(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="tool-versions.json"):
            load_tool_versions(tmp_path)


class TestVersionOk:
    def test_equal(self):
        assert _version_ok("0.28.17", "0.28.17") is True

    def test_greater(self):
        assert _version_ok("0.29.4", "0.28.17") is True

    def test_less(self):
        assert _version_ok("0.28.16", "0.28.17") is False

    def test_none_version(self):
        assert _version_ok(None, "0.28.17") is False

    def test_magic_version(self):
        assert _version_ok("8.3.489", "8.3.460") is True

    def test_magic_version_too_old(self):
        assert _version_ok("8.3.400", "8.3.460") is False


def _nix_available():
    return ToolInfo(
        name="nix-shell", available=True, version="2.18.1", path="/usr/bin/nix-shell"
    )


def _nix_unavailable():
    return ToolInfo(name="nix-shell", available=False)


def _klayout_available(version="0.30.4"):
    return ToolInfo(
        name="klayout", available=True, version=version, path="/usr/bin/klayout"
    )


def _klayout_unavailable():
    return ToolInfo(name="klayout", available=False)


def _magic_available(version="8.3.568"):
    return ToolInfo(
        name="magic", available=True, version=version, path="/usr/bin/magic"
    )


def _magic_unavailable():
    return ToolInfo(name="magic", available=False)


_DEFAULT_TOOL_VERSIONS = {"klayout": "0.30.4", "magic": "8.3.568"}


def _setup_tt_dir(tmp_path, with_nix_file=True, tool_versions=_DEFAULT_TOOL_VERSIONS):
    """Create a minimal tt dir with precheck directory."""
    precheck_dir = tmp_path / "precheck"
    precheck_dir.mkdir(parents=True, exist_ok=True)
    if with_nix_file:
        (precheck_dir / "default.nix").write_text("# nix")
    if tool_versions is not None:
        (precheck_dir / "tool-versions.json").write_text(json.dumps(tool_versions))
    return tmp_path


class TestDetectPrecheckEnv:
    def test_auto_prefers_nix(self, tmp_path):
        # tool-versions.json not needed when nix is available
        tt_dir = _setup_tt_dir(tmp_path, tool_versions=None)
        with (
            patch(
                "tinytapeout.cli.precheck_env.check_nix", return_value=_nix_available()
            ),
        ):
            result = detect_precheck_env(tt_dir, "auto")
        assert result.runner == RUNNER_NIX
        assert result.nix_file == tt_dir / "precheck" / "default.nix"

    def test_auto_falls_back_to_native(self, tmp_path):
        tt_dir = _setup_tt_dir(tmp_path)
        with (
            patch(
                "tinytapeout.cli.precheck_env.check_nix",
                return_value=_nix_unavailable(),
            ),
            patch(
                "tinytapeout.cli.precheck_env.check_klayout",
                return_value=_klayout_available(),
            ),
            patch(
                "tinytapeout.cli.precheck_env.check_magic",
                return_value=_magic_available(),
            ),
        ):
            result = detect_precheck_env(tt_dir, "auto")
        assert result.runner == RUNNER_NATIVE

    def test_auto_errors_when_nothing_available(self, tmp_path):
        tt_dir = _setup_tt_dir(tmp_path)
        with (
            patch(
                "tinytapeout.cli.precheck_env.check_nix",
                return_value=_nix_unavailable(),
            ),
            patch(
                "tinytapeout.cli.precheck_env.check_klayout",
                return_value=_klayout_unavailable(),
            ),
            patch(
                "tinytapeout.cli.precheck_env.check_magic",
                return_value=_magic_unavailable(),
            ),
            pytest.raises(SystemExit),
        ):
            detect_precheck_env(tt_dir, "auto")

    def test_auto_errors_when_native_too_old(self, tmp_path):
        tt_dir = _setup_tt_dir(
            tmp_path, tool_versions={"klayout": "0.29.0", "magic": "8.3.500"}
        )
        with (
            patch(
                "tinytapeout.cli.precheck_env.check_nix",
                return_value=_nix_unavailable(),
            ),
            patch(
                "tinytapeout.cli.precheck_env.check_klayout",
                return_value=_klayout_available("0.28.0"),
            ),
            patch(
                "tinytapeout.cli.precheck_env.check_magic",
                return_value=_magic_available("8.3.400"),
            ),
            pytest.raises(SystemExit),
        ):
            detect_precheck_env(tt_dir, "auto")

    def test_auto_nix_without_nix_file_skips_nix(self, tmp_path):
        tt_dir = _setup_tt_dir(tmp_path, with_nix_file=False)
        with (
            patch(
                "tinytapeout.cli.precheck_env.check_nix", return_value=_nix_available()
            ),
            patch(
                "tinytapeout.cli.precheck_env.check_klayout",
                return_value=_klayout_available(),
            ),
            patch(
                "tinytapeout.cli.precheck_env.check_magic",
                return_value=_magic_available(),
            ),
        ):
            result = detect_precheck_env(tt_dir, "auto")
        assert result.runner == RUNNER_NATIVE

    def test_explicit_nix(self, tmp_path):
        tt_dir = _setup_tt_dir(tmp_path)
        with patch(
            "tinytapeout.cli.precheck_env.check_nix", return_value=_nix_available()
        ):
            result = detect_precheck_env(tt_dir, "nix")
        assert result.runner == RUNNER_NIX

    def test_explicit_nix_errors_when_unavailable(self, tmp_path):
        tt_dir = _setup_tt_dir(tmp_path)
        with (
            patch(
                "tinytapeout.cli.precheck_env.check_nix",
                return_value=_nix_unavailable(),
            ),
            pytest.raises(SystemExit),
        ):
            detect_precheck_env(tt_dir, "nix")

    def test_explicit_native(self, tmp_path):
        tt_dir = _setup_tt_dir(tmp_path)
        with (
            patch(
                "tinytapeout.cli.precheck_env.check_klayout",
                return_value=_klayout_available(),
            ),
            patch(
                "tinytapeout.cli.precheck_env.check_magic",
                return_value=_magic_available(),
            ),
        ):
            result = detect_precheck_env(tt_dir, "native")
        assert result.runner == RUNNER_NATIVE

    def test_explicit_native_errors_when_missing(self, tmp_path):
        tt_dir = _setup_tt_dir(tmp_path)
        with (
            patch(
                "tinytapeout.cli.precheck_env.check_klayout",
                return_value=_klayout_unavailable(),
            ),
            patch(
                "tinytapeout.cli.precheck_env.check_magic",
                return_value=_magic_available(),
            ),
            pytest.raises(SystemExit),
        ):
            detect_precheck_env(tt_dir, "native")

    def test_explicit_native_errors_when_too_old(self, tmp_path):
        tt_dir = _setup_tt_dir(
            tmp_path, tool_versions={"klayout": "0.29.0", "magic": "8.3.500"}
        )
        with (
            patch(
                "tinytapeout.cli.precheck_env.check_klayout",
                return_value=_klayout_available("0.28.0"),
            ),
            patch(
                "tinytapeout.cli.precheck_env.check_magic",
                return_value=_magic_available("8.3.489"),
            ),
            pytest.raises(SystemExit),
        ):
            detect_precheck_env(tt_dir, "native")


class TestWrapCommand:
    def test_native_passthrough(self):
        env = PrecheckEnv(runner=RUNNER_NATIVE)
        cmd = ["/usr/bin/python", "precheck.py", "--gds", "test.gds"]
        assert wrap_command(env, cmd) == cmd

    def test_nix_wrapping(self, tmp_path):
        nix_file = tmp_path / "default.nix"
        env = PrecheckEnv(runner=RUNNER_NIX, nix_file=nix_file)
        cmd = ["/venv/bin/python", "precheck.py", "--gds", "test.gds"]
        result = wrap_command(env, cmd)
        assert result[0] == "nix-shell"
        assert result[1] == str(nix_file)
        assert result[2] == "--run"
        assert "/venv/bin/python precheck.py --gds test.gds" == result[3]

    def test_nix_wrapping_quotes_spaces(self, tmp_path):
        nix_file = tmp_path / "default.nix"
        env = PrecheckEnv(runner=RUNNER_NIX, nix_file=nix_file)
        cmd = ["/venv/bin/python", "precheck.py", "--gds", "/path with spaces/test.gds"]
        result = wrap_command(env, cmd)
        # shlex.join should quote the path with spaces
        assert (
            "'/path with spaces/test.gds'" in result[3]
            or '"/path with spaces/test.gds"' in result[3]
        )
