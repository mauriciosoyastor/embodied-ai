# Lessons para agentes

Lecciones cortas de fallos reales (CI, imports, seams, drift local↔GitHub) que no deben repetirse.

Cada archivo `NNNN-*.md` es una lección. `AGENTS.md` apunta a las que bloquean CI o ensucian el working tree.

| # | Archivo | Trigger |
|---|---|---|
| 0001 | `0001-ruff-f821-imports-en-tests.md` | `ruff` F821 / test usa símbolo sin import |
| 0002 | `0002-gha-expresiones-sin-pipe-int.md` | `Invalid workflow file` / `\| int` en `if:` |
| 0003 | `0003-sin-siblings-frontend-webcam.md` | carpeta hermana `*-prototype` vs path oficial |
| 0004 | `0004-gitignore-artefactos-agentes.md` | untracked `node_modules`/`dist`/`trajectory` |
| 0005 | `0005-mypy-overrides-temporales.md` | override mypy que sobrevivió al módulo real |
| 0006 | `0006-reuse-selectivo.md` | `pip install` repo <12/12 ingeniería trae `dlib`/`Postgres` y rompe `uv.lock` |
| 0008 | `0008-citas-existen-precommit.md` | doc cita `docs/adr/*`, `tests/*.py` o `harness/*.py` inexistente |

Al escribir una lección nueva: síntoma → causa → regla positiva → check antes de push → ejemplo incorrecto/correcto.
