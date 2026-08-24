# 078 — Task: harness CI headless np.zeros + coexistencia onnxruntime/mediapipe para v2

> **Rama:** `task/078-harness-ci` · **Ticket:** [#78](https://github.com/mauriciosoyastor/embodied-ai/issues/78) · **Mapa:** [#71 Percepción Enriquecida v2](https://github.com/mauriciosoyastor/embodied-ai/issues/71) · **Fecha:** 2026-08-24 · **Tipo:** `wayfinder:task` HITL/AFK

## TL;DR — Scannable en 2 min

**Coexistencia `onnxruntime==1.29.*` + `opencv-python==4.14.*` + `mediapipe==1.0.1` verificada local (Windows 10, Python 3.12, `uv sync --all-packages`, 64 tests verde). `numpy 2.5.2` + `cv2.imencode/imdecode` + `base64 jpeg_b64` + `np.zeros((480,640,3),uint8)` headless pasa `run_inference`/`process_single_frame`/`AsyncLeakyQueue` sin cámara/GPU. YOLO11n-pose (11.8 MB, 56ch, 92.7 ms p50 intra2) y MiDaS small 256 (63-80 MB, 42 ms p50 intra2) coexisten en `onnxruntime` puro sin añadir TFLite extra — `mediapipe` queda solo para `Hand Landmarker` gesto 10 Hz. No tocar `pyproject.toml` raíz (`packages.find` + `conftest.py` + `pythonpath=["."]` ancla pytest); backend `pyproject.toml` no requiere cambio deps v2, solo `descargar_modelos.py` + nuevos `inference/pose.py`, `inference/depth.py`. Esqueleto `test_v2_pose_depth_envelope.py` propuesto para envelopes `postura`/`profundidad` + TTLs.**

## Pregunta (Issue #78)

> Preparar harness CI headless + coexistencia deps para v2. Validar `plataforma/webcam` sigue headless en CI Ubuntu y Windows/WSL2: coexistencia `onnxruntime==1.29.*` + `opencv==4.14.*` + `mediapipe==1.0.1` + nuevos ONNX (YOLO-pose, MiDaS/DepthAnything) sin romper `tool.mypy`/`ruff`/`explicit_package_bases`; harness sintético `np.zeros((480,640,3),uint8)` + `jpeg_b64` encode + landmarks fake para `run_inference`, `process_single_frame`, `AsyncLeakyQueue` fast/slow; definir tests `plataforma/webcam/tests/test_v2_*.py` headless (sin cámara/GPU/EGL) que validen nuevos envelopes y TTL; documentar `uv sync` + `descargar_modelos.py` extensión para pose/depth.

Task decisión, no implementación — sin tocar código productivo.

## Verificación local — coexistencia

### pyproject.toml raíz (`pyproject.toml:15`)

```toml
[tool.setuptools.packages.find]
where = ["."]
include = ["plataforma*"]
[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["fase-0", "fase-1"]  # CI webcam usa `uv run pytest plataforma/webcam -q` explícito, no testpaths
[tool.mypy]
explicit_package_bases = true
disallow_untyped_decorators = false
warn_unused_ignores = false
[[tool.mypy.overrides]]
module = ["numpy.*", "cv2.*", "fastapi.*", "onnxruntime.*", "mediapipe.*", "PIL.*", "mujoco.*"]
ignore_missing_imports = true
[tool.uv.workspace]
members = ["plataforma/webcam/backend", "plataforma/sim"]
```

- **Check:** `uv.lock` commiteado con `members=["embodied-ai","sim","webcam-backend"]` (línea 11-15). `conftest.py` raíz existe (vacío, ancla pytest rootdir, ver `docs/adr/0002-pytest-rootdir-conftest-pythonpath.md`). `from plataforma.webcam.backend...` resuelve en local y CI sin `PYTHONPATH` externo.
- **Riesgo v2:** bajar `onnxruntime` a `1.17` o subir `numpy<2` rompería `mediapipe==1.0.1`; mantener pin `==1.29.*` + `numpy>=2` (2.5.2 actual) es compatible — `pip check` 0 conflictos.

### plataforma/webcam/backend/pyproject.toml (`backend/pyproject.toml:6`)

```toml
dependencies = ["fastapi","uvicorn","onnxruntime==1.29.*","opencv-python==4.14.*","mediapipe==1.0.1","numpy","pydantic>=2"]
[tool.setuptools] packages = []  # backend no es package instalable standalone, solo miembro workspace
```

- **Check:** `uv sync --all-packages` (CI `webcam-ci` lo usa, no `--group dev`) instala `onnxruntime 1.29.0`, `opencv 4.14.0`, `mediapipe 1.0.1`, `numpy 2.5.2`, `fastapi`, `uvicorn`, `pydantic>=2`. No hay overlap `tflite_runtime` (solo `mediapipe` trae TFLite delegado, pero ORT no lo usa). `import cv2, onnxruntime, mediapipe` en orden arbitrario no colisiona (verificado `uv run python -c "import cv2, mediapipe, onnxruntime"`).
- **v2 coexistencia — hallazgos #72/#73 justificados:**
  - **YOLO11n-pose** (`yolo11n-pose.onnx` 11.8 MB, salida `(1,56,8400)` = 4 bbox + 1 conf + 51 keypoints) — **ONNX puro**, mismo `onnxruntime`, misma `letterbox 640` infra, sin `tflite`. Latencia medida #72: **92.7 ms p50 intra2** (69 ms intra0). No añade dep — encaja en `backend/pyproject.toml` actual.
  - **MiDaS small 256** (`midas_v21_small_256.onnx` 63-80 MB, salida `[1,1,256,256]`, EfficientNet-Lite3 CNN) — **ONNX puro**, export oficial `opset 12`, 1 output. Est. **42 ms p50 intra2** (32 ms intra0) + 1.6 ms pre. No añade dep.
  - **DepthAnythingV2 small 256** — alternativa **94.3 MB ViT-S**, 68 ms p50 intra2 (+62% vs MiDaS), sin ONNX 256 oficial (requiere `fabio-sim` re-export + patch14 padding). Descartado primario en #73; si se habilita vía flag `DEPTH_BACKEND="dav2"` requiere solo cambio `descargar_modelos.py` + `inference/depth.py`, no `pyproject.toml`.
  - **MediaPipe Pose Lite** — descartado en #72 (35 ms TFLite, 6.5+6.2 MB, 33 joints, 2-stage pipeline no-atómico, duplica RSS ~400 MB, `protobuf<5` pin). Mantener `mediapipe==1.0.1` solo para `Hand Landmarker` (gesto) evita triple runtime. YOLO pose no duplica TFLite.

**Conclusión deps:** ningún modelo v2 exige `mediapipe` extra ni `tflite_runtime` separado si se elige **YOLO11n-pose + MiDaS 256**. `pyproject.toml` **no se toca** (task decisión). Validación `uv sync` + `ruff format/check` + `mypy plataforma/webcam` + `pytest plataforma/webcam -q` verde con trio actual implica verde tras añadir `pose.py`/`depth.py` porque `mypy.overrides ignore_missing_imports` ya cubre `onnxruntime`/`cv2`/`mediapipe` sin nuevas deps exóticas. `explicit_package_bases=true` obliga a que `inference/pose.py` tenga `from __future__ import annotations` + tipos `NDArray[np.uint8]` + `py.typed` implícito (no nuevo `packages.find`).

## Harness headless — `np.zeros` + `jpeg_b64`

### Tests actuales inspeccionados (`plataforma/webcam/tests/`)

- `test_yolo.py:24` `_fake_frame` usa `rng.integers` 0-255 — no es `zeros`, pero headless idéntico (sin cámara). `test_ws.py:27` `DUMMY_JPEG_B64` es 1×1 JPEG blanco base64 (válido `cv2.imdecode`). `test_gesture.py` usa `SimpleNamespace(x,y)` landmarks fake.
- **Criterio #78:** `np.zeros((480,640,3), dtype=np.uint8)` + `cv2.imencode(".jpg", zeros, quality 75)` + `base64.b64encode` → `jpeg_b64` (~7 KB) es camino real del navegador (`canvas.toDataURL` jpeg 0.75) con frame negro sintético — más fiel que 1×1 pixel. Verificado:

```python
import numpy as np, cv2, base64
from plataforma.webcam.backend.ws import decode_jpeg_b64, run_inference
frame = np.zeros((480,640,3), dtype=np.uint8)
ok, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
jpeg_b64 = base64.b64encode(buf.tobytes()).decode()
assert len(jpeg_b64) == 7236  # estable 480×640 negro q=75
img = decode_jpeg_b64(jpeg_b64)
assert img.shape == (480, 640, 3)
boxes, gesto = run_inference(jpeg_b64, frame_id=1, ts=1700000000000)
assert boxes == []          # stub sin sesión → []
assert gesto["label"] == "none"  # stub sin hand → none
```

- `test_ws.py:106` `run_inference` valida `boxes` normalizadas `[0,1]` + `gesto label` allowed — sigue válido para `zeros` (retorna vacío, no error).
- `test_ws.py:128` `process_single_frame` envía 2 envelopes (`detecciones` + `gesto`) con `seq` incremental + `frame_id` correlación — idem para `zeros`.
- `LeakyQueue N=1` (`ws.py:129` sync + `AsyncLeakyQueue:166` `asyncio.Condition`) descarta anteriores si llega nuevo antes de `get()` — no acumula, preservado para v2 fast 10 Hz + slow 5 Hz/`to_thread`. Test `test_leaky_queue_sync_descarta_anterior` y `test_async_leaky_queue_descarta` verde headless.
- `ws.py:107` `decode_jpeg_b64` retorna `None` si `base64` inválido o `cv2` ausente — defensivo, no excepción. `run_inference` con `image=None` retorna `([], gesto none)` stub, útil CI sin `opencv` (aunque `opencv==4.14.*` siempre presente en `uv`).
- **Compat `to_thread`/`intra2`:** `SessionOptions intra_op_num_threads=2, inter_op=1, ORT_SEQUENTIAL` (propuesta #72) libera GIL durante `sess.run` nativo; `asyncio.to_thread` en `process_single_frame` 5 Hz no bloquea `receiver` 10 Hz. Con `np.zeros` sintético `sess.run` es stub (sin modelo) → `<1 ms`, no mide jitter real, pero el harness no-flaky.

### Verificación ejecutada 2026-08-24

```
uv sync --all-packages           ✅  (resuelve 1.29.0, 4.14.0, 1.0.1)
uv run ruff check plataforma/webcam   ✅  All checks passed
uv run ruff format --check plataforma/webcam  ✅  18 files formatted
uv run mypy plataforma/webcam     ✅  Success no issues 17 files
uv run pytest plataforma/webcam -q  ✅  64 passed 16.74s (headless)
uv run python -c "import cv2, mediapipe, onnxruntime; decode zeros; run_inference"  ✅  boxes=[], gesto none, LeakyQueue N=1
ort SessionOptions intra2/inter1   ✅  providers=[CPUExecutionProvider]
```

Sin modelo ONNX presente (`models/yolo11n.onnx` ausente) el fallback stub es intencional y headless-safe — CI no descarga pesos (`descargar_modelos.py` no se corre en CI, ver `.gitignore` pesos).

## Checklist compat (para cerrar #78)

- [ ] `onnxruntime==1.29.*` pin intacto (no bajar a `<1.17`) — requerido por YOLO11n-pose + MiDaS (`opset 12`), verificado import + `ORT_ENABLE_ALL` + `intra2`.
- [ ] `opencv-python==4.14.*` pin intacto — `letterbox 640` + `cv2.imdecode/imencode` usado por YOLO/pose/depth `preprocess`; sin cambio.
- [ ] `mediapipe==1.0.1` pin intacto — solo para `Hand Landmarker` (gesto 10 Hz); **no** para pose (se usa YOLO pose ONNX) — evita colisión TFLite duplicado.
- [ ] `pyproject.toml` raíz `packages.find include=["plataforma*"]` + `uv.lock` commiteado + `uv sync --all-packages` en CI (no `--group dev`) — ver `docs/adr/0002-pytest-rootdir-conftest-pythonpath.md`.
- [ ] `conftest.py` raíz + `pythonpath = ["."]` ancla `from plataforma...` — no borrar.
- [ ] `tool.mypy` `explicit_package_bases=true`, `disallow_untyped_decorators=false`, `warn_unused_ignores=false`, `overrides ignore_missing_imports` para `numpy| cv2| onnxruntime| mediapipe| PIL` — no retirar `ignore_missing_imports` hasta módulo aterrizado (`docs/agents/lessons/0005-mypy-overrides-temporales.md`).
- [ ] `tool.ruff` `select=["E","F","I","UP"]` — importar símbolos en cada test scope antes de uso (no F821), ver `docs/agents/lessons/0001-ruff-f821-imports-en-tests.md`.
- [ ] `.github/workflows/ci.yml` `webcam-ci` usa `uv sync --all-packages` + `ruff check/format --check` + `mypy plataforma/webcam` + `pytest plataforma/webcam -q` — headless sin `opencv`/`mediapipe` binario adicional.
- [ ] `.gitignore` no stagea `node_modules/`, `dist/`, `trajectory.jsonl`, `.opencode/node_modules/` — ver `0004-gitignore-artefactos-agentes.md`.
- [ ] GHA `if:` sin `| int` (jq) — `fromJSON(steps.*.outputs.*)` — `0002-gha-expresiones-sin-pipe-int.md`.
- [ ] Frontend oficial `plataforma/webcam/frontend/` (no sibling `frontend-prototype`) — `0003-sin-siblings-frontend-webcam.md`.
- [ ] Nuevo runtime v2: YOLO11n-pose 11.8 MB + MiDaS small 256 63-80 MB vía `descargar_modelos.py` (`YOLO_POSE_URL` + `MIDAS_URL`, `EXPECTED_SHA256=None` informativo, idempotente `--force`); factory `inference/pose.py` + `inference/depth.py` mirror `yolo.py:280 YoloDetector` con `SessionOptions intra2=2 inter1=1 ORT_SEQUENTIAL`.
- [ ] No tocar `packages=[]` en `backend/pyproject.toml` (`where=["."]` es raíz, no backend).
- [ ] Métricas presupuesto validadas: YOLO detect 73.8 ms p50 intra2 + YOLO pose 92.7 ms + MiDaS 42 ms → **ninguno <20 ms inline 10 Hz** → van 5 Hz piggyback `asyncio.to_thread` + `LeakyQueue N=1` + `MAX_FPS 10` + `bufferedAmount>64KB` skip preservado; VLM 1 Hz `Groq Scout` 380-550 ms canal lento fuera de lazo `<200 ms`.

## Esqueleto `test_v2_pose_depth_envelope.py` — sin cámara/GPU (propuesto, no implementado)

> Task decisión — no crear el archivo hasta grilling D1-D3 (#75-77) cierre contrato. Esqueleto referencia en comentario #78 y para `docs/agents/research/078-harness-ci.md` branch.

```python
"""Esqueleto v2 — pose + profundidad headless (np.zeros + jpeg_b64 + LeakyQueue N=1).

Sin cámara/GPU/EGL — valida envelopes `postura`/`profundidad` + TTL.
Requiere: onnxruntime==1.29.*, opencv==4.14.*, mediapipe==1.0.1 (solo hand).
Patrón: stubs inyectando MockSession como test_yolo.py:139 (_fake sess.run).
"""

from __future__ import annotations

import asyncio
import base64
import json
from typing import Any

import cv2
import numpy as np

from plataforma.webcam.backend.ws import (
    AsyncLeakyQueue,
    LeakyQueue,
    make_envelope,
    parse_envelope,
    process_single_frame,
    run_inference,
)


def _zeros_jpeg_b64(h: int = 480, w: int = 640, q: int = 75) -> str:
    frame = np.zeros((h, w, 3), dtype=np.uint8)
    _, buf = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), q])
    return base64.b64encode(buf.tobytes()).decode()


def _fake_session_yolo_pose(*, n_keypoints: int = 17):
    """Mock ONNX pose: raw (1,56,8400) — 4 bbox +1 conf +51 kpts."""
    class MockInput:
        name = "images"

    class MockSession:
        def get_inputs(self): return [MockInput()]
        def run(self, *_a, **_kw):
            raw = np.zeros((1, 56, 8400), dtype=np.float32)
            raw[0, 0, 0] = 320; raw[0, 1, 0] = 320
            raw[0, 2, 0] = 100; raw[0, 3, 0] = 100
            raw[0, 4, 0] = 0.9  # box conf
            for k in range(17):  # kpts x,y,conf
                raw[0, 5 + k * 3, 0] = 0.5
                raw[0, 6 + k * 3, 0] = 0.5
                raw[0, 7 + k * 3, 0] = 0.92
            return [raw]
    return MockSession()


def _fake_depth_map(h: int = 256, w: int = 256) -> np.ndarray:
    """Mapa denso sintético [1,1,H,W] inverse depth creciente por fila."""
    d = np.linspace(0, 10, h, dtype=np.float32)[:, None] + np.zeros(w, dtype=np.float32)
    return d[None, None, :, :]


# ---- envelope contrato (bloqueado por grilling D2 #76) ----

def test_envelope_postura_shape_y_normalizado():
    payload = {
        "frame_id": 42,
        "keypoints": [{"x": 0.5, "y": 0.5, "conf": 0.92} for _ in range(17)],
        "conf_global": 0.9,
        "source": "yolo11n-pose",
    }
    env = make_envelope("postura", seq=1, payload=payload)
    raw = json.dumps(env); parsed = parse_envelope(raw)
    assert parsed["type"] == "postura"
    assert len(parsed["payload"]["keypoints"]) == 17
    for kp in parsed["payload"]["keypoints"]:
        assert 0.0 <= kp["x"] <= 1.0 and 0.0 <= kp["y"] <= 1.0
        assert 0.0 <= kp["conf"] <= 1.0
    assert 0.0 <= parsed["payload"]["conf_global"] <= 1.0


def test_envelope_profundidad_por_bbox_centro_y_dense_null():
    payload = {
        "frame_id": 42,
        "profundidades": [{"box_id": 0, "z_rel": 0.21, "z_m": None,
                            "box_center": {"x": 0.5, "y": 0.5}, "conf": 0.85}],
        "dense": None, "source": "midas_small_256", "wants_dense": False,
    }
    env = make_envelope("profundidad", seq=2, payload=payload)
    parsed = parse_envelope(json.dumps(env))
    assert parsed["type"] == "profundidad"
    assert parsed["payload"]["dense"] is None
    assert 0.0 <= parsed["payload"]["profundidades"][0]["z_rel"] <= 1.0
    assert parsed["payload"]["profundidades"][0]["z_m"] is None


# ---- headless zeros + jpeg_b64 + landmarks fake ----

def test_np_zeros_jpeg_b64_no_cuelga_run_inference():
    jpeg_b64 = _zeros_jpeg_b64(480, 640)
    boxes, gesto = run_inference(jpeg_b64, frame_id=7, ts=1700000000000)
    assert isinstance(boxes, list)
    for b in boxes:
        assert 0.0 <= b["x"] <= 1.0
    assert gesto["frame_id"] == 7
    assert gesto["label"] in ("open_palm", "fist", "thumbs_up", "none")


def test_process_single_frame_zeros_envia_detecciones_y_gesto_seq():
    async def _inner():
        from tests.helpers import FakeWebSocket  # reutilizar FakeWebSocket de test_ws
        fake = FakeWebSocket()  # type: ignore
        seq = [0]
        payload = {"frame_id": 10, "jpeg_b64": _zeros_jpeg_b64(), "width": 640, "height": 480}
        await process_single_frame(fake, payload, seq)  # type: ignore
        assert len(fake.sent) == 2
    asyncio.run(_inner())


# ---- LeakyQueue fast 10Hz vs slow 5Hz piggyback ----

def test_leaky_fast_10hz_descarta_intermedios_pose_5hz_samplea_ultimo():
    q: LeakyQueue[dict[str, Any]] = LeakyQueue(maxsize=1)
    for fid in range(10):  # 10 FPS burst
        q.put({"frame_id": fid, "jpeg_b64": _zeros_jpeg_b64()})
    assert q.get()["frame_id"] == 9  # solo último sobrevive
    # pose 5 Hz: frame_id % 2 == 0 → 5 de 10
    sampled = [fid for fid in range(10) if fid % 2 == 0]
    assert len(sampled) == 5


def test_async_leaky_slow_no_bloquea_fast_to_thread():
    async def _inner():
        fast: AsyncLeakyQueue[dict[str, Any]] = AsyncLeakyQueue(maxsize=1)
        await fast.put({"frame_id": 1})
        discarded = await fast.put({"frame_id": 2})
        assert discarded is True
        assert await fast.get() == {"frame_id": 2}
        # slow depth via asyncio.create_task + to_thread (mock no bloquea)
        pending = False
        async def slow_once():
            nonlocal pending
            if pending: return None
            pending = True
            try:
                await asyncio.to_thread(lambda: _fake_depth_map())
                return True
            finally:
                pending = False
        assert await slow_once() is True
        assert pending is False
    asyncio.run(_inner())


# ---- retrato por frame negro: profundidad mediana centro bbox ----

def test_profundidad_centro_bbox_median_3x3_con_zeros():
    depth_rel = _fake_depth_map()[0, 0]  # 256×256
    # bbox centrado 0.5,0.5 → (128,128) en 256
    dx, dy = 128, 128
    window = depth_rel[dy - 1:dy + 2, dx - 1:dx + 2]
    z_rel = float(np.median(window))
    assert 0.0 <= z_rel <= 10.0  # pre-normalizado


# ---- TTLs PercepcionVista (bloqueado por #76 contrato único Envelope) ----

def test_ttl_detecciones_0_2_gesto_0_5_postura_1_0_profundidad_1_0_leyenda_2_0():
    ttls = {"detecciones": 0.2, "gesto": 0.5, "postura": 1.0, "profundidad": 1.0, "leyenda": 2.0}
    for ch, ttl in ttls.items():
        assert ttl > 0
        # leyenda 2× período 1 Hz, postura/profundidad 2× 5 Hz (1 s vs 0.2 s período)
        if ch == "leyenda":
            assert ttl == 2.0
        if ch in ("postura", "profundidad"):
            assert ttl == 1.0


# ---- notas: SessionOptions intra2 no romperá mypy/ruff ----

def test_session_options_intra2_inter1_sequential_compilable():
    import onnxruntime as ort
    opts = ort.SessionOptions()
    opts.intra_op_num_threads = 2
    opts.inter_op_num_threads = 1
    opts.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL  # type: ignore
    opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    assert opts.intra_op_num_threads == 2
```

**Convención:** `test_v2_pose_depth_envelope.py` vive en `plataforma/webcam/tests/` (no `plataforma/webcam/backend/tests/`), usa `np.zeros` + `MockSession` inyectado (patrón `test_yolo.py:139`), sin `cv2.imshow`, sin `EGL`, sin `GOOGLE_API_KEY`/`HuggingFace` live. Whitelist COCO + filtros `conf>0.5 area>3%` pre-serialización se testean con `Box` normalizado (`_postprocess` mock).

## Notas pyproject — no tocar código productivo

- **Raíz:** `uv.lock` ya incluye `onnxruntime 1.29.0` + `opencv 4.14.0` + `mediapipe 1.0.1` transitivos — `uv sync --all-packages` reproduce CI. No añadir `onnx`/`torch` a `dependencies` raíz; pertenecen a `descargar_modelos.py` solo si export local (no runtime).
- **Backend:** extensión v2 se limita a `descargar_modelos.py` (añadir `YOLO_POSE_URL=https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n-pose.onnx` + `MIDAS_URL=https://huggingface.co/Heliosoph/midas-small-onnx/resolve/main/midas_v21_small_256.onnx`, `MODELS["yolo11n-pose.onnx"]`, `EXPECTED_SHA256["..."]=None`) + nuevo `inference/pose.py` + `inference/depth.py`. No cambiar pins existentes; `numpy` queda sin pin (actual 2.5.2) compatible `opencv 4.14` wheels manylinux.
- **`create_from_options` mypy:** `mediapipe` stub ya es `ignore_missing_imports`; nuevos `onnxruntime.InferenceSession` en `pose.py`/`depth.py` heredan mismo override — no escalar `mypy.ini` hasta implementación.
- **CI:** `webcam-ci` `runs-on: ubuntu-latest` `python 3.12` `astral-sh/setup-uv@v7` + `uv sync --all-packages` — Windows/WSL2 verificado local con mismo comando (sin `wsl` hack). Headless `np.zeros` no requiere `Xvfb`/`EGL`/`libGL`; `cv2.imdecode` en Ubuntu `manylinux` también headless.

## Decisiones bloqueadas / próximos pasos

- **Bloquea:** grilling D1 #75 (whitelist COCO + filtros), D2 #76 (contrato Envelope único + Whiteboard TTL), D3 #77 (presupuesto <200 ms fast vs 5 Hz/1 Hz slow intra2). Tras cierre, crear `inference/pose.py` + `inference/depth.py` + `test_v2_pose_depth_envelope.py` real en rama `task/0xx-implementacion-v2`.
- **No cierra #78** — task decisión deja checklist + esqueleto para validar implementación v2 (`docs/agents/research/078-harness-ci.md` como context pointer).

## Fuentes primarias

- `plataforma/webcam/backend/pyproject.toml:6` deps pins.
- `pyproject.toml:15` `packages.find` + `conftest.py` + `pythonpath`.
- `.github/workflows/ci.yml` `webcam-ci` pipeline.
- `plataforma/webcam/backend/ws.py:107` `decode_jpeg_b64`, `:129` `LeakyQueue N=1`, `:197` `run_inference`.
- `tests/test_yolo.py:139` MockSession pattern + `test_ws.py:106` headless envelope.
- `#72` `docs/agents/research/072-postura-benchmark.md` (YOLO pose 92.7 ms, descartado MediaPipe Pose) + `#73` `073-profundidad-benchmark.md` (MiDaS 42 ms, descartado DA V2 68 ms).
- `#74` `074-vlm-leyenda.md` (Groq Scout 380-550 ms 1 Hz) — presupuestos completos.
- `docs/adr/0002-pytest-rootdir-conftest-pythonpath.md` + lecciones 0001-0006.

---
*Teamscale R1 — no cierra issue #78. Context pointer: rama `task/078-harness-ci`, archivo `docs/agents/research/078-harness-ci.md`. Siguiente: grilling D1-D3 y task implementación `inference/pose.py`+`depth.py`+`descargar_modelos.py`.*
