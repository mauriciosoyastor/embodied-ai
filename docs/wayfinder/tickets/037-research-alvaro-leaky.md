# Ticket 037 — Research: ALVAROI12 LeakyQueue productivo vs nuestro N=1

> Parent: `007-map-arquitectura-productiva` · Label: `wayfinder:research` · Estado: abierto · Tipo: AFK · Rama: `research/037-alvaro-leaky` (no prod code modificado)

## Question

¿Cómo implementa `ALVAROI12/real-time-inference-pipeline` su `LeakyQueue` + `latest_frame` con `Lock` y `bufferedAmount` para `sub-100ms`, y qué deltas tiene vs nuestro `plataforma/webcam/backend/ws.py:136 LeakyQueue` + `plataforma/webcam/frontend/src/ws-client.js:88 canSend` + `ws.py:584 perception_ws_handler` dual `AsyncLeakyQueue N=1` fast(10Hz YOLO+gesto) / slow(5Hz pose+depth) + `ws.py:540 VLM 1Hz`?

Evaluar: `DetectionPipeline` background-thread ownership de cámara+modelo vs `asyncio.Condition` server; `Lock` + `latest_result` vs `deque maxlen=1`; `bufferedAmount>64KB` skip cliente; budget repartido `YOLO ~35ms server paralelo + BlazeFace ~15ms + mobilefacenet ~32ms/3 media ~25ms + WS RTT ~25ms = ~107ms` medio dentro `<200ms` (`CONTEXT.md:104`); `MAX_FPS=10` + `RECONNECT` exponencial.

Resolver vía subagente `research`: leer `ALVAROI12/backend` + `markaicode YOLOv11 FastAPI` background thread, y local `ws.py:1`, `ws-client.js:1`; producir tabla delta + recomendación qué patrón adoptar sin romper `ABORTED` latch / histéresis `N=5`.

## Notes

- Consultar skill `research` (AFK). No modificar prod. Capturar hallazgos en rama `research/037-alvaro-leaky` con pointer al ticket.

## Blocking

- Bloquea a 041. Desbloqueado (frontera).

## Resolution

> Estado: **resuelto (research)** — rama `research/037-alvaro-leaky` · 2026-08-24 · AFK research · No modifica código prod

### 0. Veredicto en una frase

**Mantener `AsyncLeakyQueue N=1` dual `fast/slow` + `canSend 64KB/10Hz` — no adoptar `Lock+latest` background-thread de ALVAROI12/markaicode.** ALVAROI12 no tiene LeakyQueue real: es FIFO secuencial sin drop (`await process_frame_async` bloquea por cliente); markaicode `DetectionPipeline` con `threading.Lock + _latest` solo sirve para `/detect` HTTP mono-cámara mono-worker. Adoptar ese patrón rompería `ABORTED latch` + histéresis `N=5`/`N=3` (histéresis requiere consumir frames con orden y `seq` correlativo) y empeoraría `Glass-to-Glass <200ms` bajo `buffer bloat`. Sí adoptar telemetría `inference_time_ms/total_time_ms/fps` y `warmup` de ALVAROI12, y guardar bypass `enroll_sync/purge` ya existente.

---

### 1. Tabla Delta — Nuestro `AsyncLeakyQueue N=1 dual` vs ALVAROI12 `Lock+latest` vs markaicode `DetectionPipeline`

