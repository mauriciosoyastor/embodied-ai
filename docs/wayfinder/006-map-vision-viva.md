# Wayfinder Map — Visión Viva Real (Cámara → Whiteboard)

> Label: `wayfinder:map` · Estado: cerrado — way completo · Tracker: local-markdown · Creado: 2026-08-23 · Cerrado: 2026-08-23

## Destination

**Change en lugar** en `plataforma/webcam` donde `enrollment-panel.js:271 mockFaceFromPerson` + `face-embedding.js:56 stubEmbedding` se reemplazan por **detector facial real** (MediaPipe/ONNX) + **ArcFace `mobilefacenet.onnx` 128-d** vía `onnxruntime-web` WASM, con **re-identificación per-frame** (coseno <0.42) y **tracking persistente** (IoU/KCF) que renderiza badge `Hola <nombre>` en `overlay.js`, y expone `detecciones + identidades` enriquecidas al `WhiteboardState` (`plataforma/sim`) vía `WS /ws/percepcion` D5 sin romper `LeakyQueue N=1` / 10Hz / `Glass-to-Glass <200ms` / histéresis `N=5` / `ABORTED` latch. Cierra cuando `localStorage + identities.json` hidratado + matching en vivo corre **headless** (`uv run pytest plataforma/webcam -q` con frames sintéticos) y en `http://localhost:5173 ↔ :8000` demo persona conocida muestra `Hola <nombre>` y desconocida `desconocido`, con `ruff`/`mypy` verde.

## Notes

- Dominio: Embodied AI platform · `plataforma/webcam` (`enrollment-panel.js:1`, `face-embedding.js:1`, `ws.py:1`, `ws-client.js:1`, `overlay.js`, `app.py:57`) + `plataforma/sim` (`WhiteboardState`, `Bridge/Adapter`) + `fase-1` no tocado
- Skills a consultar por sesión: `grilling`, `domain-modeling`, `research`, `prototype`, `tdd`
- Preferencias fijas: change en lugar = **sí ejecuta** (este mapa sí aterriza código + tests, no solo decide); `ABORTED` latch y histéresis `N=5` idénticos a `handle_gesto`; `localStorage:webcam.identities` + `identities.json` hibrido permanece (mapa 004); privacidad: embedding 128-d nunca imagen cruda; `monorepo desacoplado` + `uv workspace` + `conftest.py`/`pythonpath=["."]` + `ruff`/`mypy strict` (`explicit_package_bases=true`, `ignore_missing_imports` para `onnxruntime.*`/`mediapipe.*`/`cv2.*` si hace falta) + `pytest` headless sin cámara; `LeakyQueue N=1` / `MAX_FPS=10` / `WS_BUFFERED_LIMIT=64KB` / `Glass-to-Glass <200ms` como budgets no negociables; `COSINE_THRESHOLD=0.42` + `COSINE_GRAY=[0.42,0.55]` como base
- Estado actual verificado: YOLO11n `yolo11n.onnx` + `hand_landmarker.task` `is_stub=False`, `WS /ws/percepcion` D5 operativo `:8000`, enrollment hibrido `enroll_sync`/`purge` bypass `N=1` (mapa 004), pero face es **proxy** `mockFaceFromPerson` + embedding **stub** determinístico `xorshift32` sin matching per-frame

## Decisions so far

<!-- índice — una línea por ticket cerrado: gist + link; el detalle vive en el ticket -->

