# Wayfinder Map — Arquitectura Productiva Replicable (Leaky + ReID + Bridge + WebRTC)

> Label: `wayfinder:map` · Estado: cerrado — way completo · Tracker: local-markdown · Creado: 2026-08-24 · Cerrado: 2026-08-24

## Destination

**Change en lugar** en `plataforma/webcam` + `plataforma/sim` que aterriza **arquitectura productiva replicable** integrando `ALVAROI12/real-time-inference-pipeline` (LeakyQueue N=1 + latest_frame Lock para `glass-to-glass <200ms`), `basabraj/Mobilefacenet` (ReID híbrido YOLO-face + IoU + MobileFaceNet 128-d + threshold per-person + LanceDB), `gazebosim/ros_gz` (Bridge `SimAdapter` → `GzAdapter` con `ros_gz_bridge`), y `pydantic/pydantic-ai` `pydantic-graph` (StateGraph `SIM_IDLE/RUNNING/PAUSED/ABORTED` con `BaseNode[StateT,DepsT,RunEndT]`), y **baja latencia real en Jetson** con `dusty-nv/jetson-inference` WebRTC + NVDEC `nvh264dec` (migración `RTSP+WebSocket → WebRTC` Fase 2). Cierra cuando `plataforma/webcam` corre 10Hz sin `buffer bloat` con ReID vivo y `plataforma/sim` corre `MujocoAdapter` o `GzAdapter` tras mismo `Protocol`, todo `ruff/mypy/pytest` headless verde en `http://localhost:5173 ↔ :8000`.

## Notes

- Dominio: Embodied AI platform · `plataforma/webcam` (`ws.py:1`, `ws-client.js:1`, `overlay.js`, `app.py:57`, `frontend/src/enrollment-panel.js`, `face-embedding.js`) + `plataforma/sim` (`adapter.py:8`, `graph.py`, `whiteboard.py`, `mujoco_adapter.py`) + `fase-1` no tocado
- Skills a consultar por sesión: `grilling`, `domain-modeling`, `research`, `prototype`, `tdd`
- Preferencias fijas: change en lugar = **sí ejecuta** (este mapa aterriza decisiones + código replicable, no solo decide); `LeakyQueue N=1` / `MAX_FPS=10` / `WS_BUFFERED_LIMIT=64KB` / `Glass-to-Glass <200ms` budgets no negociables; `ABORTED` latch + histéresis `N=5` idénticos a `handle_gesto`; `WhiteboardState` single-writer memoria sin `transcript`; `monorepo desacoplado` + `uv workspace` + `conftest.py`/`pythonpath=["."]` + `ruff`/`mypy strict` (`explicit_package_bases=true`, `ignore_missing_imports` para `onnxruntime.*`/`mediapipe.*`/`cv2.*` si hace falta) + `pytest` headless sin cámara; `COSINE_THRESHOLD=0.42` + `COSINE_GRAY=[0.42,0.55]` + `REID_N=3` grace2 + `IoU>0.5` edad5 como base heredada mapa 006
- Estado actual verificado: mapa 006 cerrado 2026-08-23 con BlazeFace short-range real + stub `mobilefacenet` `xorshift32`, `WS /ws/percepcion` D5 operativo, `SimAdapter` `FakeAdapter`/`MujocoAdapter` operativo, `pydantic-graph` StateGraph `SIM_*` operativo; falta replicar Leaky productivo, ReID calibrado, Bridge Gz y WebRTC NVDEC
- Referencias externas validadas 2026-08-24: `ALVAROI12/real-time-inference-pipeline` (YOLOv8+WebSocket sub-100ms), `basabraj/Mobilefacenet` (YOLOv8n-face+IoU+LanceDB), `gazebosim/ros_gz` (ros_gz_bridge), `dusty-nv/jetson-inference` 8.7k★ (webrtc-server.md + NVDEC), `pydantic/pydantic-ai` 15.8k★ (`pydantic-graph`)

## Decisions so far

<!-- índice — una línea por ticket cerrado: gist + link; el detalle vive en el ticket -->