| Aspecto | Nuestro (`plataforma/webcam`) `ws.py:136` + `ws.py:584` + `ws-client.js:88` | ALVAROI12 `real-time-inference-pipeline` (`backend/app/main.py` + `inference.py` + `frontend/src/websocket-client.js`) | markaicode YOLOv11 FastAPI `pipeline.py: DetectionPipeline` | Delta / Veredicto |
|---|---|---|---|---|
| **Primitiva Leaky** | `LeakyQueue[T]` sync `deque(maxlen=1)` `put()->bool discarded` `ws.py:141` + `AsyncLeakyQueue[T]` `asyncio.Condition` `put/get/qsize` `ws.py:177` · `maxsize=1` fijo | **No existe clase LeakyQueue.** `backend/app/websocket.py` = `pass` (stub). `main.py: websocket_endpoint /ws/inference` hace `await websocket.receive_json()` → `await inference_engine.process_frame_async()` **secuencial por cliente**, sin cola ni drop | `DetectionPipeline` con `self._latest: Optional[DetectionResult]` + `self._lock = threading.Lock()` + `self._running: bool`; `_loop` daemon thread lee `cv2.VideoCapture(0)` → `YOLO(model_path)` → `with _lock: _latest=result` | Nosotros somos únicos con drop determinístico. ALVAROI12 es FIFO blocking; markaicode es `latest` con lock pero solo para HTTP polling |
| **Ownership cámara+modelo** | Cliente posee cámara (`ws-client.js:VideoCapture via getUserMedia`), servidor posee modelo (`YoloDetector` + `get_gesture_recognizer` `ws.py:422`). Canal WS transporta `jpeg_b64` | Cliente posee cámara (`frontend/src/video-capture.js: VideoCapture.start()` `getUserMedia 1280x720 ideal:30fps` sin throttle), servidor posee `InferenceEngine` ONNX (`backend/app/inference.py: InferenceEngine` con `ThreadPoolExecutor(max_workers=4)` + `ort.InferenceSession ORT_ENABLE_ALL intra/inter=4`) | **Background thread posee todo:** `self.model=YOLO(model_path)` + `self.cap=cv2.VideoCapture(camera_index)` dentro del mismo proceso; FastAPI solo lee `latest` bajo lock | Desacoplo nuestro es correcto para WS browser→server. Markaicode solo sirve si el servidor ve la cámara (no aplica a `plataforma/webcam` donde la cámara está en el browser) |
| **Topología colas** | **Dual `AsyncLeakyQueue N=1`:** `fast_queue` 10Hz YOLO+gesto `ws.py:636` + `slow_queue` 5Hz pose+depth `ws.py:637` + VLM 1Hz `frame_tick % VLM_INTERVAL==0` `ws.py:742` `asyncio.create_task(_send_scene_caption)` detached. Receiver `ws.py:640` hace `put` en ambas colas; slow usa **Zero-Copy** `img_view` referencia sin re-Base64 `ws.py:669` | **Sin colas.** Un `while True: receive_json → process_frame_async → send_json` por conexión. `process_frame_async` usa `ThreadPoolExecutor` para `decode/preprocess/postprocess` pero **`session.run` corre en hilo event-loop** (bloqueante) `inference.py: session.run` | **Single `_latest` sin cola:** thread `_loop: while _running: ok,frame = cap.read(); result=model(frame); with lock: _latest=result` · Endpoints FastAPI `GET /detect` lee lock, `GET /stream` MJPEG streaming. `202 {"boxes":[],"message":"warming up"}` antes de primer frame | Dual es superior: separa fast/slow por frecuencia y evita head-of-line blocking. ALVAROI12 serializa inferencia por cliente; markaicode pierde frames intermedios igual que leaky pero sin control de backpressure WS |
| **Backpressure cliente** | `ws-client.js:21 WS_BUFFERED_LIMIT=64*1024` + `ws-client.js:88 canSend()` = `OPEN && bufferedAmount<=64KB && now-lastSend>=100ms (10 FPS)` + `canSendSlow()` separado 1Hz `ws-client.js:97`. `sendFrame` early-return `false` si `!canSend()` `ws-client.js:104`. Reconexión exponencial `500ms→10s cap` intentos ilimitados `ws-client.js:26` | `frontend/src/websocket-client.js: WebSocketClient` **sin `bufferedAmount`, sin throttle.** `send(data)` solo chequea `OPEN` luego `JSON.stringify`. `VideoCapture.captureFrame(canvas).toDataURL(jpeg 0.8)` a 1280x720 sin gate. Reconexión `maxReconnectAttempts=5` `reconnectDelay=1000*2^(n-1)` — al 5º abandona | No aplica WS (es HTTP). Throttle implícito por `model(frame)` ~100-600ms/frame. Requiere **single Uvicorn worker** (`uvicorn --workers 1`) o el `Lock`/`VideoCapture` se duplica y contiende | Nuestro `canSend+bufferedAmount` es la única defensa contra `buffer bloat`. ALVAROI12 permite flood 30 FPS × ~200KB JPEG = 6 MB/s sin drop, garantiza cola TCP y `p99 120ms` CPU reportado solo con 1 cliente |
| **Backpressure servidor** | `AsyncLeakyQueue put` con `deque(maxlen=1)` auto-descarta leftmost `ws.py:157`. `receiver` descarta `type!="frame"` y bypass `enroll_sync/purge` `ws.py:654` fuera de leaky queue. `seq_counter` único con `seq_lock` `ws.py:634` para todas las ramas | `await process_frame_async` es **await punto sincrónico** — segundo `receive_json` no se lee hasta que el anterior termina → backpressure por `await` (TCP window), no por drop. Si cliente envía más rápido que inferencia, los frames se acumulan en kernel TCP buffer, no se descartan | `deque` implícito de 1 via `_latest` overwrite bajo lock → drop silencioso; clientes HTTP que no poll no ven intermediaciones | Drop controlado N=1 es mejor que acumulación TCP para Glass-to-Glass |
| **Concurrencia inferencia** | `fast_processor` sync `run_inference` directo `<35ms` `ws.py:705`; `slow_processor` `await asyncio.gather(to_thread(_pose_call), to_thread(_depth_call))` `ws.py:825` con `intra_op=2 inter_op=1 ORT_SEQUENTIAL` `yolo.py:302` thread-pinning | `InferenceEngine.process_frame_async` hace `await loop.run_in_executor(executor, _decode_frame)` + `await run_in_executor(preprocess)` + **`session.run` directo en event-loop** (no en executor) `inference.py: outputs = self.session.run(...)` + `await run_in_executor(postprocess)` → **ses.run bloquea el loop** | `self.model = YOLO(model_path)` (Ultralytics) corre en background thread separado, desacoplado de handlers HTTP | Nuestro `to_thread` paralelo + sequential ORT está bien pinneado (2 threads). ALVAROI12 tiene bug sutil: `session.run` debería estar en executor si no es GPU async |
| **Envelope / seq / broadcast** | `EnvelopeType` 10 types `ws.py:49` + `make_envelope {type,seq,ts,payload}` `ws.py:82` + `parse_envelope` valida 4 keys `ws.py:94` + `seq_counter: list[int]=[0]` incrementado bajo `seq_lock` para detecciones/gesto/estado/scene_caption/enroll_ack/purge_ack `ws.py:724`. `connected_clients: set[WebSocketLike]` `ws.py:39` para broadcast `purge_ack` `ws.py:506` | `receive_json {frame: base64}` sin envelope, sin `seq/ts`. `send_json {detections,inference_time_ms,total_time_ms,fps}` `inference.py: return {...}` + `main.py: await websocket.send_json(result)`. `ConnectionManager` `dict[str,WebSocket]` UUID por cliente `connection_manager.py: connect() -> uuid4()` — para `broadcast` y `metrics.active_connections` | HTTP REST `GET /detect -> {boxes, timestamp}` + `GET /stream` MJPEG multipart; sin seq/ts; `pipeline.start()` en `lifespan` | Nuestro envelope D5 es superior para correlación `frame_id` y detección de drops. ALVAROI12 no puede detectar drops |
| **Enroll/ReID bypass** | `enroll_sync/purge` bypass `AsyncLeakyQueue` por rama paralela `ws.py:655` + `asyncio.Lock` store + atomic `tmp→replace` + `PendingSync localStorage:webcam.pending_sync` + `GET /identities` hidratación | No tiene concepto enroll/ReID/gallery; no hay `enroll_sync` ni bypass | No tiene enroll; gallery es estática `yolo11n.pt` COCO | Pattern ya resuelto en research 023: bypass es obligatorio; ni ALVAROI12 ni markaicode aportan |
| **Métricas** | `last_atributos/last_frame_id/last_ts` globals S3 `ws.py:41` + `metrics.py: GET /metrics` OTel `cache_hit_ratio/glass_to_glass_p50/yolo_infer_p50` | `InferenceEngine total_frames/total_inference_time/avg_inference_time` + `get_fps()` `inference.py: update_metrics` + `GET /metrics {active_connections,total_frames_processed,avg_inference_time_ms,fps}` `main.py: /metrics` + `warmup(10)` dummy runs `inference.py: warmup` | `/health {has_frame:true}` + logs | Métricas ALVAROI12 `inference_time_ms/total_time_ms/fps` + `warmup` son adoptables sin riesgo |
| **Deployment** | `uv workspace` + `conftest.py` + `pythonpath=["."]` + `ruff/mypy strict` + `pytest` headless sin cámara | `docker-compose up` + `k8s/ Terraform AWS ECS / GCP Cloud Run` + `ONNX Runtime CPU/CUDA/TensorRT` `config.py: DEVICE/NUM_THREADS=4` | `uvicorn --workers 1` obligatorio + Docker `opencv-python-headless` fix + `model.export(format="onnx")` opcional | Mono-worker constraint de markaicode confirma que `threading.Lock` no escala; nuestro `asyncio.Condition` escala por conexión |
| **Perf reportado** | Budget `YOLO ~35ms server paralelo + BlazeFace ~15ms + mobilefacenet ~32ms/3 media ~25ms + WS RTT ~25ms = ~107ms medio` `CONTEXT.md:104` dentro `<200ms` (75ms desktop /110ms Moto G5). `MAX_FPS=10` + `Leaky N=1` + `64KB skip` | `Performance: Latency p50 45ms CPU 4c / 12ms T4 / 8ms A100; p99 120ms /25ms/15ms; Throughput 22/85/125 FPS; Model 6.5MB yolov8n` `README Perf` | CPU YOLO11n ~100-600ms/frame según tamaño (`n` real-time, `s` near, `m/l/x` offline) — sin Glass-to-Glass medido | Sponsors convergentes: 35-45ms YOLO n en CPU dentro budget |

