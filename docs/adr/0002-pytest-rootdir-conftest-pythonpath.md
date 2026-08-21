# 0002 — Pytest resuelve `plataforma.*` vía rootdir + pythonpath (conftest + mypy)

**Status**: accepted (2026-08-21, fix CI local↔GitHub para `plataforma/webcam`).

**Contexto**
Tests en `plataforma/webcam/tests/` importan `from plataforma.webcam.backend...`.
Local funcionaba porque `uv sync --all-packages` instalaba el workspace; en GitHub
`webcam-ci` hacía `uv sync --group dev` o `pip install -e ".[dev]"` sin el miembro
`webcam-backend` → `ModuleNotFoundError: No module named 'plataforma'` y
`Cannot find implementation for "numpy"` en mypy. Además, sin ancla, pytest no
añadía la raíz a `sys.path` → `from plataforma...` fallaba incluso instalado.

**Decisión**
1. **Raíz como paquete instalable**: `pyproject.toml:14` ` [tool.setuptools.packages.find] where=["."] include=["plataforma*"]` + `uv.lock` commiteado. `pip install -e .` y `uv sync --all-packages` exponen `plataforma`.
2. **Ancla pytest definitiva**: `conftest.py` vacío en la raíz — pytest lo usa como `rootdir` e inyecta automáticamente la raíz a `sys.path` en cualquier entorno (local/CI), sin env vars.
3. **Redundancia declarativa**: `pyproject.toml:26` `[tool.pytest.ini_options] pythonpath = ["."]` — cubre runners donde `conftest` no se detecta por `testpaths`. Ambas capas (conftest + pythonpath) son intencionales.
4. **Mypy alineado**: `pyproject.toml` `explicit_package_bases = true` + `disallow_untyped_decorators = false` (con `strict=true` es `disallow`, no `warn`) + `[[tool.mypy.overrides]] ignore_missing_imports` para `numpy.*`, `cv2.*`, `fastapi.*`, `onnxruntime.*`, `mediapipe.*`, `PIL.*`. El override temporal de `plataforma.webcam.backend.ws` se retiró al aterrizar S2-B (ver `docs/agents/lessons/0005-mypy-overrides-temporales.md`).

**Alternativas descartadas**
- Solo `PYTHONPATH=.` en `ci.yml` — frágil en `bash -e`, no cubre local sin export.
- Solo `uv run python -m pytest` — funciona pero exige disciplina de comando; `pythonpath`/`conftest` lo hacen implícito.
- `uv sync --group dev` — instala solo `dev`, no el workspace.

**Consecuencias**
- Todo agente/modelo que añada código bajo `plataforma/` debe mantener `conftest.py` en raíz y `pythonpath = ["."]`. No borrar ni mover.
- CI `webcam-ci` usa `uv sync --all-packages` + `uv run pytest plataforma/webcam -q` sin `env: PYTHONPATH`.
- Si reaparece `ModuleNotFoundError: No module named 'plataforma'`, verificar en orden: `conftest.py` existe, `pythonpath`, `packages.find`, `uv sync --all-packages`.
