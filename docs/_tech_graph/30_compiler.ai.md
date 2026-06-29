# 30_compiler · task parser + contract compiler

## nodes

```yaml
- id: COMPILER
  label: "compiler.py"
  kind: service
  module_id: COMPILER
  depends_on: [MODELS]
  entry_points:
    - "parse_task_markdown"
    - "compile_contracts_from_task"
    - "validate_human_gate_rules"
    - "parse_human_gates"
    - "retrieve_wiki"
```

## edges

```yaml
- from: COMPILER
  to: MODELS
  mark: "->"
  type: depends_on
  label: "AcceptanceContract / HumanGate / HarnessTask / WikiEntry"
```

## 文件

- `src/compiler.py`