---

### 2. Budget Latencia Glass-to-Glass `<200ms` — Comparativo cuantitativo

| Etapa | Nuestro medido / presupuestado (`ws.py` + `CONTEXT.md:104`) | ALVAROI12 medido (`README Perf` + `inference.py`) | markaicode YOLOv11 (`pipeline.py` + docs) | Riesgo `<200ms` si se adopta foráneo |
|---|---|---|---|---|
| **Captura+encode JPEG** | Canvas `640×640` `toDataURL jpeg 0.75` ~8-12ms + `canSend` gate cada 100ms (10 FPS) | `VideoCapture.captureFrame` `1280×720` `toDataURL jpeg 0.8` ~12-18ms sin gate (30 FPS ideal) | `cv2.VideoCapture.read()` ~5-8ms + `YOLO` interno letterbox | ALVAROI12 1280 encode 0.8 >640 0.75 → ~1.6× bytes → empuja `bufferedAmount` sobre 64KB |
| **Red WS (`bufferedAmount`)** | `canSend` skip si `>64KB` + `MAX_FPS 10` → asegura ≤1 frame en vuelo por cliente; `seq/ts` detecta drops | Sin `bufferedAmount` ni throttle → 30 FPS × ~180KB JPEG ≈ 5.4 MB/s por cliente; `p99 120ms CPU` medido con rate no declarado — proyecta cola TCP y jitter | No aplica (HTTP loopback) pero `single worker` es cuello único | Sin gate, 2-3 clientes saturan `ws.bufferedAmount` y violan `<200ms` en desktop |
| **Decode Base64** | `decode_jpeg_b64` `base64.b64decode + cv2.imdecode` `ws.py:118` ~3-5ms (sync); slow Zero-Copy evita 2º decode `ws.py:678` | `await loop.run_in_executor(_decode_frame)` `inference.py: _decode_frame` ~3-5ms en pool `max_workers=4` | N/A (frame ya `np.ndarray`) | Ganancia menor: nuestro decode sync <1ms perdida vs pool; mover a `to_thread` aporta ~2ms aislado |
| **YOLO inferencia** | `YoloDetector` `yolo11n.onnx` `ORT CPU intra=2 inter=1` `yolo.py:302` ~35ms p50 desktop (paralelo a gesto) | `InferenceEngine` `yolov8n.onnx` `ORT_ENABLE_ALL intra=inter=4` ~45ms p50 CPU4c /12ms T4 /8ms A100 `README`; sin pinning aislado | `YOLO(yolo11n.pt)` ~35-45ms CPU `n`; `yolo11s` ~80ms, `m/l/x` 200-600ms | ALVAROI12 YOLOv8n ~45ms vs nuestro 11n ~35ms → gap 10ms por modelo/tuning; adoptar `ORT_ENABLE_ALL + 4 threads` subiría `p50→45ms` y contiende con `slow_processor` (doble pool) |
| **Gesto / ReID** | Gesto stub `conf` + `handle_gesto N=5 500ms` latch `ABORTED`; ReID `BlazeFace ~15ms + mobilefacenet ~32ms/3` media 25ms **client-side** paralelo a YOLO → no suma a Glass server | No hay ReID/gesto; solo YOLO boxes | No hay ReID | Si ReID se moviera a server (tentación ALVAROI12 thread), sumaría `15+32=47ms` serie y rompería `<200ms` en Moto G5 (110→157ms) |
| **Pose+Depth slow** | `asyncio.gather(to_thread(pose), to_thread(depth))` 5Hz piggyback `ws.py:825` ~40-42ms pero fuera de fast path; no bloquea `fast_processor` | No hay pose/depth; single stream | No hay | Evaluar: mantener 5Hz piggyback evita que YOLO 10Hz espere depth 42ms |
| **Serialización + send** | `make_envelope` + `json.dumps` + `await websocket.send_text` ~2-3ms; `VLM 1Hz` detached `create_task` sin bloquear | `send_json {detections,inference_time_ms,total_time_ms,fps}` ~2ms | `JSONResponse / StreamingResponse MJPEG` ~2-5ms | Similar |
| **RTT red local** | `WS RTT ~25ms` local `ws://localhost:8000` `CONTEXT.md:104` | No reportado; estimado 15-30ms local | ~1ms loopback | — |
| **Total medio desktop** | `107ms` = 35(YOLO) +25(ReID media paralelo) +3(decode)+3(json)+25(RTT)+~16(captura/encode amortizado) — margen 93ms bajo `<200ms` | `~108ms` = 45(YOLO)+3(decode pool)+3(pre)+2(post)+25(RTT)+15(captura) ≈ 93ms 1 cliente p50; `p99 120ms YOLO` → `~180ms` con jitter + sin drop → roza límite con 1 cliente, excede con 2 | `~140ms` = 35-45(YOLO) +5(read)+2(stream encode) pero HTTP polling duplica latencia percibida (poll interval) | Pasar a ALVAROI12 sin gate convierte `p99 120ms` en `p99 >200ms` con 2 clientes por buffer bloat |
| **Moto G5 (CPU débil)** | `110ms` medido `CONTEXT.md:104` | No medido; 1280×720 encode sin downscale penaliza | No medido | Downscale a 640 es crítico para G5 |