- [Research: ALVAROI12 LeakyQueue productivo vs nuestro N=1 — Ticket 037](tickets/037-research-alvaro-leaky.md) — mantener `AsyncLeakyQueue N=1` dual fast/slow + `canSend 64KB/10Hz`; ALVAROI12 sin Leaky real (FIFO blocking) — adoptar solo telemetría `warmup/fps` (2026-08-24)
- [Research: basabraj ReID per-person threshold + LanceDB — Ticket 038](tickets/038-research-basabraj-reid.md) — `embedding[128]` intacto, fijo `0.42` + gris `0.42-0.55` mantiene; per-person `0.60-0.65` solo con multi-foto, no LanceDB ahora; sí centroid+skip+margin Fase 1 (2026-08-24)
- [Research: gazebosim/ros_gz bridge mapping — Ticket 039](tickets/039-research-rosgz-bridge.md) — `CmdVel→Twist@gz.msgs.Twist ROS_TO_GZ`, `Odometry@gz.msgs.Odometry GZ_TO_ROS`, YAML + `GzAdapter` mock headless listo para 044 (2026-08-24)
- [Research: dusty-nv WebRTC + NVDEC Jetson — Ticket 040](tickets/040-research-dustynv-webrtc.md) — `webrtc://@:8554` `videoSource/videoOutput` + `nvh264dec` sin `PCIe copy`, `H.264` `WebRTC` `full-duplex` `<80ms LAN`, fallback `WS D5` desktop preserva `<200ms` (2026-08-24)
- [Grilling: ¿Leaky evoluciona o reemplaza perception_ws_handler? — Ticket 041](tickets/041-grilling-leaky-handler.md) — **evolucionar** dual `AsyncLeakyQueue N=1` fast/slow + `WS D5` baseline + fallback `webrtc` Jetson `C`, `intra 2/1 SEQUENTIAL` + `to_thread`, `warmup(10)` + `Zero-Copy` + `metrics` (2026-08-24)
- [Grilling: Contrato Whiteboard con ReID calibrada + Bridge — Ticket 042](tickets/042-grilling-whiteboard-bridge.md) — extender `detecciones.identities?: IdentidadVista[0..3]` `Bypass Galería` canal síncrono, `Single-Writer proyección` no `CmdVel`, `GzAdapter` agnóstico `SimAdapter` (2026-08-24)
- [Prototype: Overlay ReID + Leaky vivo — Ticket 043](tickets/043-prototype-overlay-leaky.md) — throwaway `prototype-leaky-reid.html` `?variant=a|b` veredicto **A badge-box** para prod (verde/amarillo/gris + traj 12, 10FPS Leaky 64KB, WS↔WebRTC fallback) + B fallback ≥4 caras (2026-08-24)
- [Task: Spike GzAdapter minimal headless — Ticket 044](tickets/044-task-gzadapter-spike.md) — `gazebo_adapter.py` `GzAdapter(SimAdapter)` mock `_FakeGzTransport` `CmdVel→Twist@gz.msgs.Twist`, `14 passed` headless `ruff/mypy` verde (2026-08-24) — **mapa sin frontera**
- [Grilling: ¿Leaky evoluciona o reemplaza perception_ws_handler? — Ticket 041](tickets/041-grilling-leaky-handler.md) — **evolucionar** dual `AsyncLeakyQueue N=1` fast/slow + `WS D5` baseline + fallback `webrtc` Jetson `C`, `intra 2/1 SEQUENTIAL` + `to_thread`, `warmup(10)` + `Zero-Copy` + `metrics` (2026-08-24)

## Not yet specified

<!-- fog hacia el destino — no ticketizable aún con nitidez; gradúa cuando la frontera avance -->

- **Migración completa `graph.py` a `pydantic-graph` iter vs `Graph.run`** — ¿`TickNode/DecisionNode/ActNode` pasan a `GraphBuilder` con `graph.iter()` para debug step-by-step? Fog hasta grilling Whiteboard (042).
- **CLAHE / MOG2 background subtraction nocturno** (`justthzz` + Guía Maestra Fase2 `history=500 variance=20`) — fog post-ReID calibrado (038) — graduó a Fase 1 gates en 038, pero no ticket aún.
- **Safety Envelope físico (`Deadman's Switch`/`Heartbeat`/`Geofencing`) consumiendo `last_identidades`** — fog post-contrato Whiteboard (042).
- **Multi-cámara / ReID across sesiones** — fog post-prototype overlay (043).

## Out of scope

- Entrenar `mobilefacenet`/`ArcFace` propio desde cero — solo replicar 128-d existente (heredado mapa 006)
- Auth cloud / OAuth / DB centralizada — solo `localStorage` + `identities.json` / `LanceDB` local
- ROS2 navegación completa (Nav2, SLAM) — solo `Bridge` `cmd_vel`/`odometry` mínimo
- Video grabación persistente y dataset biometría — solo snapshot 112×112 para embedding

## Tickets (frontera)

> Cada ticket es un child de este mapa. Bloqueos: `Bloquea:` = este ticket bloquea a otros. Frontera = abiertos sin bloqueos.

### Ticket 037 — Research: ALVAROI12 LeakyQueue productivo vs nuestro N=1 [wayfinder:research] — CERRADO 2026-08-24

**Question:** ¿Cómo implementa `ALVAROI12/real-time-inference-pipeline` su `LeakyQueue` + `latest_frame` con `Lock` y `bufferedAmount` para `sub-100ms`, y qué deltas tiene vs nuestro `ws.py:136 LeakyQueue` + `ws-client.js:88 canSend` + `AsyncLeakyQueue N=1` dual fast/slow `ws.py:584`? Medir budget `YOLO ~35ms + BlazeFace ~15ms + mobilefacenet ~32ms/3`.

**Bloquea:** 041

**Estado:** cerrado — ver [037](tickets/037-research-alvaro-leaky.md) — mantener `AsyncLeakyQueue N=1` dual + `canSend 64KB/10Hz`

### Ticket 038 — Research: basabraj ReID per-person threshold + LanceDB [wayfinder:research] — CERRADO 2026-08-24

