#!/usr/bin/env python3
"""新增配置中心增强测试：Pydantic 模型、多环境、热重载、CLI。"""

from __future__ import annotations

import time
from pathlib import Path

import pytest
import yaml

from harness_probe.cli import main
from harness_sdk.config import ConfigManager
from harness_sdk.config_models import (
    ExecutorConfig,
    HarnessConfig,
    SandboxConfig,
    validate_config_dict,
)


@pytest.fixture
def cfg_dir(tmp_path: Path) -> Path:
    d = tmp_path / "config"
    d.mkdir()
    return d


def _write_yaml(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# Pydantic 模型校验
# ---------------------------------------------------------------------------

def test_sandbox_config_defaults():
    cfg = SandboxConfig()
    assert cfg.image == "python:3.11-slim"
    assert cfg.timeout == 60.0
    assert cfg.network is False


def test_sandbox_config_validation():
    with pytest.raises(ValueError):
        SandboxConfig(timeout=-1)


def test_executor_config_validates_plugins():
    cfg = ExecutorConfig(plugins={"custom": "my_package.module:MyClass"})
    assert cfg.plugins["custom"] == "my_package.module:MyClass"


def test_executor_config_rejects_invalid_plugin_path():
    with pytest.raises(ValueError, match="plugin path"):
        ExecutorConfig(plugins={"bad": "not_a_valid_path"})


def test_harness_config_round_trip():
    data = HarnessConfig().to_dict()
    parsed = HarnessConfig.from_dict(data)
    assert parsed.executor.default_plugin == "subprocess"


def test_validate_config_dict_empty_passes():
    assert validate_config_dict({}) == []


def test_validate_config_dict_errors_list():
    errors = validate_config_dict({
        "safety": {"mode": "banana"},
    })
    assert errors
    assert any("mode" in err for err in errors)


# ---------------------------------------------------------------------------
# 多环境加载
# ---------------------------------------------------------------------------

def test_env_override_base_file(cfg_dir: Path):
    _write_yaml(cfg_dir / "executor.yaml", {"default_plugin": "subprocess"})
    _write_yaml(cfg_dir / "executor.test.yaml", {"default_plugin": "docker"})
    cfg = ConfigManager.default(config_dir=cfg_dir, env="test")
    assert cfg.get("harness.executor.default_plugin") == "docker"


def test_env_override_harness_wrapped(cfg_dir: Path):
    _write_yaml(cfg_dir / "harness.yaml", {"harness": {"safety": {"mode": "whitelist"}}})
    _write_yaml(cfg_dir / "harness.prod.yaml", {"harness": {"safety": {"mode": "unsafe"}}})
    cfg = ConfigManager.default(config_dir=cfg_dir, env="prod")
    assert cfg.get("harness.safety.mode") == "unsafe"


def test_env_missing_falls_back(cfg_dir: Path):
    _write_yaml(cfg_dir / "executor.yaml", {"default_plugin": "firejail"})
    cfg = ConfigManager.default(config_dir=cfg_dir, env="staging")
    assert cfg.get("harness.executor.default_plugin") == "firejail"


def test_harness_env_variable_priority(cfg_dir: Path, monkeypatch: pytest.MonkeyPatch):
    _write_yaml(cfg_dir / "executor.yaml", {"default_plugin": "subprocess"})
    _write_yaml(cfg_dir / "executor.test.yaml", {"default_plugin": "docker"})
    monkeypatch.setenv("HARNESS_ENV", "test")
    monkeypatch.setenv("HARNESS_EXECUTOR_DEFAULT_PLUGIN", "preview")
    cfg = ConfigManager.default(config_dir=cfg_dir)
    assert cfg.get("harness.executor.default_plugin") == "preview"


def test_cli_env_argument_overrides_env_variable(cfg_dir: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HARNESS_ENV", "prod")
    cfg = ConfigManager.default(config_dir=cfg_dir, env="test")
    assert cfg._env == "test"


# ---------------------------------------------------------------------------
# 热重载与回调
# ---------------------------------------------------------------------------

def test_register_on_reload_and_callback_triggered(cfg_dir: Path):
    _write_yaml(cfg_dir / "audit.yaml", {"log_dir": "/tmp/audit"})
    cfg = ConfigManager.default(config_dir=cfg_dir)
    calls: list = []
    cfg.register_on_reload(lambda m: calls.append(m.to_dict()))
    cfg.watch()
    time.sleep(0.1)
    # Write twice to ensure a real mtime change is detected regardless of initial event
    _write_yaml(cfg_dir / "audit.yaml", {"log_dir": "/tmp/audit-updated-1"})
    time.sleep(1.0)
    _write_yaml(cfg_dir / "audit.yaml", {"log_dir": "/tmp/audit-updated"})
    time.sleep(2.0)
    cfg.stop_watch()
    assert calls
    assert calls[-1]["harness"]["audit"]["log_dir"] == "/tmp/audit-updated"


def test_context_manager_watch(cfg_dir: Path):
    _write_yaml(cfg_dir / "audit.yaml", {"log_dir": "/tmp/audit"})
    with ConfigManager.default(config_dir=cfg_dir).watch() as cfg:
        assert cfg._watch_running is True
    assert cfg._watch_running is False


# ---------------------------------------------------------------------------
# CLI 增强
# ---------------------------------------------------------------------------

def test_cli_config_show_with_env(capsys: pytest.CaptureFixture, tmp_path: Path):
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    _write_yaml(cfg_dir / "executor.yaml", {"default_plugin": "subprocess"})
    _write_yaml(cfg_dir / "executor.test.yaml", {"default_plugin": "docker"})
    code = main(["config", "show", "--config-dir", str(cfg_dir), "--env", "test"])
    captured = capsys.readouterr()
    assert code == 0
    data = yaml.safe_load(captured.out)
    assert data["harness"]["executor"]["default_plugin"] == "docker"


def test_cli_config_validate_env_error(capsys: pytest.CaptureFixture, tmp_path: Path):
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    _write_yaml(cfg_dir / "executor.yaml", {"default_plugin": "subprocess"})
    _write_yaml(cfg_dir / "executor.test.yaml", {"default_plugin": 12345})
    code = main(["config", "validate", "--config-dir", str(cfg_dir), "--env", "test"])
    captured = capsys.readouterr()
    assert code == 2
    assert "default_plugin" in captured.out or "default_plugin" in captured.err


def test_harness_env_cli_run_resolution(monkeypatch: pytest.MonkeyPatch):
    """确认 CLI --env 优先于 HARNESS_ENV 环境变量。"""
    monkeypatch.setenv("HARNESS_ENV", "prod")
    assert main(["config", "show", "--env", "test"]) == 0