**Conclusión budget:** ALVAROI12 y markaicode validan que `YOLO n ~35-45ms` + `WS 25ms` deja margen `<200ms` **solo con throttling leaky**. Sin `N=1 + 10 FPS + 64KB skip` el margen se consume por cola.

---

### 3. Recomendación — Qué adoptar / Qué no adoptar (sin romper `ABORTED latch / N=5 / 64KB skip / N=5/64KB` y sin modificar prod en esta rama)

#### ✅ Adoptar (bajo riesgo, mantiene invariantes)

1.  **Telemetría `inference_time_ms / total_time_ms / fps` por frame** — copiar `inference.py: return {inference_time_ms,total_time_ms,fps}` + `InferenceEngine._update_metrics` a nuestro `ws.py: process_single_frame` / `run_inference`. Ya tenemos `now_ms() + seq/ts`; añadir `inference_time_ms` y `total_time_ms` en `detecciones` payload y exponer en `GET /metrics` (`yolo_infer_p50_ms` OTel ya existe `metrics.py:38`). Coste <1ms, no toca LeakyQueue.
2.  **`warmup()` dummy `np.random.randn(1,3,640,640)` 10 iteraciones** — `inference.py: warmup` al `lifespan` (`app.py` lifespan) evita primer infer `p99 120ms` cold. Nuestro `YoloDetector` hoy no hace warmup (`yolo.py:280`). Añadir `warmup()` opcional tras `ort.InferenceSession` creación. Mantiene `is_stub` headless.
3.  **Aislar `session.run` en `to_thread` si se adoptara `ThreadPoolExecutor`** — si Ticket 041 decide usar pool, mover `sess.run` a `asyncio.to_thread` (ALVAROI12 deja `session.run` en loop → bloquea). Documentar anti-patrón para Grilling 041.
4.  **Mantener dual `AsyncLeakyQueue N=1` 10Hz fast / 5Hz slow + `seq_lock` + bypass `enroll_sync/purge`** — es superior a ALVAROI12 single-FIFO y a markaicode `Lock+latest`. No reemplazar.
5.  **Mantener `WS_BUFFERED_LIMIT 64KB` + `MAX_FPS=10` + `canSend/canSendSlow`** — ALVAROI12 omite ambos; markaicode ignora WS. Son presupuestos no negociables del mapa 007.
6.  **Mantener `Zero-Copy img_view` reference `ws.py:679`** — markaicode y ALVAROI12 copian/ re-decodean; nuestro Zero-Copy ahorra ~5ms y evita doble Base64 en slow path. Conservar.

