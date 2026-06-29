"""Harness Agent Core · 探针版（dry-run · 无 LLM）"""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from src.builder import build_hat_prompt, print_cache_boundary
from src.compiler import load_wiki_stub, parse_task_markdown, retrieve_wiki
from src.graph_loader import load_graph, query_subgraph
from src.models import BlockedError, HarnessTask, RunNodeStatus, TaskRunGraph, TechGraph


class HarnessProbeCore:
    """大脑=（未来）LLM ·  Harness=本 Core 托底"""

    def __init__(
        self,
        graph: TechGraph,
        wiki_path: str | Path,
        output_dir: str | Path = "outputs",
    ):
        self.graph = graph
        self.wiki_entries = load_wiki_stub(wiki_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def gate_scan(self, task: HarnessTask, planned_hats: list[str]) -> None:
        for hat in planned_hats:
            gate = task.blocks_hat(hat)
            if gate:
                raise BlockedError(
                    f"human_gate {gate.gate_id} pending，阻塞帽 {hat}",
                    gate_id=gate.gate_id,
                )

    def pre_spawn_verify(self, task: HarnessTask) -> None:
        if not task.contracts:
            raise BlockedError("failure_paths 未编译出 AcceptanceContract")
        if len(task.contracts) > 15:
            raise BlockedError("AcceptanceContract 超过 15 行")

    def run_task(
        self,
        task: HarnessTask,
        dry_run: bool = True,
        show_prompt: bool = True,
        from_hat: str | None = None,
        to_hat: str | None = None,
    ) -> TaskRunGraph:
        session_id = uuid.uuid4().hex[:12]
        run_graph = TaskRunGraph(
            session_id=session_id,
            task_path=task.task_path,
            l0_freeze_id=self.graph.freeze_id,
            entry_node=task.entry_node,
        )

        self.gate_scan(task, task.planned_hats)
        self.pre_spawn_verify(task)

        hats = task.planned_hats
        if from_hat or to_hat:
            from_idx = task.planned_hats.index(from_hat) if from_hat and from_hat in task.planned_hats else 0
            to_idx = task.planned_hats.index(to_hat) + 1 if to_hat and to_hat in task.planned_hats else len(task.planned_hats)
            hats = task.planned_hats[from_idx:to_idx]


        subgraph = query_subgraph(self.graph, task.entry_node, depth=2)
        wiki_hits = retrieve_wiki(
            self.wiki_entries,
            task.dynamic_query,
            task.entry_node,
        )

        handoff_summary = "（首轮无上一帽）"
        for hat in hats:
            run_node = run_graph.append_hat(
                hat,
                [c.ref for c in task.contracts],
            )
            run_node.status = RunNodeStatus.running

            task_with_handoff = task.model_copy(
                update={
                    "dynamic_query": f"{task.dynamic_query}\n\n上一帽摘要: {handoff_summary}"
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

            prompt_path = self.output_dir / f"prompt_{session_id}_hat{hat}.md"
            prompt_path.write_text(compiled.full_text, encoding="utf-8")

            if show_prompt:
                print(f"\n--- hat {hat} · {prompt_path} ---")
                print_cache_boundary(compiled)

            if dry_run:
                # 模拟 Subagent 回报与 contract 验收
                evidence_table = self._mock_subagent_result(task, hat)
                run_node.evidence = json.dumps(evidence_table, ensure_ascii=False)
                run_node.status = RunNodeStatus.done
                handoff_summary = f"hat {hat} done · refs={','.join(c.ref for c in task.contracts)}"
            else:
                raise NotImplementedError("非 dry_run 模式尚未接入 LLM（见 README 路线图）")

        run_graph.status = "done"
        self._persist_run_graph(run_graph)
        return run_graph

    def _mock_subagent_result(self, task: HarnessTask, hat: str) -> list[dict[str, str]]:
        rows = []
        for contract in task.contracts:
            rows.append(
                {
                    "ref": contract.ref,
                    "pass_fail": "pass",
                    "evidence": f"dry-run hat={hat} · {contract.verify}",
                }
            )
        return rows

    def _persist_run_graph(self, run_graph: TaskRunGraph) -> Path:
        path = self.output_dir / f"task_run_{run_graph.session_id}.json"
        path.write_text(
            run_graph.model_dump_json(indent=2),
            encoding="utf-8",
        )
        return path

    def propose_graph_evolution_note(self, insight: str) -> str:
        """自我进化 · 仅生成 PR 提案文本，不直接改 L0"""
        return f"""## Graph evolution proposal (human review required)

- insight: {insight}
- action: 编辑 *.graph.yaml → export → CI → HG-AUDIT-R1
- forbidden: Agent 直接改 graph.json
"""
