# Safety 模式示例（v0.7.1）

## 项目级安全策略文件

仓库根目录已提供 `config/safety.yaml`，演示如何扩展默认白名单与黑名单。

## 三种模式的使用方式

### 1. whitelist（默认）

使用项目配置文件，仅放行白名单内命令：

```bash
python -m harness_probe.cli run \
  --executor real \
  --safety-config config/safety.yaml \
  --from-hat 30 --to-hat 40 \
  --task data/tasks/sample_task.md
```

### 2. audit

`audit` 模式跳过白名单，但仍拦截危险 shell 元字符与危险命令前缀：

```bash
python -m harness_probe.cli run \
  --executor real \
  --safety-mode audit \
  --from-hat 30 --to-hat 40 \
  --task data/tasks/sample_task.md
```

### 3. unsafe

`unsafe` 模式不做任何拦截，但必须显式设置环境变量 `HARNESS_UNSAFE=1`：

```bash
HARNESS_UNSAFE=1 python -m harness_probe.cli run \
  --executor real \
  --safety-mode unsafe \
  --from-hat 30 --to-hat 40 \
  --task data/tasks/sample_task.md
```

## 更多参数

- `--dry-run`：不实际执行命令，仅输出预览
- `--execution-log-dir PATH`：将 executed / blocked / timeout / dry_run 事件写入 `execution_log_<session_id>.jsonl`
