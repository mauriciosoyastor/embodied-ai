# Ticket 041 — Grilling: ¿Leaky evoluciona o reemplaza perception_ws_handler?

> Parent: `007-map-arquitectura-productiva` · Label: `wayfinder:grilling` · Estado: **cerrado 2026-08-24** · Tipo: HITL · Bloqueado por 037,040 (liberado)

## Question

Con datos Research 037 (ALVAROI12 Leaky) + 040 (dusty-nv WebRTC/NVDEC): ¿evolucionar `plataforma/webcam/backend/ws.py:584 perception_ws_handler` dual-queue `fast 10Hz YOLO+gesto / slow 5Hz pose+depth` + `VLM 1Hz` o reemplazar por `background-thread latest_frame` con `Lock` estilo ALVAROI12?

## Grilling Round — 2026-08-24 (HITL)

**Participantes:** human (decisor) + agent (griller) + `domain-modeling`

**Frontera preguntada:**

- Q1 — Evolución `ws.py:584` dual vs `Lock+_latest`
- Q2 — Transporte `ws-client.js:1` `WS D5` vs `WebRTC webrtc://@:8554` con fallback
- Q3 — Concurrencia ONNX `intra=2 inter=1 SEQUENTIAL` vs `4/4 ENABLE_ALL` + pool

**Respuestas humanas (verbatim 2026-08-24):**

> Q1 (Evolución WS Handler - Opción A): Mantener AsyncLeakyQueue dual es la decisión correcta. Separar la vía rápida (YOLO + Gesto @ 10Hz) de la lenta (Pose + Depth @ 5Hz, VLM @ 1Hz) evita el bloqueo Head-of-Line (HoL). Reemplazar por Lock + _latest rompería la ventana de histéresis (N=5/N=3) y el registro latcheado del estado ABORTED al eliminar frames intermedios sin métrica temporal.
> Q2 (Transporte Frontend - Opción C): Implementar fallback dinámico en ws-client.js. El envelope WebSocket D5 garantiza compatibilidad cross-platform (<200ms glass-to-glass) en entornos CI/x86/WSL2. La sonda (HEAD /webrtc/signal) permite habilitar WebRTC + NVDEC en hardware Jetson dinámicamente sin romper la suite de pruebas.
> Q3 (Concurrencia ONNX - Opción A): Fijar intra=2, inter=1 con ORT_SEQUENTIAL evita la saturación de la CPU en SoCs ARM/Jetson. Elevar a 4/4 despoja de hilos al tracker ByteTrack (<1ms) y a la lógica HSV. Envolver session.run en asyncio.to_thread libera el event loop sin la sobrecarga de un pool rígido de 4 hilos. Warmup de tensores: Ejecutar warmup(10) en el arranque del servidor para compilar los grafos de ejecución de ONNX/TensorRT y amortizar el cold-start delay.
> Zero-Copy Memory Views: Reutilizar buffers compartidos (memoryview) al desempaquetar tramas JPEG del WebSocket para evitar copias inter-proceso hacia las matrices NumPy.
> Telemetría Expuesta: Exportar métricas (inference_time_ms, total_time_ms, fps, dropped_frames_total) mediante Prometheus para detectar picos de latencia en la arista.

## Resolution

> Estado: **cerrado 2026-08-24** · HITL grilling + domain-modeling · Decisión unánime

### Decisión 041 — Leaky Handler evoluciona, no se reemplaza

**Q1 — Aprobado: Evolucionar `ws.py:584` dual `AsyncLeakyQueue N=1`**
- Mantener `fast_queue 10Hz YOLO+gesto ws.py:636` + `slow_queue 5Hz pose+depth ws.py:637` + `VLM 1Hz detached create_task ws.py:742` + `Zero-Copy img_view ws.py:669` + `bypass enroll_sync/purge ws.py:654` + `seq_counter + seq_lock ws.py:634` + `connected_clients ws.py:39`.
- **No reemplazar** por `Lock+_latest` (markaicode) — rompería `handle_gesto N=5`/`REID_N=3 grace2` y `ABORTED latch` (`CONTEXT.md:59-60,99`) al perder orden `frame_id/seq` correlativo y `consecutivos` conteo.
- `Lock+_latest` queda reservado solo para `AdapterPoller` interno `GzAdapter` sim mono-proceso si se necesita polling, no para WS multi-cliente.

**Q2 — Aprobado: Fallback dinámico `C` en `ws-client.js:1`**
- Baseline `WS D5` `envelope {type,seq,ts,payload} ws.py:82` + `canSend 64KB/10Hz ws-client.js:88` + `canSendSlow 1Hz ws-client.js:97` + `reconnect 500ms→10s ws-client.js:26` permanece para `x86/WSL2/CI`/`pytest` headless — garantiza `<200ms` cross-platform.
- Añadir `selectTransport()` probe `fetch HEAD https://<JETSON-IP>:8554/webrtc/signal 200→webrtc else ws` (grilling Q2 C). `webrtc` branch usa `jetson-webrtc-client.js` shim `GstWebRTC` con `videoSource webrtc://@:8554/input` + `videoOutput webrtc://@:8554/output` + `nvh264dec` NVDEC sin `PCIe copy` (040). `WS` branch mantiene `createPerceptionClient ws://:8000/ws/percepcion`.
- Backend mantiene dual: `:8000/ws` WS + `:8554/webrtc` Jetson paralelo; no migración `RTSP→WebRTC` todavía — solo viewer.

**Q3 — Aprobado: `intra=2 inter=1 ORT_SEQUENTIAL` + `to_thread`**
- Fijar `ONNX_INTRA_OP 2 INTER 1 ORT_SEQUENTIAL yolo.py:302` + `await asyncio.gather(to_thread(pose), to_thread(depth)) ws.py:825` + envolver `session.run` en `asyncio.to_thread` (libera loop sin pool rígido 4 hilos).
- **No adoptar** `4/4 ENABLE_ALL + ThreadPoolExecutor(4)` ALVAROI12 (contiende `ByteTrack <1ms`/`HSV`, `p50 45ms` vs `35ms` sin ganancia).

### Optimizaciones adicionales aprobadas (no bloqueantes para 041, aterrizan en 043/044)

1. **Warmup(10) tensores** en `lifespan app.py` — `np.random.randn(1,3,640,640)` dummy 10 iteraciones `InferenceEngine.warmup` style ALVAROI12 para compilar grafos ONNX/TensorRT y amortizar `p99 120ms` cold-start.
2. **Zero-Copy Memory Views** — `memoryview` al desempaquetar `jpeg_b64` `ws.py:118 decode_jpeg_b64` hacia `np.frombuffer` sin copy inter-proceso a `np.ndarray`.
3. **Telemetría Prometheus** — exponer `inference_time_ms, total_time_ms, fps, dropped_frames_total` en `GET /metrics` (`metrics.py` + `ws.py` `detecciones` payload) para `p99` alertas Glass-to-Glass.

### Domain-modeling

- `CONTEXT.md` sin cambios: `LeakyQueue N=1`, `Glass-to-Glass <200ms`, `ABORTED latch`, `handle_gesto N=5`, `REID_N=3 grace2` permanecen canónicos.
- `ABORTED` single-writer `WhiteboardState` sin `transcript` preservado.

### Impacto mapa

- Desbloquea `043 Prototype Overlay ReID + Leaky vivo` parcialmente (espera también 042).
- No requiere ADR (no cambia contrato `ws.py` wire — evolución interna).

## Blocking

- Bloquea a 043. Bloqueado por 037,040 — **liberado** al cerrar (043 ahora espera solo 042).
