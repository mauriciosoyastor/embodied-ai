# Ticket 036 — Task: Migrar stub→real + tests headless

> Parent: `006-map-vision-viva` · Label: `wayfinder:task` · Estado: cerrado 2026-08-23 · Tipo: HITL/AFK · Bloqueado por 033,034,035 (liberado)

## Question

Trabajo que **aterriza el change** (único ticket que _hace_ vs decide, per Wayfinder Notes):

Reemplazar `enrollment-panel.js:271 mockFaceFromPerson` + `face-embedding.js:56 stubEmbedding` por detector/embedding reales (031/032), implementar matching per-frame + tracking (033), exponer `identities` a `WhiteboardState` vía `WS /ws/percepcion` D5 (034), y plegar veredicto overlay (035) a `overlay.js`/`enrollment-panel.js` + `ws.py` si aplica `reid` server-side.

Debe quedar:

- `uv run ruff format . && uv run ruff check --fix . && uv run mypy plataforma/webcam && uv run pytest plataforma/webcam -q` verde **headless** (frames sintéticos `numpy.zeros`, landmarks sintéticos, `onnx` stub en CI sin `wasm`, `localStorage` mock en `jsdom`)
- `GET /identities` + `WS enroll_sync/purge/reid` verificado sin romper `LeakyQueue N=1` / `MAX_FPS=10` / `ABORTED` latch / histéresis `N=5`
- Demo `http://localhost:5173 ↔ :8000` con persona conocida badge `Hola <nombre>` (cosine <0.42) y desconocida `desconocido`

Registrar qué se hizo (rutas, `identities.json` schema cap 5 `hat_e`, `ws.py` bypass si aplica) para siguientes mapas (depth/CLAHE).

## Blocking

- Bloquea a —. Bloqueado por 033,034,035.

## Resolution

> Estado: **cerrado 2026-08-23** · Task HITL/AFK ejecutada · Change aterrizado · Verificación verde

**Qué se hizo (stub→real visión viva):**

- **`frontend/src/face-detector.js`** (nuevo) — BlazeFace short-range via `@mediapipe/tasks-vision` dynamic import + `FilesetResolver.forVisionTasks`, `FaceDetector.createFromOptions VIDEO minDetectionConfidence 0.7`, `detect()` mayor área + `detectAll()` hasta 3, bbox normalizada `[0,1]` clamp, probe `HEAD→GET Range 405`, fallback `isStub=true`.
- **`frontend/src/face-embedding.js`** (fix Ticket 032) — `ort.env.wasm.wasmPaths="/wasm/"`, fix `session.ort.Tensor` → `ortRef` capturado, fallback `HEAD 405 → GET Range bytes=0-0`, `session._ort = ort`. Stub `xorshift32` L2 preservado.
- **`plataforma/sim/whiteboard.py`** (034) — `IdentidadVista` Pydantic `{id,nombre,cosine,conf,estado confirmado|posible|desconocido,box,face_box,frame_id,ts}` + `WhiteboardState.last_identidades: list[IdentidadVista]|None` max 3, sin `transcript`.
- **`frontend/src/enrollment-panel.js`** (033) — re-id client-side híbrida: `REID_EVERY=3` frames @10Hz + trigger `IoU<0.7`; histéresis `REID_N=3 grace=2`; tracker `IoU greedy >0.5` edad `TRACK_AGE=5` traj 12; `getFaceBox` usa BlazeFace real con fallback `mockFaceFromPerson`; matching `cosineDistance` vs `loadGallery()` hidratada; zonas `<0.42` firme / `0.42–0.55` posible / `>0.55` desconocido; `ABORTED` overlay-only (no muta Whiteboard); API `getLastIdentidades/getTracker/setOnIdentidades/_runReId/_iou/_shouldEmbed` para tests.
- **`frontend/src/overlay.js`** (035 Variante A plegada) — badges `Hola <nombre> ✓` verde / `posible?` amarillo / `desconocido` gris sobre box por IoU-match, trayectoria polyline traj 12 pts, `handleIdentidades(identities)` + `detecciones.identities` opcional D5 backward-compatible, count `N obj · M id`.
- **`frontend/src/main.js`** — wiring `onIdentidades → overlay.handleIdentidades`.
- **`backend/descargar_modelos.py`** — `BLAZE_URL` + `MOBILEFACENET_URL`, descarga a `frontend/public/models/` idempotente (`--skip-frontend` opt-out), flags `--blaze-url/--face-url`.
- **`frontend/.gitignore`** — `public/models/*.onnx|*.tflite`, `public/wasm/` (nunca commitear pesos, lección 0004).

**Verificación (2026-08-23):**

```
uv run ruff format .            → 1 reformatted, 117 unchanged
uv run ruff check --fix .       → All checks passed
uv run mypy plataforma/webcam   → Success: no issues in 17 source files
uv run pytest plataforma/webcam plataforma/sim -q → 73 passed in 15.82s
```

Headless sin cámara: CI corre con `isStub=True` fallback (sin pesos), prod con pesos descargados corre real. Demo `http://localhost:5173 ↔ :8000`: iniciar cámara → persona enrolada badge `Hola <nombre> ✓` (cos<0.42 N=3), desconocida gris.

**Deuda técnica — fuente mobilefacenet.onnx (Opción C, 2026-08-23):**

No existe fuente pública verificada de `mobilefacenet.onnx` **128-d**: `onnx/models` 404 (solo ArcFace ResNet100 512-d/249MB), HuggingFace gated o pytorch-only (`py-feat/mobilefacenet` es `.pth.tar`). Decisión del usuario:

- **A rechazada** — `buffalo_l.zip` insightface (200 OK, 288MB, contiene `w600k_mbf.onnx`) es **512-d**: quiebra contrato `embedding[128]` del mapa 004 obligando a migrar schemas y distancias sin necesidad previa.
- **B rechazada** — export ONNX local con torch: gigabytes de dependencia para un artefacto, viola mínimos artefactos (lección 0006).
- **C elegida** — `MOBILEFACENET_URL=""` en `descargar_modelos.py`: descarga **skip con aviso `[DEUDA]`** sin fallar exit; stub `xorshift32` cubre tests/CI/demo; pytest/ruff/mypy verde. La fuente definitiva se decide en sesión enfocada exclusivamente en re-id browser.

BlazeFace sí quedó operativo: URL verificada 200 OK, descargado a `frontend/public/models/blaze_face_short_range.tflite` (229.746 bytes) — el detector facial real funciona hoy; solo el embedding sigue en stub hasta resolver la deuda.

**Mapa 006 way completo** — frontera vacía, destino alcanzado.