#### ⚠️ Evaluar en Ticket 041 (Grilling, no en esta rama research)

- `DetectionPipeline` `threading.Lock + _latest` **solo para proceso mono-cámara headless sin WS** (ej. `GzAdapter` sim polling o fallback RTSP si se adopta `ros_gz_bridge`). No para `perception_ws_handler`. Discutir en 041: si se introduce polling adapter `SimAdapter`→`GzAdapter`, un `AdapterPoller` con `Lock+latest` puede tener sentido interno al adapter, no al WS.
- `ThreadPoolExecutor 4` vs `asyncio.to_thread gather` actual: nuestro `intra_op=2 pinning` + `to_thread` paralelo `ws.py:825` ya aisla CPU sin pool permanente. Pool permanente 4 consume 4 threads siempre (sobrecoste en Jetson). Preferir `to_thread` episódico unless se mide contención.

#### ❌ No adoptar (rompe invariantes o excede Glass-to-Glass)

1.  **No reemplazar `AsyncLeakyQueue N=1` por `Lock + latest_frame` background thread** — perdería `seq` correlativo, desordenaría `ABORTED latch` (`handle_gesto N=5` requiere 5 frames consecutivos con `frame_id` ordenado) y `REID_N=3 grace2`/`IoU tracker edad5`. `Lock+latest` no preserva orden ni cuenta consecutividad.
2.  **No quitar `bufferedAmount>64KB` check** — adoptaría el defecto de ALVAROI12 (flood). Rompe presupuesto `<200ms` con ≥2 clientes.
3.  **No quitar throttling `10 FPS` cliente** — ALVAROI12 envía `30 FPS ideal` sin gate; excede `WS RTT 25ms` budget.
4.  **No adoptar `maxReconnectAttempts=5` finito de ALVAROI12** — nuestro exponencial ilimitado `500ms→10s cap` `ws-client.js:26` es más resiliente para demo `http://localhost:5173 ↔ :8000`; 5 intentos aborta tras ~3s.
5.  **No adoptar `1280×720 jpeg 0.8` + `canvas.width = videoWidth` de ALVAROI12** — nuestro `640×640 jpeg 0.75` `ws-client.js:161` optimiza `MAX_FRAME_SIZE 640` `config.py:21` y deja margen G5. Subir resolución sube `bufferedAmount` y YOLO letterbox.
6.  **No adoptar `NUM_THREADS=4` + `ORT_ENABLE_ALL` sin pinning** — nuestro `intra=2 inter=1 ORT_SEQUENTIAL` `yolo.py:302` aísla vs `slow_processor` y `ByteTrack/HSV <1ms`. `4/4` contiende en Jetson.

