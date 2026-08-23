# Ticket 029 — Research: Ingeniería de código completa de esos repos

> Label: `wayfinder:research` · Parent: `005-map-repos-enrollment.md` · Estado: cerrado · Resolución: 2026-08-23 · Reclamado por subagente research · AFK

## Question

Para los repos de 028, ¿cumplen ingeniería completa según nuestro repo (`ruff`/`mypy`/`pytest`, `conftest.py`+`pythonpath`, `uv` workspace, `LeakyQueue`/`ABORTED latch`, `ADR`/`CONTEXT`, `WS D5`/`WS_BUFFERED_LIMIT`, `COSINE_THRESHOLD 0.42`/`CAP 5`)? Tabla de madurez y gaps. Identificar lecciones de `docs/agents/lessons/` aplicables (F821, GHA pipe, `conftest.py`, `pythonpath`, `uv.lock`).

Entregable en rama `research/029-ingenieria` con `docs/agents/research/029-ingenieria.md`.

## Resolución

- Rama `research/029-ingenieria` — `docs/agents/research/029-ingenieria.md` (209 líneas)
- 12 criterios: `deepface` 25% (3/12), `CompreFace` 17%, resto 8% vs nuestro 100% (`pyproject.toml:15` `conftest.py:1` `ci.yml:37` `CONTEXT.md:89`); actualizado con brainwagon 2026-04-25 (sin ruff/mypy/uv) y Frigate/yakhyo 2025
- Gaps: `dlib` no-win32, sin `conftest.py`/`uv.lock`, sin `LeakyQueue`/`ABORTED`, thresholds no 0.42, `.gitignore` sin `identities.json`, GHA sin `fromJSON`; lecciones 0001 F821, 0002 GHA, 0004 gitignore aplicables; recomendación mantener 12/12 y ADR

**Desbloquea:** 030
