import subprocess
from pathlib import Path
from unittest.mock import patch

import yaml
from click.testing import CliRunner

from tinytapeout.cli.commands.init import TEMPLATE_REPOS, init


def _make_fake_template(tmp_path: Path) -> Path:
    """Create a minimal fake template repo for testing (no network)."""
    template_dir = tmp_path / "_template"
    template_dir.mkdir()

    # info.yaml
    info = {
        "yaml_version": 6,
        "project": {
            "title": "",
            "author": "",
            "description": "",
            "language": "Verilog",
            "clock_hz": 0,
            "tiles": "1x1",
            "top_module": "tt_um_example",
            "source_files": ["project.v"],
        },
        "pinout": {
            **{f"ui[{i}]": "" for i in range(8)},
            **{f"uo[{i}]": "" for i in range(8)},
            **{f"uio[{i}]": "" for i in range(8)},
        },
    }
    (template_dir / "info.yaml").write_text(yaml.dump(info, sort_keys=False))

    # src/project.v
    (template_dir / "src").mkdir()
    (template_dir / "src" / "project.v").write_text(
        "module tt_um_example (\n    input wire clk\n);\nendmodule\n"
    )

    # test/tb.v
    (template_dir / "test").mkdir()
    (template_dir / "test" / "tb.v").write_text(
        "  tt_um_example user_project (\n      .clk(clk)\n  );\n"
    )

    # docs/info.md
    (template_dir / "docs").mkdir()
    (template_dir / "docs" / "info.md").write_text("## How it works\n")

    # Initialize as a git repo so clone works
    _git = ["git", "-c", "user.name=Test", "-c", "user.email=test@test.com"]
    subprocess.run([*_git, "init"], cwd=str(template_dir), capture_output=True)
    subprocess.run([*_git, "add", "."], cwd=str(template_dir), capture_output=True)
    subprocess.run(
        [*_git, "commit", "--no-gpg-sign", "-m", "init"],
        cwd=str(template_dir),
        capture_output=True,
    )

    return template_dir


