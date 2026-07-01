"""Capability model tests."""

from __future__ import annotations

from harness_sdk.capability import (
    Capability,
    CapabilitySet,
    CommandRisk,
    evaluate_command_risk,
    infer_capabilities_from_command,
)


def test_default_capability_set():
    """默认能力集包含 read 与 execute。"""
    assert Capability.network.value == "network"
    assert Capability.shell.value == "shell"
    assert Capability.env.value == "env"
    assert Capability.sudo.value == "sudo"


def test_capability_set_from_strings():
    cs = CapabilitySet(["read", "write"])
    assert Capability.read in cs
    assert Capability.write in cs
    assert Capability.network not in cs
    assert cs.to_list() == ["read", "write"]


def test_capability_set_from_enum():
    cs = CapabilitySet([Capability.read, Capability.execute])
    assert Capability.read in cs
    assert Capability.execute in cs


def test_capability_set_operations():
    a = CapabilitySet(["read", "execute"])
    b = CapabilitySet(["write", "execute"])
    union = a | b
    assert set(union.to_list()) == {"read", "execute", "write"}
    inter = a & b
    assert inter.to_list() == ["execute"]
    diff = a - b
    assert diff.to_list() == ["read"]


def test_capability_set_default():
    cs = CapabilitySet.default()
    assert Capability.read in cs
    assert Capability.execute in cs
    assert Capability.network not in cs


def test_capability_set_all():
    cs = CapabilitySet.all()
    assert len(cs) == len(Capability)


def test_capability_set_issubset():
    a = CapabilitySet(["read"])
    b = CapabilitySet(["read", "execute"])
    assert a.issubset(b)
    assert not b.issubset(a)


def test_capability_set_pydantic_roundtrip():
    from pydantic import BaseModel

    class Model(BaseModel):
        caps: CapabilitySet

    m = Model(caps=["read", "execute"])
    assert Capability.read in m.caps
    data = m.model_dump()
    assert set(data["caps"]) == {"execute", "read"}


def test_infer_capabilities_simple_command():
    required = infer_capabilities_from_command("echo hello")
    assert Capability.execute in required
    assert Capability.read in required


def test_infer_capabilities_write_redirection():
    required = infer_capabilities_from_command("echo x > file.txt")
    assert Capability.write in required
    assert Capability.execute in required


def test_infer_capabilities_network():
    required = infer_capabilities_from_command("curl https://example.com")
    assert Capability.network in required
    assert Capability.execute in required


def test_infer_capabilities_shell():
    required = infer_capabilities_from_command("echo a | cat")
    assert Capability.shell in required


def test_infer_capabilities_env():
    required = infer_capabilities_from_command("echo $HOME")
    assert Capability.env in required


def test_infer_capabilities_sudo():
    required = infer_capabilities_from_command("sudo apt update")
    assert Capability.sudo in required


def test_evaluate_command_risk_safe():
    risk, required, missing, reason = evaluate_command_risk("echo hello")
    assert risk == CommandRisk.safe
    assert not missing
    assert reason is None


def test_evaluate_command_risk_blocked_missing_network():
    risk, required, missing, reason = evaluate_command_risk(
        "curl https://example.com", CapabilitySet.default()
    )
    assert risk == CommandRisk.blocked
    assert Capability.network in missing
    assert "missing_capabilities" in reason


def test_evaluate_command_risk_dangerous_network_granted():
    risk, required, missing, reason = evaluate_command_risk(
        "curl https://example.com", CapabilitySet(["read", "execute", "network"])
    )
    assert risk == CommandRisk.dangerous
    assert not missing


def test_evaluate_command_risk_restricted_shell():
    risk, required, missing, reason = evaluate_command_risk(
        "echo a | cat", CapabilitySet(["read", "execute", "shell"])
    )
    assert risk == CommandRisk.restricted
    assert not missing


def test_evaluate_command_risk_sudo_prohibited_even_granted():
    risk, required, missing, reason = evaluate_command_risk(
        "sudo whoami", CapabilitySet(["read", "execute", "sudo"])
    )
    assert risk == CommandRisk.blocked
    assert "privileged_command_prohibited_in_sandbox" in reason


def test_evaluate_command_risk_extra_capabilities_granted():
    risk, required, missing, reason = evaluate_command_risk(
        "echo hello", CapabilitySet.all()
    )
    assert risk == CommandRisk.safe


def test_capability_set_equality():
    assert CapabilitySet(["read", "execute"]) == CapabilitySet(["execute", "read"])
    assert CapabilitySet(["read"]) != CapabilitySet(["execute"])
    assert CapabilitySet(["read"]) != "not-a-set"


def test_capability_set_repr():
    cs = CapabilitySet(["read"])
    assert "CapabilitySet" in repr(cs)
    assert "'read'" in repr(cs)


def test_capability_set_discard():
    cs = CapabilitySet(["read", "execute"])
    cs.discard("read")
    assert Capability.read not in cs
    cs.discard("network")  # no error
    assert Capability.network not in cs
