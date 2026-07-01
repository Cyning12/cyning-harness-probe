"""Sandbox executor tests."""

from __future__ import annotations

import os
import shutil
import sys

import pytest

from harness_probe.cli import build_parser
from harness_sdk.executor import load_executor_plugin
from harness_sdk.executor_plugins.docker import DockerExecutor
from harness_sdk.executor_plugins.firejail import FirejailExecutor
from harness_sdk.executor_plugins.sandbox import SandboxConfigError


docker_required = pytest.mark.skipif(
    os.environ.get("HARNESS_TEST_DOCKER") != "1",
    reason="set HARNESS_TEST_DOCKER=1 to run Docker sandbox tests",
)


def test_load_docker_plugin():
    executor = load_executor_plugin("docker")
    assert isinstance(executor, DockerExecutor)


@pytest.mark.skipif(sys.platform != "linux", reason="firejail is Linux only")
def test_load_firejail_plugin():
    executor = load_executor_plugin("firejail")
    assert isinstance(executor, FirejailExecutor)


@pytest.mark.asyncio
@docker_required
async def test_docker_executor_runs_echo():
    executor = DockerExecutor()
    result = await executor.run("echo hello")
    assert result.returncode == 0
    assert result.stdout.strip() == "hello"
    assert not result.timed_out


@pytest.mark.asyncio
@docker_required
async def test_docker_executor_respects_overrides():
    executor = DockerExecutor(
        image="alpine:latest",
        timeout=30.0,
        network=False,
        memory="256m",
    )
    result = await executor.run("echo harness")
    assert result.returncode == 0
    assert "harness" in result.stdout


@pytest.mark.asyncio
async def test_docker_executor_not_installed(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    executor = DockerExecutor()
    with pytest.raises(SandboxConfigError, match="Docker not installed"):
        await executor.run("echo hello")


def test_docker_executor_invalid_image():
    with pytest.raises(SandboxConfigError, match="image must not be empty"):
        DockerExecutor(image="")


def test_docker_executor_invalid_timeout():
    with pytest.raises(SandboxConfigError, match="timeout must be positive"):
        DockerExecutor(timeout=0.0)


@pytest.mark.skipif(sys.platform == "linux", reason="tests the macOS-only error path")
def test_firejail_executor_linux_only_on_mac():
    with pytest.raises(SandboxConfigError, match="Linux only"):
        FirejailExecutor()


@pytest.mark.skipif(sys.platform != "linux", reason="requires Linux")
@pytest.mark.asyncio
async def test_firejail_not_installed_on_linux(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    executor = FirejailExecutor()
    with pytest.raises(SandboxConfigError, match="firejail not installed"):
        await executor.run("echo hello")


def test_cli_sandbox_args_parsed():
    parser = build_parser()
    args = parser.parse_args(
        [
            "run",
            "--executor-plugin",
            "docker",
            "--sandbox-image",
            "alpine:latest",
            "--sandbox-timeout",
            "30",
            "--sandbox-no-network",
            "--sandbox-memory",
            "256m",
        ]
    )
    assert args.executor_plugin == "docker"
    assert args.sandbox_image == "alpine:latest"
    assert args.sandbox_timeout == 30.0
    assert args.sandbox_no_network is True
    assert args.sandbox_memory == "256m"
