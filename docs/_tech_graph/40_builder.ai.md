# 40_builder · Prompt 三段式组装

## nodes

```yaml
- id: BUILDER
  label: "builder.py"
  kind: service
  module_id: BUILDER
  depends_on: [COMPILER]
  entry_points:
    - "build_hat_prompt"
    - "build_subagent_prompt"
    - "print_cache_boundary"
```

## edges

```yaml
- from: BUILDER
  to: COMPILER
  mark: "->"
  type: depends_on
  label: "format_contract_table / format_wiki_context"
```

## 文件

- `src/builder.py`
