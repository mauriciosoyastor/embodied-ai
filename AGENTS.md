# Instrucciones del proyecto

## Regla obligatoria: aprobación previa

- **Nunca** ejecutes un proceso ni continúes con la siguiente tarea sin la aprobación explícita del usuario.
- Antes de ejecutar, editar, instalar, commitear o iniciar cualquier acción que modifique el sistema o el repositorio, propone el plan y espera confirmación.
- Si un paso tiene varias opciones, presenta las opciones y deja que el usuario elija.
- Esta regla aplica incluso si el usuario pidió una tarea larga con varios pasos: cada paso se ejecuta solo tras aprobación.

## Regla de CI local↔GitHub (no se vuelve a equivocar)

- **Raíz instalable**: `pyproject.toml` debe exponer `plataforma` vía `[tool.setuptools.packages.find] where=["."] include=["plataforma*"]` + `uv.lock` commiteado. No usar `packages = []` si hay código bajo `plataforma/`. `uv sync --all-packages` (no `--group dev`) en CI.
- **Ancla pytest**: `conftest.py` en la raíz (ver `docs/adr/0002-pytest-rootdir-conftest-pythonpath.md`) + `[tool.pytest.ini_options] pythonpath = ["."]`. No borrar ninguno. Si `pytest` falla con `No module named 'plataforma'`, verificar en orden: `conftest.py`, `pythonpath`, `packages.find`, `uv sync --all-packages`.
- **Mypy**: `explicit_package_bases = true`, `disallow_untyped_decorators = false` (con `strict=true` es `disallow`, no `warn`), `warn_unused_ignores = false`, y `[[tool.mypy.overrides]] ignore_missing_imports` para `numpy.*`, `cv2.*`, `fastapi.*`, `onnxruntime.*`, `mediapipe.*`, `PIL.*`. Antes de push: `uv run ruff format . && uv run ruff check --fix . && uv run mypy plataforma/webcam && uv run pytest plataforma/webcam -q`.
- **Ruff F821 en tests**: si un test llama un símbolo de otro módulo (`run_inference`, `ws_mod`, etc.), importalo en ese scope antes de usarlo. Comentarios no alcanzan. Ver `docs/agents/lessons/0001-ruff-f821-imports-en-tests.md`. Si CI muere en `ruff check` con `F821 Undefined name`, leer esa lección.
- **Workflows GHA**: en `if:` no uses `\| int` (jq). Usá `fromJSON(steps.*.outputs.*)`. Ver `docs/agents/lessons/0002-gha-expresiones-sin-pipe-int.md`.
- **Sin siblings**: frontend oficial = `plataforma/webcam/frontend/` (no `plataforma/frontend-prototype/`). Ver `docs/agents/lessons/0003-sin-siblings-frontend-webcam.md`.
- **Artefactos**: no stagear `node_modules/`, `dist/`, `trajectory.jsonl`, `.opencode/node_modules/`. Ver `docs/agents/lessons/0004-gitignore-artefactos-agentes.md`.
- **Overrides temporales**: al aterrizar un módulo, retirar `ignore_missing_imports` / skips asociados. Ver `docs/agents/lessons/0005-mypy-overrides-temporales.md`.

Índice: `docs/agents/lessons/README.md`.

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **embodied-ai** (10172 symbols, 25076 relationships, 174 execution flows).

> Index stale? Run `node .gitnexus/run.cjs analyze --index-only` from the project root — it auto-selects an available runner. No `.gitnexus/run.cjs` yet? Bootstrap with `npx`, `bunx`, or `pnpm dlx` — e.g. `bunx gitnexus@latest analyze` (npm 11 npx crash; #1939).

## Always Do

- **MUST run impact analysis before editing.** Use `impact({target: "symbolName", direction: "upstream"})` (MCP) or `node .gitnexus/run.cjs impact "symbolName" --direction upstream --repo .` (CLI fallback); report callers, processes, and risk. Never substitute grep for graph analysis. For unified PDG impact, add `mode: "pdg"` with optional `line: <N>` — it returns statement-level `affectedStatements` over CDG + REACHING_DEF and inter-procedural symbols in `interproceduralByDepth`/`byDepth`; no-layer/degraded PDG results are UNKNOWN-risk notes (`--pdg` layer). CLI equivalent: `node .gitnexus/run.cjs impact "symbolName" --direction upstream --mode pdg --line <N> --repo .`.
- **MUST analyze graph changes before committing.** Use `detect_changes({scope: "all"})` (MCP) or `node .gitnexus/run.cjs detect-changes --scope all --repo .` (CLI fallback). `partial: true` or `truncated: true` is not a clean check — a zero means unseen, not unaffected; re-run it. For regression review: `detect_changes({scope: "compare", base_ref: "main"})` or `node .gitnexus/run.cjs detect-changes --scope compare --base-ref "main" --repo .`.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- **MUST treat `risk: UNKNOWN` as unresolved, not as low.** An empty caller set is not evidence the symbol is unused — it can also mean the callers are not resolvable by the index (plain-object property access, dynamic dispatch, cross-language calls). `impact` pairs `UNKNOWN` with a `riskNote` saying so. Confirm with a text search before treating the symbol as safe to change or delete; do not proceed on the strength of a zero.
- When exploring unfamiliar code, use `query({search_query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `context({name: "symbolName"})`.
- For security review, `explain({target: "fileOrSymbol"})` lists taint findings (source→sink flows; needs `analyze --pdg`).
- For control/data dependence, `pdg_query({mode: "controls", target: "fileOrSymbol"})` answers "under what condition does X run?" (CDG, incl. guard clauses) and `pdg_query({mode: "flows", target, variable})` traces "where does variable Y flow?" (REACHING_DEF). `--pdg` layer.

## Never Do

- NEVER edit a function, class, or method before MCP/CLI impact analysis.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis, and never read `UNKNOWN` as an all-clear — it means the walk could not answer, which is the one verdict that requires confirming by other means.
- NEVER rename symbols with find-and-replace — use `rename` which understands the call graph.
- NEVER commit before MCP/CLI graph change analysis.

## Resources

| Resource | Use for |
| --- | --- |
| `gitnexus://repo/embodied-ai/context` | Codebase overview, check index freshness |
| `gitnexus://repo/embodied-ai/clusters` | All functional areas |
| `gitnexus://repo/embodied-ai/processes` | All execution flows |
| `gitnexus://repo/embodied-ai/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
| --- | --- |
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