class TestInitCommand:
    def test_creates_project_non_interactive(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        template_dir = _make_fake_template(tmp_path)

        with patch.dict(TEMPLATE_REPOS, {"sky130A": str(template_dir)}):
            runner = CliRunner()
            result = runner.invoke(
                init,
                [
                    "--name",
                    "my_counter",
                    "--tech",
                    "sky130A",
                    "--tiles",
                    "1x1",
                    "--author",
                    "Test Author",
                    "--description",
                    "A simple counter",
                    "--clock-hz",
                    "50000000",
                    "--language",
                    "Verilog",
                ],
            )

        assert result.exit_code == 0, result.output
        project_dir = tmp_path / "tt_um_my_counter"
        assert project_dir.exists()

    def test_patches_info_yaml(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        template_dir = _make_fake_template(tmp_path)

        with patch.dict(TEMPLATE_REPOS, {"sky130A": str(template_dir)}):
            runner = CliRunner()
            runner.invoke(
                init,
                [
                    "--name",
                    "my_counter",
                    "--tech",
                    "sky130A",
                    "--tiles",
                    "1x2",
                    "--author",
                    "Jane",
                    "--description",
                    "counter",
                    "--clock-hz",
                    "10000000",
                    "--language",
                    "SystemVerilog",
                ],
            )

        info_path = tmp_path / "tt_um_my_counter" / "info.yaml"
        with open(info_path) as f:
            data = yaml.safe_load(f)

        assert data["project"]["top_module"] == "tt_um_my_counter"
        assert data["project"]["title"] == "tt_um_my_counter"
        assert data["project"]["author"] == "Jane"
        assert data["project"]["description"] == "counter"
        assert data["project"]["clock_hz"] == 10000000
        assert data["project"]["tiles"] == "1x2"
        assert data["project"]["language"] == "SystemVerilog"

    def test_renames_module_in_source_files(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        template_dir = _make_fake_template(tmp_path)

        with patch.dict(TEMPLATE_REPOS, {"sky130A": str(template_dir)}):
            runner = CliRunner()
            runner.invoke(
                init,
                [
                    "--name",
                    "my_counter",
                    "--tech",
                    "sky130A",
                    "--tiles",
                    "1x1",
                    "--author",
                    "Test",
                    "--description",
                    "desc",
                    "--clock-hz",
                    "0",
                    "--language",
                    "Verilog",
                ],
            )

        project_dir = tmp_path / "tt_um_my_counter"
        project_v = (project_dir / "src" / "project.v").read_text()
        assert "tt_um_my_counter" in project_v
        assert "tt_um_example" not in project_v

        tb_v = (project_dir / "test" / "tb.v").read_text()
        assert "tt_um_my_counter" in tb_v
        assert "tt_um_example" not in tb_v

    def test_initializes_fresh_git_repo(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        # Configure git user so the initial commit succeeds in any environment
        monkeypatch.setenv("GIT_AUTHOR_NAME", "Test")
        monkeypatch.setenv("GIT_AUTHOR_EMAIL", "test@test.com")
        monkeypatch.setenv("GIT_COMMITTER_NAME", "Test")
        monkeypatch.setenv("GIT_COMMITTER_EMAIL", "test@test.com")
        monkeypatch.setenv("GIT_CONFIG_GLOBAL", "/dev/null")
        template_dir = _make_fake_template(tmp_path)

        with patch.dict(TEMPLATE_REPOS, {"sky130A": str(template_dir)}):
            runner = CliRunner()
            runner.invoke(
                init,
                [
                    "--name",
                    "my_counter",
                    "--tech",
                    "sky130A",
                    "--tiles",
                    "1x1",
                    "--author",
                    "Test",
                    "--description",
                    "desc",
                    "--clock-hz",
                    "0",
                    "--language",
                    "Verilog",
                ],
            )

        project_dir = tmp_path / "tt_um_my_counter"
        assert (project_dir / ".git").exists()

        # Check it's a fresh repo (not the template's history)
        result = subprocess.run(
            ["git", "log", "--oneline"],
            cwd=str(project_dir),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        lines = result.stdout.strip().splitlines()
        assert len(lines) == 1
        assert "Initial commit" in lines[0]

    def test_rejects_existing_directory(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        (tmp_path / "tt_um_existing").mkdir()

        runner = CliRunner()
        result = runner.invoke(
            init,
            [
                "--name",
                "existing",
                "--tech",
                "sky130A",
                "--tiles",
                "1x1",
                "--author",
                "Test",
                "--description",
                "desc",
                "--clock-hz",
                "0",
                "--language",
                "Verilog",
            ],
        )
        assert result.exit_code == 1
        assert "already exists" in result.output

    def test_rejects_invalid_name(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(
            init,
            [
                "--name",
                "123bad",
                "--tech",
                "sky130A",
                "--tiles",
                "1x1",
                "--author",
                "Test",
                "--description",
                "desc",
                "--clock-hz",
                "0",
                "--language",
                "Verilog",
            ],
        )
        assert result.exit_code != 0
        assert "must start with a letter" in result.output

    def test_ihp_tech(self, tmp_path: Path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        template_dir = _make_fake_template(tmp_path)

        with patch.dict(TEMPLATE_REPOS, {"ihp-sg13g2": str(template_dir)}):
            runner = CliRunner()
            result = runner.invoke(
                init,
                [
                    "--name",
                    "ihp_test",
                    "--tech",
                    "ihp-sg13g2",
                    "--tiles",
                    "1x1",
                    "--author",
                    "Test",
                    "--description",
                    "IHP project",
                    "--clock-hz",
                    "0",
                    "--language",
                    "Verilog",
                ],
            )

        assert result.exit_code == 0, result.output
        project_dir = tmp_path / "tt_um_ihp_test"
        assert project_dir.exists()