- [Research: Detector facial real — Ticket 031](tickets/031-research-detector-facial-real.md) — MediaPipe `BlazeFace short-range` 0.2–0.34 MB, 12–22 ms browser, `createFromModelPath` directo sin `*.task`, coexiste con `hand_landmarker.task` mismo `FilesetResolver`, UltraFace 1.21 MB duplica wasm, `face-api.js` descartado — veredicto BlazeFace (2026-08-23)
- [Research: ArcFace mobilefacenet real — Ticket 032](tickets/032-research-embedding-real.md) — `mobilefacenet.onnx` 112×112 128-d `onnxruntime-web@1.29 wasm` `executionProviders:["wasm"]`, 4.2 MB, 30–42 ms, `face-embedding.js:70` ya es aterrizaje, `wasmPaths="/wasm/"` + fallback `xorshift32` L2, sin colisión `mediapipe==1.0.1`/`onnxruntime==1.29`/`numpy 1.26` (2026-08-23)
- [Grilling: Pipeline re-id + tracking — Ticket 033](tickets/033-grilling-pipeline-reid-tracking.md) — híbrido cada 3 frames + `IoU<0.7`, zona gris `0.42–0.55` (solo `<0.42` a Whiteboard), tracker `IoU greedy >0.5` edad 5, histéresis `N=3` grace 2, `10 FPS` `LeakyQueue`, `ABORTED` overlay-only, enroll 1 / re-id 3 — `CONTEXT.md:96` + `ADR 0005` (2026-08-23)
- [Grilling: Contrato percepción → Whiteboard — Ticket 034](tickets/034-grilling-contrato-whiteboard.md) — extiende `detecciones` con `identities?: IdentidadVista[]` (no `type:reid`), `WhiteboardState.last_identidades` lista 0–3 client-side sin `LeakyQueue`, reusa `GET /identities` hidratación, `DecisionAgentica` contexto personalización — `CONTEXT.md:102` + `ADR 0006` (2026-08-23)
- [Prototype: Overlay ReID — Ticket 035](tickets/035-prototype-overlay-reid.md) — `prototype-vision-viva.html` throwaway 2 variantes `?variant=a|b` (A badge-box + traj IoU vs B chip-list), veredicto **A** para prod (badge ligado a box, verde/amarillo/gris por `estado`) + B fallback >2 caras — rama `prototype/035-vision-viva` (2026-08-23)
- [Task: Migrar stub→real — Ticket 036](tickets/036-task-migracion-vision-viva.md) — `face-detector.js` BlazeFace + fix `face-embedding.js` wasmPaths/ort.Tensor + `IdentidadVista`/`last_identidades` en `whiteboard.py` + re-id híbrida N=3/IoU en `enrollment-panel.js` + badges Variante A en `overlay.js` + `descargar_modelos.py` frontend models; `ruff`/`mypy` 17 files/`pytest` **73 passed** headless verde (2026-08-23) — **mapa sin frontera**

## Not yet specified

<!-- fog hacia el destino — no ticketizable aún con nitidez; gradúa cuando la frontera avance -->

- **Fuente real `mobilefacenet.onnx` 128-d (deuda Opción C, post-cierre)** — no existe fuente pública verificada (onnx/models 404, HF gated/pytorch-only; insightface `w600k_mbf.onnx` es 512-d y migraría contrato `embedding[128]` del mapa 004). Hoy stub `xorshift32` cubre tests/CI; BlazeFace real ya operativo. Gradúa a nueva sesión enfocada en re-id browser
- Depth/proxémica (MiDaS / depth-anything) para distancia a persona — fog hasta cerrar re-id + tracking
- CLAHE / mejora low-light y MOG2 background subtraction para robustez nocturna — fog post-tracking
- Multi-cámara o ReID across sesiones (persistencia `identities.json` LRU, límite tamaño) — fog post-contrato Whiteboard
- Streaming `DecisionAgentica` con `Grammar-Constrained Decoding` consumiendo `identities` — fog post-Whiteboard
- Safety Envelope físico (`Deadman's Switch`/`Heartbeat`/`Geofencing`) alimentado por `identities` (ej. no avanzar si `desconocido` >N) — fog post-integración

## Out of scope

- Auth cloud / OAuth / DB centralizada — solo `localStorage` + `identities.json` local (heredado mapas 000/004)
- Video grabación persistente y dataset biometría — solo snapshot 112×112 para embedding, no stream storage
- Entrenar modelo facial propio — solo `mobilefacenet`/`ArcFace` 128-d existente
- ROS2 / Gazebo / PX4 Offboard como consumer de `identities` — pertenece a mapas `sim` (001/002), solo `WhiteboardState` aquí

## Tickets (frontera)

> Cada ticket es un child de este mapa. Bloqueos: `Bloquea:` = este ticket bloquea a otros. Frontera = abiertos sin bloqueos.

### Ticket 031 — Research: Detector facial real en browser (MediaPipe vs ONNX) [wayfinder:research] — CERRADO 2026-08-23

**Question:** ¿Qué detector facial browser corre junto a `hand_landmarker.task` sin colisión TF Lite/WASM y con budget <50ms @640×480? Evaluar MediaPipe Face Detection / BlazeFace Tasks vs UltraFace ONNX vs `face-api.js` TinyFaceDetector: bundle size, licencia, `onnxruntime-web` wasm provider, compat `is_stub` fallback, y bbox normalizada `[0,1]` lista para `face-embedding.js:98 embed`.