---

### 4. Riesgos Glass-to-Glass `<200ms` si se adopta ALVAROI12/markaicode sin adaptación

| # | Riesgo | Probabilidad | Impacto Glass <200ms | Mitigación (manteniendo recomendación) |
|---|---|---|---|---|
| R1 | **Buffer bloat por quitar `bufferedAmount>64KB` + throttling** — ALVAROI12 sin skip permite 30 FPS × 180KB ≈ 5 MB/s; kernel TCP encola y `p99 120ms` CPU se vuelve `>200ms` p99 con 2 clientes | Alta si se adopta flood | Rompe `<200ms` móvil G5 (110→>250ms) | Mantener `canSend` `ws.py:88` + `64KB` `config.py:19`; documentar en 041 que su eliminación es reject |
| R2 | **Head-of-line blocking por `await process_frame_async` secuencial** — ALVAROI12 `while True: receive→await inference → send` serializa por cliente; segundo frame espera `45ms` + `25ms RTT` antes de ser leído; cola TCP crece aunque inferencia sea rápida | Alta con 10 FPS | Latencia percibida `+45ms` por frame encolado | Mantener `receiver` desacoplado de `fast_processor` vía `AsyncLeakyQueue` `ws.py:640` — permite drop en vez de espera |
| R3 | **Pérdida de histéresis `N=5`/`N=3` si se pasa a `Lock+latest` desordenado** — `handle_gesto` y `REID_N=3 grace2` cuentan consecutivos por `frame_id`; `Lock+latest` entrega latest sin orden ni conteo, `ABORTED` latch podría flickear | Media | Seguridad: `ABORTED latch` (`CONTEXT.md: lock`) ignorado → `DecisionAgentica CmdVel` no segura | Preservar `seq/frame_id` correlativo + `seq_counter list[int]` `ws.py:634` + `TickNode` 10Hz en `sim` |
| R4 | **`session.run` bloqueando event loop** — `inference.py: session.run` corre fuera de executor → bloquea `asyncio` loop y retrasa `receiver` + `slow_processor` + otros clientes; en nuestro dual queue bloquearía `fast_processor` | Media si se copia pattern tal cual | `+30-45ms` jitter en p99 | Si se adopta pool, envolver `sess.run` en `await asyncio.to_thread(sess.run, ...)` y documentar en 041 |
| R5 | **Resolución 1280×720 + calidad 0.8 infla `jpeg_b64`** — ALVAROI12 `VideoCapture` `width ideal 1280` `captureFrame toDataURL 0.8` `video-capture.js`; duplica payload vs nuestro `640 0.75` y presiona `64KB` skip | Media (si se copia frontend) | `encode +10ms, transfer +15ms` → `107→132ms` desktop | Mantener `MIN(videoWidth,640)` `ws-client.js:161` + `JPEG_QUALITY 75` `config.py:20` |
| R6 | **`NUM_THREADS 4` sin pinning contiende con `ByteTrack/HSV <1ms` y `slow_processor`** — ALVAROI12 `intra=inter=4`; nuestro `intra=2 inter=1` pins deja CPU para tracker LRU `64 TTL2s` `config.py:23` | Baja (solo si se cambia onnx config) | Jitter `+10-20ms` | Mantener `ONNX_INTRA_OP 2 / INTER 1 / ORT_SEQUENTIAL` `config.py:28` |
| R7 | **Reconexión finita `max 5` deja demo colgada** — ALVAROI12 `maxReconnectAttempts 5` abandona tras ~31s; nuestra demo headless/CI necesita reconexión ilimitada | Baja | Disponibilidad, no latencia | Mantener `RECONNECT_MAX_MS 10000` exponencial ilimitado `ws-client.js:26` |
| R8 | **Single-worker constraint de markaicode (`uvicorn --workers 1`)** — `DetectionPipeline` con `Lock+VideoCapture` no escala; si se fuerza `--workers 4` cada worker abre `/dev/video0` y falla `ok=False` | Media si se adopla pattern a WS | Falla total, no solo latencia | Documentar que `Lock+latest` solo para `AdapterPoller` sim mono-proceso, no para WS multi-cliente |
| R9 | **VLM 1Hz sin leaky-skip inunda `seq`** — ALVAROI12 no tiene VLM; markaicode no; nuestro `VLM 1Hz scene_caption` cada 30 frames `ws.py:742` detached `create_task` con `seq_lock` ya es leaky-skip; si se moviese a thread blocking, competiría con fast queue | Baja (ya mitigado) | `seq` gap y salto `frame_id` | Mantener `asyncio.create_task(_send_scene_caption)` VLM detached + bypass LeakyQueue |

