"""Harness SDK · 硬闸异常"""

from __future__ import annotations


class BlockedError(Exception):
    """Harness 硬闸 · 停止后续帽"""

    def __init__(self, message: str, gate_id: str | None = None):
        super().__init__(message)
        self.gate_id = gate_id
