# 配置中心示例

Harness Probe v0.9.2 引入统一配置中心 `harness_sdk/config.py`，集中加载 `config/*.yaml`、环境变量 `HARNESS_*` 与 CLI 参数，按优先级合并：

```
默认值 < 配置文件 < 环境变量 < 命令行参数
```

## 配置文件

`config/` 目录下的 YAML 会被自动加载：

| 文件 | 命名空间 | 说明 |
|------|----------|------|
| `config/executor.yaml` | `harness.executor` | 默认执行器插件、插件映射、沙箱默认参数 |
| `config/audit.yaml` | `harness.audit` | 审计日志目录与保留策略 |
| `config/safety.yaml` | `harness.safety` | 安全模式、白名单/黑名单 |
| `config/probe_config.yaml` | `harness.probe` | Probe CLI 默认路径与参数 |

配置文件可使用 `harness:` 顶层包裹，也可使用旧格式（按文件名推断命名空间）。

## 环境变量覆盖

| 环境变量 | 配置键 |
|----------|--------|
| `HARNESS_EXECUTOR_DEFAULT_PLUGIN` | `harness.executor.default_plugin` |
| `HARNESS_AUDIT_LOG_DIR` | `harness.audit.log_dir` |
| `HARNESS_AUDIT_RETENTION_MAX_FILES` | `harness.audit.retention.max_files` |
| `HARNESS_AUDIT_RETENTION_MAX_DAYS` | `harness.audit.retention.max_days` |
| `HARNESS_SAFETY_MODE` | `harness.safety.mode` |
| `HARNESS_SAFETY_CONFIG_PATH` | `harness.safety.config_path` |

示例：

```bash
HARNESS_EXECUTOR_DEFAULT_PLUGIN=docker \
HARNESS_SAFETY_MODE=audit \
  harness-probe run --task data/tasks/sample_task.md
```

## CLI 配置命令

```bash
# 校验配置并返回退出码
harness-probe config validate

# 查看当前合并后的配置（JSON）
harness-probe config show

# 查看当前配置（YAML / Markdown）
harness-probe config show --format yaml
harness-probe config show --format markdown

# 指定配置目录
harness-probe config validate --config-dir ./my-config
```

## SDK 直接使用

```python
from harness_sdk import ConfigManager

cfg = ConfigManager.default()
print(cfg.get("harness.executor.default_plugin"))

# CLI 覆盖（最高优先级）
cfg.set("harness.executor.default_plugin", "docker")
```

## 失败路径

| 触发条件 | 行为 |
|----------|------|
| 配置目录不存在 | 使用内置默认值并发出警告 |
| YAML 格式损坏 | `config validate` 退出码 2，给出文件路径与原因 |
| 配置值类型错误 | `config validate` 退出码 2，指出字段与期望类型 |
| 环境变量为非法值 | `config validate` 退出码 2，指出变量名与原因 |
