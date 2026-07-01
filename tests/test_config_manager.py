"""ConfigManager unit tests."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from harness_sdk.config import ConfigError, ConfigManager, DEFAULTS


@pytest.fixture
def empty_config_dir(tmp_path: Path) -> Path:
    """返回一个存在的空配置目录。"""
    cfg_dir = tmp_path / "config"
    cfg_dir.mkdir()
    return cfg_dir


def _write_yaml(path: Path, data: dict) -> None:
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def test_default_values_use_builtins(empty_config_dir: Path):
    cfg = ConfigManager.default(config_dir=empty_config_dir)
    assert cfg.get("harness.executor.default_plugin") == "subprocess"
    assert cfg.get("harness.safety.mode") == "whitelist"
    assert cfg.get("harness.audit.retention.max_files") == 100


def test_default_returns_deep_copy(empty_config_dir: Path):
    cfg = ConfigManager.default(config_dir=empty_config_dir)
    data = cfg.to_dict()
    data["harness"]["executor"]["default_plugin"] = "docker"
    assert cfg.get("harness.executor.default_plugin") == "subprocess"


def test_load_executor_config(empty_config_dir: Path):
    _write_yaml(
        empty_config_dir / "executor.yaml",
        {"default_plugin": "docker", "sandbox": {"timeout": 120.0}},
    )
    cfg = ConfigManager.default(config_dir=empty_config_dir)
    assert cfg.get("harness.executor.default_plugin") == "docker"
    assert cfg.get("harness.executor.sandbox.timeout") == 120.0


def test_load_harness_wrapped_config(empty_config_dir: Path):
    _write_yaml(
        empty_config_dir / "harness.yaml",
        {"harness": {"safety": {"mode": "audit"}}},
    )
    cfg = ConfigManager.default(config_dir=empty_config_dir)
    assert cfg.get("harness.safety.mode") == "audit"


def test_load_audit_config(empty_config_dir: Path):
    _write_yaml(
        empty_config_dir / "audit.yaml",
        {"log_dir": "/tmp/audit", "retention": {"max_files": 5}},
    )
    cfg = ConfigManager.default(config_dir=empty_config_dir)
    assert cfg.get("harness.audit.log_dir") == "/tmp/audit"
    assert cfg.get("harness.audit.retention.max_files") == 5


def test_load_safety_config(empty_config_dir: Path):
    _write_yaml(
        empty_config_dir / "safety.yaml",
        {"mode": "unsafe", "config_path": "custom/safety.yaml"},
    )
    cfg = ConfigManager.default(config_dir=empty_config_dir)
    assert cfg.get("harness.safety.mode") == "unsafe"
    assert cfg.get("harness.safety.config_path") == "custom/safety.yaml"


def test_probe_config_legacy_compat(empty_config_dir: Path):
    _write_yaml(
        empty_config_dir / "probe_config.yaml",
        {"probe": {"default_graph": "data/foo.json", "default_depth": 3}},
    )
    cfg = ConfigManager.default(config_dir=empty_config_dir)
    assert cfg.get("harness.probe.default_graph") == "data/foo.json"
    assert cfg.get("harness.probe.default_depth") == 3


def test_env_override_scalar(empty_config_dir: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HARNESS_EXECUTOR_DEFAULT_PLUGIN", "docker")
    monkeypatch.setenv("HARNESS_AUDIT_RETENTION_MAX_FILES", "200")
    monkeypatch.setenv("HARNESS_SAFETY_MODE", "audit")

    cfg = ConfigManager.default(config_dir=empty_config_dir)
    assert cfg.get("harness.executor.default_plugin") == "docker"
    assert cfg.get("harness.audit.retention.max_files") == 200
    assert cfg.get("harness.safety.mode") == "audit"


def test_legacy_env_executor_plugin(empty_config_dir: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HARNESS_EXECUTOR_PLUGIN", "preview")
    cfg = ConfigManager.default(config_dir=empty_config_dir)
    assert cfg.get("harness.executor.default_plugin") == "preview"


def test_cli_override_highest_priority(empty_config_dir: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("HARNESS_EXECUTOR_DEFAULT_PLUGIN", "docker")
    _write_yaml(
        empty_config_dir / "executor.yaml",
        {"default_plugin": "firejail"},
    )
    cfg = ConfigManager.default(config_dir=empty_config_dir)
    cfg.set("harness.executor.default_plugin", "preview")
    assert cfg.get("harness.executor.default_plugin") == "preview"


def test_validate_default_passes(empty_config_dir: Path):
    cfg = ConfigManager.default(config_dir=empty_config_dir)
    assert cfg.validate() == []


def test_validate_type_errors(empty_config_dir: Path):
    _write_yaml(
        empty_config_dir / "audit.yaml",
        {"retention": {"max_files": "100", "max_days": -1}},
    )
    cfg = ConfigManager.default(config_dir=empty_config_dir)
    errors = cfg.validate()
    assert any("max_files" in err for err in errors)
    assert any("max_days" in err for err in errors)


def test_validate_invalid_safety_mode(empty_config_dir: Path):
    _write_yaml(
        empty_config_dir / "safety.yaml",
        {"mode": "unknown"},
    )
    cfg = ConfigManager.default(config_dir=empty_config_dir)
    errors = cfg.validate()
    assert any("harness.safety.mode" in err for err in errors)


def test_invalid_yaml_raises_config_error(empty_config_dir: Path):
    (empty_config_dir / "bad.yaml").write_text("mode: [unclosed", encoding="utf-8")
    with pytest.raises(ConfigError, match="invalid_yaml"):
        ConfigManager.default(config_dir=empty_config_dir)


def test_config_root_must_be_mapping(empty_config_dir: Path):
    (empty_config_dir / "bad.yaml").write_text("- not a mapping", encoding="utf-8")
    with pytest.raises(ConfigError, match="config_root_must_be_mapping"):
        ConfigManager.default(config_dir=empty_config_dir)


def test_missing_config_dir_warns_and_uses_defaults(tmp_path: Path):
    missing = tmp_path / "no_such_config"
    with pytest.warns(UserWarning, match="config_dir_not_found"):
        cfg = ConfigManager.default(config_dir=missing)
    assert cfg.get("harness.executor.default_plugin") == "subprocess"


def test_get_path_expands_user_and_relative(empty_config_dir: Path, tmp_path: Path):
    cfg = ConfigManager.default(config_dir=empty_config_dir, project_root=tmp_path)
    cfg.set("harness.audit.log_dir", "~/audit")
    resolved = cfg.get_path("harness.audit.log_dir")
    assert resolved == Path.home() / "audit"

    cfg.set("harness.audit.log_dir", "rel/audit")
    resolved = cfg.get_path("harness.audit.log_dir")
    assert resolved == (tmp_path / "rel" / "audit").resolve()


def test_set_creates_nested_keys(empty_config_dir: Path):
    cfg = ConfigManager.default(config_dir=empty_config_dir)
    cfg.set("harness.new.section.key", "value")
    assert cfg.get("harness.new.section.key") == "value"


def test_to_dict_is_independent_of_defaults():
    cfg = ConfigManager(DEFAULTS)
    cfg.set("harness.executor.default_plugin", "docker")
    assert DEFAULTS["harness"]["executor"]["default_plugin"] == "subprocess"