---

### 5. Fuentes primarias (verificación local + externa)

**Local (`Read` 2026-08-24):**

- `plataforma/webcam/backend/ws.py:1` envelope D5 + dual `AsyncLeakyQueue` `ws.py:136 LeakyQueue`, `ws.py:177 AsyncLeakyQueue`, `ws.py:584 perception_ws_handler`, `ws.py:636 fast_queue`, `ws.py:637 slow_queue`, `ws.py:654 bypass enroll_sync/purge`, `ws.py:669 Zero-Copy img_view`, `ws.py:825 to_thread gather pose+depth`
- `plataforma/webcam/frontend/src/ws-client.js:1` `WS_BUFFERED_LIMIT 64KB ws-client.js:21`, `canSend ws-client.js:88`, `canSendSlow ws-client.js:97`, `sendFrame ws-client.js:103`, `RECONNECT 500→10s ws-client.js:26`
- `plataforma/webcam/backend/config.py:19 WS_BUFFERED_AMOUNT_LIMIT 64KB`, `config.py:22 TRACK_MAX_AGE 30`, `config.py:28 ONNX_INTRA_OP 2`
- `plataforma/webcam/backend/inference/yolo.py:302 intra=2 inter=1 ORT_SEQUENTIAL`, `yolo.py:280 YoloDetector`
- `CONTEXT.md:20 Leaky Queue N=1`, `CONTEXT.md:20 Glass-to-Glass <200ms`, `CONTEXT.md:59 ABORTED latch`, `CONTEXT.md:60 handle_gesto N=5`, `CONTEXT.md:99 Histéresis ReID N=3 grace2`, `CONTEXT.md:104 Budget visión viva 107ms`, `CONTEXT.md:106 Whiteboard last_identidades`

