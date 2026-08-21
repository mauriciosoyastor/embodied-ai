# Plataforma Webcam

Módulo `plataforma/webcam` — backend FastAPI con inferencia YOLO11n (ONNX) + MediaPipe Hand Landmarker.
Parte de S2 (#46) · Contratos D7 (#45), D4 (#34). Este README cubre solo S2-E (estructura + CI + descarga).

## Estructura

```
plataforma/webcam/
  backend/
    pyproject.toml          # miembro uv workspace (comparte uv.lock raíz)
    descargar_modelos.py    # baja pesos oficiales a backend/models/
    models/                 # gitignored — pesos *.onnx / *.task
    app.py                  # (S2-A) FastAPI + lifespan
    ws.py                   # (S2-A) handler /ws/percepcion
    inference/              # (S2-B/C) yolo.py + gesture.py
  frontend/                 # (futuro) ws-client.js + overlay.js
  tests/                    # frames/landmarks sintéticos — headless
  .gitignore                # models/ + *.onnx
  README.md                 # este archivo
```

`plataforma/webcam/backend` es miembro del `uv` workspace raíz (`tool.uv.workspace.members` en `pyproject.toml` raíz). Comparte `uv.lock` y caché; declara dependencias propias (`onnxruntime==1.29.*`, `opencv-python==4.14.*`, `mediapipe==1.0.1`, `fastapi`, `uvicorn`, `numpy`, `pydantic>=2`).

## Requisitos

- Python 3.12
- `uv` (`pip install uv` o `pipx install uv`)
- No se commitean pesos (`models/` y `*.onnx` están en `.gitignore`).

## Setup local

```bash
# 1. Resolver workspace (desde la raíz del repo)
uv sync

# 2. Solo backend webcam (opcional, mismo lock)
uv sync --package webcam-backend

# 3. Descargar modelos oficiales (idempotente)
uv run python plataforma/webcam/backend/descargar_modelos.py
# re-descargar forzado:
uv run python plataforma/webcam/backend/descargar_modelos.py --force
# directorio custom:
uv run python plataforma/webcam/backend/descargar_modelos.py --models-dir ./models

# 4. Verificar pesos
ls -lh plataforma/webcam/backend/models/
# yolo11n.onnx (~10 MB) + hand_landmarker.task (~~12 MB)
```

Modelos:
- `yolo11n.onnx` — Ultralytics assets v8.3.0 (`https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n.onnx`)
- `hand_landmarker.task` — Google AI Edge (`https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task`)

El script es idempotente: si los archivos ya existen y `--force` no se pasa, se omite la descarga. Con hash esperado configurado en `EXPECTED_SHA256`, verifica SHA256 después de descargar.

## Tests headless (sin cámara)

```bash
# todos los checks del módulo (como en CI)
uv run ruff check plataforma/webcam
uv run ruff format --check plataforma/webcam
uv run mypy plataforma/webcam
uv run pytest plataforma/webcam -q

# sin uv (fallback pip)
pip install -e "plataforma/webcam/backend[dev]"  # si aplica
pytest plataforma/webcam -q
```

Los tests usan frames sintéticos (`numpy` zeros) y landmarks sintéticos — no requieren cámara/GPU/EGL, corren en CI Ubuntu headless y en Windows/WSL2.

## CI (path-filtered)

`.github/workflows/ci.yml` extiende `quality` raíz con:

- job `changes` → `dorny/paths-filter@v3` con filtro `webcam: plataforma/webcam/**`
- job `webcam-ci` → `needs: changes`, `if: needs.changes.outputs.webcam == 'true'`, `runs-on: ubuntu-latest` que corre `uv sync` + `ruff check` + `mypy` + `pytest` solo cuando cambia `plataforma/webcam/**`.

Local dry-run:

```bash
# simular filtro
git diff --name-only origin/main | grep '^plataforma/webcam/'
```

## Troubleshooting

- `uv sync` falla por lock: borrar `uv.lock` y re-generar con `uv sync` (no commitear duplicado; el lock es único en raíz).
- `mediapipe==1.0.1` requiere `opencv-python==4.14.*` y `numpy`; en Windows usar Python 3.12 64-bit.
- Descarga bloqueada por proxy: usar `--yolo-url` / `--hand-url` con mirror local.