**Bloquea:** 033

**Estado:** cerrado — ver [031](tickets/031-research-detector-facial-real.md) — BlazeFace short-range recomendado 0.2 MB 12–22 ms

### Ticket 032 — Research: ArcFace mobilefacenet 128-d real en browser [wayfinder:research] — CERRADO 2026-08-23

**Question:** ¿Cómo aterrizar `mobilefacenet.onnx` 112×112 en `face-embedding.js:70 createFaceEmbedder` con `onnxruntime-web` wasm (`session.run` 1×3×112×112, normalize `(-0.5)/0.5 → L2`) sin romper `uv` `onnxruntime==1.29` server? Medir modelo size, latencia CPU wasm, pin `numpy 1.26`, y fallback `stubEmbedding` idempotente. Verificar `enrollment-panel.js:334 cropSource` pipeline.

**Bloquea:** 033

**Estado:** cerrado — ver [032](tickets/032-research-embedding-real.md) — `mobilefacenet.onnx` 4.2 MB wasm `executionProviders:["wasm"]` validado, `face-embedding.js:70` ya listo

### Ticket 033 — Grilling: Pipeline re-id per-frame + tracking persistente [wayfinder:grilling] — CERRADO 2026-08-23

**Question:** ¿Cuándo calcular embedding y matchear? Opciones: cada frame vs cada N vs solo cuando YOLO `person` cambia. Threshold `0.42` + zona gris `0.42-0.55`, single vs multi-person (¿bloquear enroll si `persons>=2` y re-id si múltiples?), persistencia IDs vía IoU `w*h` overlap vs KCF vs ByteTrack simple, presupuesto `Glass-to-Glass <200ms` repartido (YOLO ~40ms + face ~30ms + embed ~30ms). HITL con `grilling` + `domain-modeling`.

**Bloquea:** 034, 035, 036

**Estado:** cerrado — ver [033](tickets/033-grilling-pipeline-reid-tracking.md) — híbrido 3+IoU, gris 0.42–0.55, IoU greedy edad 5, N=3 grace2

### Ticket 034 — Grilling: Contrato percepción → WhiteboardState [wayfinder:grilling] — CERRADO 2026-08-23

**Question:** ¿Qué payload nuevo consume `WhiteboardState` sin `transcript`? ¿Extender `detecciones {boxes}` con `identities:[{id,nombre,conf,box,cosine}]` vs nuevo `type:reid` D5? Single-writer memoria, `Reducer` fog, y cómo `DecisionAgentica` (`plataforma/sim` `DecisionNode` + `Muse Spark`) lo consume sin romper `ABORTED` latch. ¿Matching client-side (privacidad) vs server-side? HITL `grilling` + `domain-modeling`.

**Bloquea:** 036

**Estado:** cerrado — ver [034](tickets/034-grilling-contrato-whiteboard.md) — extiende detecciones con `last_identidades` client-side sin LeakyQueue

### Ticket 035 — Prototype: Overlay con badge re-id + trayectorias [wayfinder:prototype] — CERRADO 2026-08-23

**Question:** Throwaway `prototype-vision-viva.html` (no plegar): ¿cómo se ve badge `Hola <nombre>` / `desconocido` sobre `box person`, traza tracking, feedback enroll vs re-id, y estado `pending_sync`? Comparar variantes (badge dentro box vs barra superior, color por `conf`). HITL `prototype`.

**Bloquea:** 036

**Estado:** cerrado — ver [035](tickets/035-prototype-overlay-reid.md) — veredicto **A badge-box** para prod

### Ticket 036 — Task: Migrar stub→real + tests headless [wayfinder:task] — CERRADO 2026-08-23

**Question:** Trabajo que aterriza el change: reemplazar `mockFaceFromPerson` + `stubEmbedding` por detector/embedding reales, implementar matching per-frame + tracking en `enrollment-panel.js`/`overlay.js`/`ws.py` (si aplica), exponer `identities` a `WhiteboardState`, y dejar `uv run ruff format . && uv run ruff check --fix . && uv run mypy plataforma/webcam && uv run pytest plataforma/webcam -q` verde headless (frames/landmarks sintéticos, `onnx` stub en CI). HITL/AFK.

**Bloquea:** —

**Estado:** cerrado — ver [036](tickets/036-task-migracion-vision-viva.md) — change aterrizado, 73 passed, mapa completo
