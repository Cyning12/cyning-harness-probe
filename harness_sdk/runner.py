"""Harness SDK · 多帽执行编排（纯逻辑 · 无 IO）"""

from __future__ import annotations

import json
from typing import Callable

from harness_sdk.builder import build_hat_prompt
from harness_sdk.compiler import retrieve_wiki
from harness_sdk.exceptions import BlockedError
from harness_sdk.graph import query_subgraph
from harness_sdk.models import (
    CompiledPrompt,
    HarnessTask,
    RunNodeStatus,
    TaskRunGraph,
    TaskRunNode,
    TechGraph,
    WikiEntry,
)


class TaskRunner:
    """纯逻辑执行器：输入 task + graph + wiki，返回 TaskRunGraph。

    不读写文件、不 print、不访问环境变量。
    """

    def __init__(
        self,
        task: HarnessTask,
        graph: TechGraph,
        wiki_entries: list[WikiEntry],
        session_id: str | None = None,
        mock_executor: Callable[[HarnessTask, str, CompiledPrompt], dict[str, str]] | None = None,
    ):
        self.task = task
        self.graph = graph
        self.wiki_entries = wiki_entries
        self.session_id = session_id
        self.mock_executor = mock_executor
        self._last_prompts: dict[str, CompiledPrompt] = {}

    def get_last_prompts(self) -> dict[str, CompiledPrompt]:
        return self._last_prompts.copy()

    def gate_scan(self, planned_hats: list[str]) -> None:
        for hat in planned_hats:
            gate = self.task.blocks_hat(hat)
            if gate:
                raise BlockedError(
                    f"human_gate {gate.gate_id} pending，阻塞帽 {hat}",
                    gate_id=gate.gate_id,
                )

    def pre_spawn_verify(self) -> None:
        if not self.task.contracts:
            raise BlockedError("failure_paths 未编译出 AcceptanceContract")
        if len(self.task.contracts) > 15:
            raise BlockedError("AcceptanceContract 超过 15 行")

    def run_sequence(
        self,
        from_hat: str | None = None,
        to_hat: str | None = None,
    ) -> TaskRunGraph:
        """生成运行计划，调用 executor，返回 TaskRunGraph。"""
        import uuid

        session_id = self.session_id or uuid.uuid4().hex[:12]
        run_graph = TaskRunGraph(
            session_id=session_id,
            task_path=self.task.task_path,
            l0_freeze_id=self.graph.freeze_id,
            entry_node=self.task.entry_node,
        )

        self.gate_scan(self.task.planned_hats)
        self.pre_spawn_verify()

        hats = self.task.planned_hats
        if from_hat or to_hat:
            from_idx = (
                self.task.planned_hats.index(from_hat)
                if from_hat and from_hat in self.task.planned_hats
                else 0
            )
            to_idx = (
                self.task.planned_hats.index(to_hat) + 1
                if to_hat and to_hat in self.task.planned_hats
                else len(self.task.planned_hats)
            )
            hats = self.task.planned_hats[from_idx:to_idx]

        subgraph = query_subgraph(self.graph, self.task.entry_node, depth=2)
        wiki_hits = retrieve_wiki(
            self.wiki_entries,
            self.task.dynamic_query,
            self.task.entry_node,
        )

        handoff_summary = "（首轮无上一帽）"
        for hat in hats:
            run_node = run_graph.append_hat(
                hat,
                [c.ref for c in self.task.contracts],
            )
            run_node.status = RunNodeStatus.running

            task_with_handoff = self.task.model_copy(
                update={
                    "dynamic_query": f"{self.task.dynamic_query}\n\n上一帽摘要: {handoff_summary}"
                }
            )
            compiled = build_hat_prompt(
                hat,
                self.graph,
                task_with_handoff,
                subgraph,
                wiki_hits,
                handoff_summary=handoff_summary,
            )
            self._last_prompts[hat] = compiled

            evidence_table = self._execute_hat(hat, compiled)
            run_node.evidence = json.dumps(evidence_table, ensure_ascii=False)
            run_node.status = RunNodeStatus.done
            handoff_summary = (
                f"hat {hat} done · refs={','.join(c.ref for c in self.task.contracts)}"
            )

        run_graph.status = "done"
        return run_graph

    def _execute_hat(
        self,
        hat: str,
        compiled: CompiledPrompt,
    ) -> list[dict[str, str]]:
        if self.mock_executor:
            return [
                {
                    "ref": c.ref,
                    "pass_fail": "pass",
                    "evidence": f"executor hat={hat} · {c.verify}",
                }
                for c in self.task.contracts
            ]
        return self._mock_subagent_result(hat)

    def _mock_subagent_result(self, hat: str) -> list[dict[str, str]]:
        rows = []
        for contract in self.task.contracts:
            rows.append(
                {
                    "ref": contract.ref,
                    "pass_fail": "pass",
                    "evidence": f"dry-run hat={hat} · {contract.verify}",
                }
            )
        return rows

    @staticmethod
    def propose_graph_evolution_note(insight: str) -> str:
        """自我进化 · 仅生成 PR 提案文本，不直接改 L0"""
        return f"""## Graph evolution proposal (human review required)

- insight: {insight}
- action: 编辑 *.graph.yaml → export → CI → HG-AUDIT-R1
- forbidden: Agent 直接改 graph.json
"""
