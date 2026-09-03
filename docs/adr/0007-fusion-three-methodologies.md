# 0007 — Fusión de las tres metodologías en Golden Path único

Fusión eficaz de **(1) Skills Matt Pocock** (`wayfinder/triage/to-tickets/tdd/code-review`), **(2) GitNexus** (`impact/detect_changes/pdg_query`), y **(3) Metodología repo** (`AGENTS.md` aprobación + `harness P-E-V` `harness/harness.py:32` + paridad CI `AGENTS.md:10`) en un pipeline obligatorio **Golden Path Fusión**.

**Status**: accepted (2026-09-03, map #121 ticket #122).

**Context**: El repo tenía las tres piezas sueltas: 42 skills Matt instaladas pero sin `docs/agents/domain.md` y `triage-labels.md`; GitNexus indexado `7748 nodes/19957 edges` con PDG recién en `pdg:true` pero sin gate en Harness; CI desalineado `ci.yml:16` `pip` vs `ci.yml:58` `uv` y `CONTEXT.md:110` contaminado con `ws.py:197 run_inference` (caso de estudio de anti-pattern: glosario con números de línea efímeros que degrada a doc vivo). Necesitábamos decidir si especulamos (tocar `plataforma/`) o preparamos terreno (Spec + configs base).

**Decision**: **Spec A — Plan, don't do.** Documentar la fusión en este ADR + configs base reversibles, sin tocar `plataforma/` en este mapa. Secuencia canónica `Golden Path Fusión`: `Issue → triage(needs-triage→ready-for-agent) → wayfinder? → to-tickets(tracer-bullet) → gitnexus-plan(impact+pdg) → gitnexus-work(+harness verify) → code-review(two-axes) → merge humano`. Pin `.gitnexusrc` `{"pdg": true}` para evitar rebuild 18.5s. DoD checklist de 4 puntos: `uv run ruff format --check . && ruff check . && mypy plataforma/webcam && pytest plataforma/webcam -q` local = `ci.yml` `uv sync --all-packages`; `status --json` `runnerIdentityStatus:current`; `harness verify verdict:ok` `risk:low`; `detect_changes` sin `HIGH` ignorado. `impact_ratio` solo observado. Linter doc: regex `\.py:\d+` en `CONTEXT.md` bloquea inyección futura.

**Considered Options**:
- **Spec B — tocar `plataforma/` ya**: descartada — drift altísimo sin reglas asimiladas; el agente aún no tiene `MUST impact before edit` interiorizado.
- **`--embeddings` 150MB/30s**: descartado P0 — PDG da 100% de mapeo AST de control-flujo; embeddings no justifican costo hasta que `query` keyword falle.
- **`pip install` vs `uv sync`**: `pip` descartado — rompe `uv.lock` y `lessons/0006-reuse-selectivo`; `uv sync --all-packages` garantiza paridad `AGENTS.md:10`.
- **Multi-context `CONTEXT-MAP.md`**: descartado — `CONTEXT.md` single-context glosario puro; detalles `ws.py:204 _passes_whitelist`, `yolo.py:300` migran a ADR/prototype, no a glosario.

**Consequences**:
- **Caso contaminación**: `ws.py:197` citado como anti-pattern; `CONTEXT.md:131` Whitelist W30 pierde números de línea a futuro via linter; histéresis `N=5` y `ReID N=3` permanecen como conceptos, no como anclas `ws.py:204`.
- **Reversibilidad**: bajo costo (5min) `pdg:true`, `ci.yml` uv; alto costo (semi-irreversible) `triage-labels.md`, `CONTEXT.md` single-context — cambiar labels requiere migración de issues.
- **Downstream**: tickets #123-#128 desbloqueados; `harness/context_injector.py` y `impact_ratio` quedan para prototipos; `pre-commit` `ruff+mypy+pytest` es gate P0, GitNexus gate es P1 en Harness.

**Purga Golden Path puro (2026-09-03, spec draft local):**
- **Removed tools**: `harness/prototype-context-injector.py`, `harness/prototype-harness-detect.html`, `prototype-memoria-objetos.html`, `plataforma/webcam/frontend/prototype-imgsz-small.html`, `plataforma/webcam/frontend/prototype-leaky-reid.html`, `.scratch/*` (graph.html, pr_body.md, plegado-productivo, correcciones-percepcion-v2), `out.txt`, `.github/workflows/agent-implement.yml.disabled`, logs `*.err/*.log`. Archivados vía git history (reversible).
- **Conservado**: `ci.yml` + `agent-review.yml` únicos, `.gitnexusrc pdg:true`, `domain.md`/`triage-labels.md`/`issue-tracker.md`, `CONTEXT.md` linter OK, `harness P-E-V` con `TrajectoryEntry.removed_tools: list[str]` para auditoría.
- **Verificación**: `uv run ruff check .` OK, `ruff format --check .` OK, `mypy plataforma/webcam` OK, `pytest` OK, `harness/check_context.py` OK, `tests/test_golden_path_puro.py` 5/5 en seam único.
