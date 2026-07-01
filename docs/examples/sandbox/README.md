# 沙箱执行器示例

Harness Probe v0.8.2 起支持在隔离沙箱中执行 `contract.verify` 命令。默认不启用，需要显式指定插件。

## 前置条件

- **Docker 沙箱**：安装 Docker 并确保 `docker` 在 `PATH` 中。
- **Firejail 沙箱**：仅 Linux；安装 `firejail`。

## CLI 使用

### Docker 沙箱执行

```bash
harness-probe run \
  --task docs/harness/tasks/active/task_harness_probe_v0_8_2_sandbox_executor_v1.md \
  --executor-plugin docker \
  --sandbox-image python:3.11-slim \
  --sandbox-timeout 60 \
  --sandbox-no-network \
  --sandbox-memory 512m \
  --from-hat 30 --to-hat 40
```

### Firejail 沙箱执行（Linux only）

```bash
harness-probe run \
  --task docs/harness/tasks/active/task_harness_probe_v0_8_2_sandbox_executor_v1.md \
  --executor-plugin firejail \
  --sandbox-timeout 60 \
  --sandbox-no-network \
  --sandbox-memory 512m \
  --from-hat 30 --to-hat 40
```

## 默认配置

`config/executor.yaml` 中 `sandbox` 段提供默认值：

```yaml
sandbox:
  image: python:3.11-slim
  timeout: 60.0
  network: false
  memory: 512m
  cpu: 1.0
```

CLI 参数会覆盖对应默认值。

## SDK 直接使用

```python
import asyncio
from harness_sdk.executor_plugins.docker import DockerExecutor

async def main():
    executor = DockerExecutor(image="alpine:latest", memory="256m")
    result = await executor.run("echo hello")
    print(result.returncode, result.stdout)

asyncio.run(main())
```

## 测试

沙箱相关测试默认不运行：

```bash
# 默认套件
pytest tests/ -q

# 启用 Docker 沙箱测试
HARNESS_TEST_DOCKER=1 pytest tests/test_sandbox_executor.py -v
```

## 失败路径

| 触发条件 | 行为 |
|----------|------|
| Docker 未安装 | `SandboxConfigError: Docker not installed...` |
| Firejail 未安装（Linux） | `SandboxConfigError: firejail not installed...` |
| macOS 使用 Firejail | `SandboxConfigError: Firejail is Linux only...` |
| 沙箱参数非法 | `SandboxConfigError: ...` |
| 命令超时 | `ExecutionResult.timed_out=True` |
