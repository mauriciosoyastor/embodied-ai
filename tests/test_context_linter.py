"""Slice 5: Guard linter CONTEXT.md."""

from pathlib import Path

from harness.check_context import check


def test_context_linter_passes_on_current_file() -> None:
    assert check(Path("CONTEXT.md")) == 0


def test_context_linter_fails_on_new_anchor(tmp_path: Path) -> None:
    p = tmp_path / "CONTEXT.md"
    p.write_text("foo ws.py:123 bar\n", encoding="utf-8")
    assert check(p) == 1
    # harness allowlist should pass
    p.write_text("harness/harness.py:32 ok\n", encoding="utf-8")
    assert check(p) == 0
    # linter example line should be ignored
    p.write_text("Linter de Documentación \\.py:\\d+ ok\n", encoding="utf-8")
    assert check(p) == 0
