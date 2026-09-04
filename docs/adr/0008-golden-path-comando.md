# 0008 — Comando Golden Path (`/golden-path`) sin auto-ejecución de skills

**Status**: accepted (2026-09-03, ejecuta A+C aprobado).

**Context**: `tests/test_golden_path_puro.py` es seam `CI+Harness` (configs + purga + `harness verify`), no orquestador: llamar a `golden path` vía `pytest` jamás invoca skills Matt (`triage/wayfinder/to-tickets/tdd/code-review`) porque las skills viven a nivel agente (tool `skill`), no como funciones Python. ADR-0007 definió la secuencia canónica pero sin comando ejecutable, y había solapes reales: `wayfinder` vs `gitnexus-plan` (ambos planean), `wayfinder:task` vs `to-tickets` vs `§7 gitnexus-plan` (triple slice), `code-review` vs `gitnexus-review` (doble review). PDG verificado funcionando (`pdg:true`, `meta.json pdg.hasCallSummary:true`, `pdg_query controls harness/harness.py total:204`) pero índice con `commitsBehind:10`, por lo que `work` debe refrescar antes del `impact`.

**Decision**: crear `.opencode/commands/golden-path.md` (`/golden-path`) con template que obliga el orden ADR-0007 y codifica reglas anti-solape + gates `HITL` de `AGENTS.md`:
`Triage(brief+verify) → [¿fog? wayfinder : skip] → to-tickets(una vez, aprobado) → por ticket: gitnexus-plan(compact default, full+strict+PDG solo en refactor/API/shared/security/perf) → gate humano bloqueante → gitnexus-work(tdd dentro + harness verify) → gitnexus-review + code-review en paralelo, un fix-cycle → merge humano`.
`gitnexus-lfg` completo y lanes sueltas nunca a la vez. `verification_commands` de `work` incluye `harness verify verdict:ok risk:low`. DoD: `CI fail rate <10%` + `uv sync --all-packages` local = `ci.yml` + `status:current` + `detect_changes` sin `HIGH` ignorado (`impact_ratio` observado).

**Considered Options**:
- **Auto-orquestador Python que llame skills**: descartado — las skills no son importables desde `pytest`/`harness`; el comando es prompt para el agente, no código.
- **Doble slice épico + por ticket**: descartado — `to-tickets` define la frontera una vez; `gitnexus-plan` detalla por ticket.
- **Un solo review**: descartado — ejes distintos y complementarios (`Standards/Spec` vs blast-radius/taint/PDG).

**Consequences**:
- `/golden-path` visible en TUI; invocar `pytest` sigue sin ejecutar skills (por diseño).
- `work` bloquea si el índice está stale hasta `node .gitnexus/run.cjs analyze --index-only --pdg`.
- Reversibilidad: borrar el `.md` revierte el comando; ADR y lesson quedan como registro.
- Downstream: ajustar glosario `CONTEXT.md` (término `Golden Path Fusión`) + lesson `0007`.