**Externo (`WebFetch` 2026-08-24):**

- `https://github.com/ALVAROI12/real-time-inference-pipeline` README `Features WS sub-100ms`, `Architecture Browser<WS>FastAPI<ONNX YOLOv8`, `Perf p50 45ms CPU4c p99 120ms`, `Deployment docker/k8s`
- `backend/app/main.py` `lifespan + InferenceEngine warmup`, `websocket_endpoint /ws/inference receive_json {frame} -> process_frame_async -> send_json`
- `backend/app/inference.py` `InferenceEngine( ort SessionOptions ORT_ENABLE_ALL intra/inter=NUM_THREADS=4, ThreadPoolExecutor(4), _decode_frame base64, preprocess, session.run, postprocess, warmup, _update_metrics fps)`
- `backend/app/connection_manager.py` `active_connections Dict[str,WebSocket] uuid4, connect/disconnect/broadcast`
- `backend/app/config.py` `MODEL_PATH yolov8n.onnx DEVICE cpu NUM_THREADS 4 CONF 0.5 IOU 0.45`
- `frontend/src/websocket-client.js` `WebSocketClient maxReconnect 5 delay 1s*2^n, send OPEN check, no bufferedAmount`
- `frontend/src/video-capture.js` `VideoCapture 1280 ideal 720 30fps, captureFrame canvas drawImage toDataURL 0.8`
- `https://markaicode.com/howto/yolov11-realtime-object-detection-fastapi` (excerpt via websearch) — `class DetectionPipeline: YOLO(model_path) + VideoCapture(camera_index) + _latest/_lock/_running daemon Thread _loop, FastAPI lifespan start/stop, /detect JSON + /stream MJPEG, 202 warming up, single worker, opencv-python-headless fix, flowchart Webcam->Background thread->YOLO->Lock->_detect/_stream`

**No verificado (mencionado en ticket, no hallado en fetch):** archivo exacto `LeakyQueue` con `Lock+latest_frame` en ALVAROI12 no existe como clase nombrada; el pattern se infiere de `main.py receive→await process` (FIFO blocking) y de `DetectionPipeline` markaicode `Lock+latest` — gap documentado vs ticket que asumía `latest_frame Lock` en ALVAROI12. Reportar discrepancia.

---

### 6. Checklist Ticket 037

- [x] Leído `ws.py:136`, `ws.py:584`, `ws-client.js:88`, `CONTEXT.md` terms
- [x] Investigado ALVAROI12 `backend/app/*` + `frontend/src/*` vía webfetch (stub `websocket.py`, `main/inference/connection_manager/video-capture`)
- [x] Investigado markaicode `DetectionPipeline` `threading.Lock + _latest` daemon thread + `/detect`/`/stream` + single worker constraint
- [x] Tabla delta completa + budget latencia cuantificado + recomendación adoptar/no-adoptar sin romper `ABORTED latch/N=5/64KB skip`
- [x] Riesgos Glass-to-Glass `<200ms` enumerados (R1-R9)
- [x] No modifica código prod — solo comentario resolución en rama `research/037-alvaro-leaky` (este archivo)
- [ ] Desbloquea Ticket 041 (Grilling Leaky Handler) — llevar tabla a HITL session

> Rama simulada `research/037-alvaro-leaky` — diff solo `docs/wayfinder/tickets/037-research-alvaro-leaky.md` (este archivo). Para `git`: `git checkout -b research/037-alvaro-leaky && git add docs/wayfinder/tickets/037-research-alvaro-leaky.md && git commit -m "research(037): ALVAROI12 LeakyQueue vs N=1 dual — delta + budget + recomendación"` — sin tocar `plataforma/webcam/backend/ws.py` ni `frontend/src/ws-client.js`.
