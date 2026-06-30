"""Harness Probe · 渲染辅助"""

from __future__ import annotations

from harness_sdk.models import CompiledPrompt


def print_cache_boundary(compiled: CompiledPrompt) -> None:
    try:
        from rich.console import Console
        from rich.panel import Panel

        console = Console()
        static = compiled.static_prefix + compiled.semi_static
        console.print(Panel(static, title="STATIC+SEMI (cache-friendly)", border_style="blue"))
        console.print(
            Panel(
                compiled.dynamic_suffix,
                title="DYNAMIC (recomputed per hat)",
                border_style="yellow",
            )
        )
        total = compiled.static_char_count + compiled.dynamic_char_count
        ratio = compiled.static_char_count / total * 100 if total else 0
        console.print(
            f"[dim]static≈{compiled.static_char_count} chars · "
            f"dynamic≈{compiled.dynamic_char_count} chars · "
            f"static ratio≈{ratio:.0f}%[/dim]"
        )
    except ImportError:
        print("=" * 50)
        print("STATIC+SEMI:", compiled.static_char_count)
        print(compiled.static_prefix + compiled.semi_static)
        print("=" * 50)
        print("DYNAMIC:", compiled.dynamic_char_count)
        print(compiled.dynamic_suffix)