**Question:** ¿Cómo calibra `basabraj/Mobilefacenet` `recog_threshold` per-person + `threshold_low/high` + `LanceDB` vs nuestro `cos 0.42` fijo + `histéresis N=3` + `IoU>0.5 edad5`, y qué `track_skip_frames`/`gallery_db` aporta para `WhiteboardState.last_identidades`?

**Bloquea:** 042

**Estado:** cerrado — ver [038](tickets/038-research-basabraj-reid.md) — `embedding[128]` intacto, no LanceDB, sí centroid+skip

### Ticket 039 — Research: gazebosim/ros_gz bridge mapping [wayfinder:research] — CERRADO 2026-08-24

**Question:** ¿Qué `message types` y sintaxis `/TOPIC@ROS_MSG@GZ_MSG` de `ros_gz_bridge parameter_bridge` mapean `CmdVel(v_x,omega_z)` y `SimObservation(x,y,yaw,v_x,v_y,omega_z)` de `adapter.py:8` para un `GzAdapter(SimAdapter)` headless sin ROS instalado, y qué `ros_gz_sim_demos` sirve como fixture?

**Bloquea:** 042, 044

**Estado:** cerrado — ver [039](tickets/039-research-rosgz-bridge.md) — `Twist@gz.msgs.Twist ROS_TO_GZ` + YAML mock listo

### Ticket 040 — Research: dusty-nv WebRTC + NVDEC Jetson [wayfinder:research] — CERRADO 2026-08-24

**Question:** ¿Cómo expone `dusty-nv/jetson-inference` `docs/webrtc-server.md` `videoSource/videoOutput webrtc://@:8554` con `GStreamer nvh264dec` sin `PCIe copy`, y qué fallback a `WebSocket` mantiene `ws-client.js:1` en desktop sin Jetson para no romper `Glass-to-Glass <200ms`?

**Bloquea:** 041

**Estado:** cerrado — ver [040](tickets/040-research-dustynv-webrtc.md) — `webrtc://@:8554` + `nvh264dec` fallback `WS` desktop

### Ticket 041 — Grilling: ¿Leaky evoluciona o reemplaza perception_ws_handler? [wayfinder:grilling] — CERRADO 2026-08-24

**Question:** Con datos 037+040: ¿evolucionar `ws.py:584 perception_ws_handler` dual-queue `fast 10Hz YOLO+gesto / slow 5Hz pose+depth` + `VLM 1Hz` o reemplazar por `background-thread latest_frame` con `Lock` estilo ALVAROI12? ¿Single `AsyncLeakyQueue` o `Lock+latest`? ¿WebRTC en `ws-client.js` o mantener `WS /ws/percepcion`? HITL `grilling` + `domain-modeling`.

**Bloquea:** 043

**Estado:** cerrado — ver [041](tickets/041-grilling-leaky-handler.md) — evolucionar dual + fallback `webrtc` + `2/1 SEQUENTIAL`

### Ticket 042 — Grilling: Contrato Whiteboard con ReID calibrada + Bridge [wayfinder:grilling] — CERRADO 2026-08-24

**Question:** Con datos 038+039: ¿`WhiteboardState` extiende `detecciones.identities?: IdentidadVista[]` con `cosine,conf,estado` calibrado per-person y `LanceDB` vs `identities.json`, y cómo `GzAdapter` consume `CmdVel` sin romper `ABORTED` latch y `REID_N=3`? HITL `grilling` + `domain-modeling`.

**Bloquea:** 043

**Estado:** cerrado — ver [042](tickets/042-grilling-whiteboard-bridge.md) — `detecciones.identities` + `Bypass Galería` + `Single-Writer` + `GzAdapter` agnóstico

### Ticket 043 — Prototype: Overlay ReID + Leaky vivo [wayfinder:prototype] — CERRADO 2026-08-24

**Question:** Throwaway `prototype-leaky-reid.html` (no plegar): ver badge `Hola <nombre>` / `posible?` / `desconocido` sobre box con trayectoria IoU, throttled `10 FPS` + `Leaky N=1` skip `bufferedAmount>64KB`, y switch `WebSocket ↔ WebRTC` mock. Comparar variante A badge-box vs B chip-list (heredado 035). HITL `prototype`.

**Bloquea:** —

**Estado:** cerrado — ver [043](tickets/043-prototype-overlay-leaky.md) — veredicto **A badge-box** + B fallback ≥4 caras

### Ticket 044 — Task: Spike GzAdapter minimal headless [wayfinder:task] — CERRADO 2026-08-24

**Question:** Trabajo que desbloquea decisión Bridge: spike `GzAdapter(SimAdapter)` minimal que traduce `CmdVel → gz topic` y `gz → SimObservation` con `FakeAdapter` fixture, sin requerir ROS/Gazebo instalado, verificado `ruff/mypy/pytest` headless (mock `gz` transport). HITL/AFK.

**Bloquea:** —

**Estado:** cerrado — ver [044](tickets/044-task-gzadapter-spike.md) — `gazebo_adapter.py` mock headless `14 passed` verde
