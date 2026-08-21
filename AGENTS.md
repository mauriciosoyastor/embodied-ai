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
