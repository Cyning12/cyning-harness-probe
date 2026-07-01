"""CLI config subcommand tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from harness_probe.cli import main


@pytest.fixture
def empty_config_dir(tmp_path: Path) -> Path:
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    return cfg_dir


def _write_yaml(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def test_config_validate_passes(capsys: pytest.CaptureFixture):
    code = main(["config", "validate"])
    captured = capsys.readouterr()
    assert code == 0
    assert "OK" in captured.out


def test_config_show_json(capsys: pytest.CaptureFixture):
    code = main(["config", "show"])
    captured = capsys.readouterr()
    assert code == 0
    data = json.loads(captured.out)
    assert data["harness"]["executor"]["default_plugin"] == "subprocess"


def test_config_show_yaml(capsys: pytest.CaptureFixture):
    code = main(["config", "show", "--format", "yaml"])
    captured = capsys.readouterr()
    assert code == 0
    data = yaml.safe_load(captured.out)
    assert data["harness"]["safety"]["mode"] == "whitelist"


def test_config_show_markdown(capsys: pytest.CaptureFixture):
    code = main(["config", "show", "--format", "markdown"])
    captured = capsys.readouterr()
    assert code == 0
    assert "当前合并配置" in captured.out
    assert "harness.executor.default_plugin" in captured.out


def test_config_validate_with_custom_dir(empty_config_dir: Path, capsys: pytest.CaptureFixture):
    _write_yaml(
        empty_config_dir / "executor.yaml",
        {"default_plugin": "docker"},
    )
    code = main(["config", "validate", "--config-dir", str(empty_config_dir)])
    captured = capsys.readouterr()
    assert code == 0
    assert "OK" in captured.out


def test_config_validate_type_error(empty_config_dir: Path, capsys: pytest.CaptureFixture):
    _write_yaml(
        empty_config_dir / "audit.yaml",
        {"retention": {"max_files": "not-an-int"}},
    )
    code = main(["config", "validate", "--config-dir", str(empty_config_dir)])
    captured = capsys.readouterr()
    assert code == 2
    assert "max_files" in captured.out or "max_files" in captured.err


def test_config_validate_invalid_yaml(empty_config_dir: Path, capsys: pytest.CaptureFixture):
    (empty_config_dir / "bad.yaml").write_text("mode: [unclosed", encoding="utf-8")
    code = main(["config", "validate", "--config-dir", str(empty_config_dir)])
    captured = capsys.readouterr()
    assert code == 2
    assert "invalid_yaml" in captured.out or "invalid_yaml" in captured.err


def test_config_show_with_env_override(capsys: pytest.CaptureFixture, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HARNESS_EXECUTOR_DEFAULT_PLUGIN", "docker")
    code = main(["config", "show"])
    captured = capsys.readouterr()
    assert code == 0
    data = json.loads(captured.out)
    assert data["harness"]["executor"]["default_plugin"] == "docker"


def test_config_help():
    with pytest.raises(SystemExit) as exc_info:
        main(["config", "--help"])
    assert exc_info.value.code == 0
