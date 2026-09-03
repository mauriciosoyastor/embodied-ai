"""TDD Slice 3: context_injector productivo."""

from harness.context_injector import inject


def test_inject_returns_header_and_empty_when_no_fails() -> None:
    md = inject(issue=999, files=["no/such/file.py"], limit=5)
    assert "## Contexto Episódico" in md
    assert "Issue #999" in md
    # no fails with that filter -> empty message
    assert "Sin fallos previos" in md or "tokens" in md


def test_inject_limit_and_format() -> None:
    md = inject(issue=127, files=[], limit=2)
    assert "límite 2" in md
    # should contain verdict:fail lines if any fails exist, else empty
    assert "## Contexto Episódico" in md
