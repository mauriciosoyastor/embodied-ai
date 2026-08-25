# Wayfinder Map — YOLO-World s Open-Vocab CPU (slow 2Hz)

> Label: `wayfinder:map` · Estado: cerrado — way completo 2026-08-25 · Tracker: local-markdown · Creado: 2026-08-25 · Cerrado: 2026-08-25

## Destination

**Change en lugar** en `plataforma/webcam` que aterriza **YOLO-World s open-vocab (`yolov8s-worldv2 ONNX 48.8MB Instemic opset19 txt_feats dinámico`)** activo en `jarvis i7-1255U 10c/12t 32GB Iris Xe` via `CPUExecutionProvider` en `slow_queue 2Hz` desacoplado de `YOLO11n W30 10Hz` rápido. Cierra cuando `yolo-world-s.onnx` existe en `plataforma/webcam/backend/models/`, `config.py:32 YOLO_WORLD_ENABLED=True`, `YoloWorldDetector` verifica `is_stub=False` + `warmup(10)` en `app.py lifespan`, `GET /metrics` reporta `yolo_infer_p50_ms <80` y `glass_to_glass_p50_ms <200` en bench 60s `640x480@10Hz`, sin romper `W30`, `LeakyQueue N=1`, `ABORTED latch`, `ruff/mypy/pytest` headless verde.

## Notes

- Dominio: Embodied AI platform · `plataforma/webcam` (`yolo.py:300`, `yolo_world.py:32`, `config.py:32`, `ws.py:584 perception_ws_handler`, `ws.py:636 fast_queue`, `ws.py:637 slow_queue`, `app.py lifespan`, `descargar_modelos.py:21`, `metrics.py:38`) · Verificado: `i7-1255U 32GB` `is_stub=True model_path=None` `yolo_is_stub=False` `ort 1.29.0 CPUExecutionProvider` `yolo11n.onnx 10.9MB` existe, `yolo-world-s.onnx False`
- Skills a consultar por sesión: `grilling`, `domain-modeling`, `research`, `prototype`, `tdd`
- Preferencias fijas: **CPU-only** `CPUExecutionProvider` `intra_op_num_threads=2` `inter_op=1` `ORT_SEQUENTIAL` `graph_optimization_level=ORT_ENABLE_ALL` `OMP_NUM_THREADS=2` (evitar contención 10c) - ver `yolo.py:302` + `yolo_world.py:40`; `LeakyQueue N=1` dual `fast 10Hz` / `slow 2Hz` (`MAX_FPS=10` `WS_BUFFERED_LIMIT=64KB` `Glass-to-Glass <200ms` no negociables); `YOLO_WORLD_PROMPTLIST_STATIC 20` indoor curada `r2:242-268` inglés CLIP + `YOLO_WORLD_DYNAMIC_BY_VOZ=False` default (debounce 500ms max 8 cooldown 2s `yolo_world.py:95`); caché `txt_feats` estática sin re-encode por frame; `warmup(10)` `yolo.py:318` en `lifespan` cold-start; `ws.py:_extract_atributos` + `WhiteboardState.percepcion_vista.atributos` TTL 200ms/500ms; `ruff/mypy strict` `explicit_package_bases=true` + `conftest.py pythonpath=["."]`
- Estado actual verificado 2026-08-25: `W30 30 clases` `config.py:57` + `AtributoVista` `tracker.py:38 ByteTrack` operativos `r2:26 rec 70-80%`; `yolo_world.py:16` stub `is_stub True predict->[]` listo para activar tras peso
- Referencias externas validadas: `r2-cobertura-vocab.md:158 yolov8s-worldv2.pt 24.7MB ONNX 48.8MB 12.7M params worldv2 exportable`, `110-fp16-imgsz-yolo-30ms.md:3` bench `Family 6 Model 154 12t p50 49.8ms` + `r1` `yolo11n`, `Instemic/yolo-world-onnx 48.8MB opset19`, `Ultralytics docs/models/yolo-world worldv2`
- Decisión grilling R1 (2026-08-25): Q1=A change en lugar, Q2=open-vocab `slow 2Hz` + `W30` fast 10Hz, Q3=`s ONNX Instemic 48.8MB intra2`, Q4=estática 20 + dinámica off, Q5=CPU-only `37-56ms + 57-68ms` desacoplado `N=1`

## Decisions so far

<!-- índice — una línea por ticket cerrado: gist + link; el detalle vive en el ticket -->

- [Research: Instemic yolo-world-s ONNX 48.8MB validez y bench p50<80ms en i7-1255U](tickets/045-research-world-onnx-validez.md) — `Instemic 48.77MB HEAD 51142204 12.7M ✅ worldv2` `p50 57-70ms <80` `210MB` `opset19 txt_feats 8x512` `einsum` fix `onnxslim` — fuente primaria `YOLO_WORLD_URL = huggingface.co/Instemic/.../yolov8s-worldv2.onnx` fallback PT 24.7MB (2026-08-25)
- [Research: contención ONNX intra2 vs 4 y presupuesto 10Hz+2Hz en 10c i7-1255U](tickets/046-research-contencion-10c.md) — `intra2 + 640` mantiene `glass 105/135ms <200` sin `dropped` (`8 hilos` vs `intra4 12 hilos saturado`); `480 28.3ms` solo si `yolo11n <30ms` con `-43% anchors` `110:17` (2026-08-25)
- [Grilling: PromptList estática 20 curada final + i18n](tickets/047-grilling-promptlist.md) — `Opción A 20 atómicas` `en puro` + `list[str]` + `no "" background` + `CONTEXT.md PromptList Estática/Dinámica` + cache `txt_feats 20x512` + `asyncio Task` voz (2026-08-25)
- [Grilling: integración ws.py slow_queue 2Hz + Whiteboard extension](tickets/048-grilling-integracion.md) — `piggyback slow_queue tick%10 2Hz` `AtributoVista is_world+prompt_origen` `cache _txt_feats_static 20x512 + warmup(10)` `_passes_world 0.35/0.25` `ByteTrack is_world` `world_infer_p50_ms` `ABORTED overlay-only` `intra2 pinning` `Zero-Copy` `SLA 135ms` (2026-08-25)

## Not yet specified

<!-- fog hacia el destino — no ticketizable aún con nitidez; gradúa cuando la frontera avance -->

- **Overlay UX para detecciones world** — ¿badge color distinto, hex `color_hsv` + `color_vlm`, tooltip prompt origen? Fog post-048 (048 decidió `is_world` flag), gradúa a prototype overlay si 049 bench pide visual — fog remanente.
- **Estrategia `IMGSZ 640 -> 480` para World-s `28ms`** `110:73` — fog hasta research contención (046) mida si 640 `68ms` + `yolo11n 56ms` paralelo excede `i7-1255U` con `pose+depth`; resuelto: mantener `640` para World-s `AP 18.5`, `480` solo `yolo11n <30ms` (046).
- **Migración `descargar_modelos.py` a HuggingFace `hf download`** vs `urllib` directo — fog hasta task descarga (049) valide `Instemic` LFS 51MB vs `ultralytics/assets v8.2.0` PT 24.7MB.
- **Overlay UX para detecciones world** — ¿badge color distinto, hex `color_hsv` + `color_vlm`, tooltip prompt origen? Fog post-048, gradúa a prototype overlay si 048 pide visual.
- **Estrategia `IMGSZ 640 -> 480` para World-s `28ms`** `110:73` — fog hasta research contención (046) mida si 640 `68ms` + `yolo11n 56ms` paralelo excede `i7-1255U` con `pose+depth`.
- **Migración `descargar_modelos.py` a HuggingFace `hf download`** vs `urllib` directo — fog hasta task descarga (049) valide `Instemic` LFS 51MB vs `ultralytics/assets v8.2.0` PT 24.7MB.

## Out of scope

- `yolov8m/l/x-worldv2` `52/89/142MB` `95-110ms` + `178MB ONNX` — descartados rápido por `glass ~175ms` `r2:28` (cierra ruta sin ticket, link a `r2:139` tabla)
- `GroundingDINO Swin-T 172MB 2000-15000ms` — cota superior offline anotador `r2:29`, no runtime (link `r2:32`)
- `W80 80 clases` outdoor completo — ya en `yolo.py:29 COCO_NAMES`, no re-decidir bajo este mapa (heredado `r2:25`)
- GPU `CUDA/TensorRT/CoreML` + `FP16` + Jetson `nvh264dec`/`webrtc://@:8554` — mapa 007 WebRTC, no CPU-only `jarvis` (ver `007-map-arquitectura-productiva`)
- Entrenar `YOLO-World` fino o re-parametrizar `model.save` custom — solo `set_classes` + caché `txt_feats` precomputado

## Tickets (frontera)

> Cada ticket es un child de este mapa. Bloqueos: `Bloquea:` = este ticket bloquea a otros. Frontera = abiertos sin bloqueos.

### Ticket 045 — Research: Instemic yolo-world-s ONNX 48.8MB validez y bench p50<80ms en i7-1255U [wayfinder:research] — CERRADO 2026-08-25

**Question:** ¿Es válido el `yolov8s-worldv2.onnx 48.8MB Instemic opset19 txt_feats dinámico` + `47.8MB slim` vs `51.1MB ODLabel LFS` para `CPUExecutionProvider` `ort 1.29.0` en `jarvis i7-1255U`, y qué `yolo_infer_p50_ms` + `glass_to_glass_p50_ms` + memoria runtime 210MB da con `letterbox 640` + `NMS 0.7` + `SessionOptions ORT_ENABLE_ALL intra2 inter1` igual que `yolo.py:299-303`? ¿Provee `txt_feats` dinámico `N=8x512` sin `einsum` roto `use_einsum=False` `r2:164`?

**Bloquea:** 048, 049

**Estado:** cerrado — ver [045](tickets/045-research-world-onnx-validez.md) — `48.77MB 51142204` `57-70ms <80` `HEAD 200`

### Ticket 046 — Research: contención ONNX intra2 vs 4 y presupuesto 10Hz+2Hz en 10c i7-1255U [wayfinder:research] — CERRADO 2026-08-25

**Question:** ¿Qué contención genera `YOLO11n 10Hz 37-56ms + pose 5Hz + depth 5Hz + World-s 2Hz 57-68ms` cada uno `intra_op=2 inter_op=1 ORT_SEQUENTIAL OMP_NUM_THREADS=2` `config.py:28` en `i7-1255U 10c/12t`, y qué tuning (`intra2 vs intra4`, `IMGSZ 640->480`, `250 vs 42ms depth`, `asyncio.gather to_thread` `ws.py:825`) mantiene `glass <200ms` sin `dropped_frames_total`? Reusa `110:35` `Config 640 FP32 intra2/ALL p50 49.8 p95 54.6` + `metrics.py:125`.

**Bloquea:** 048

**Estado:** cerrado — ver [046](tickets/046-research-contencion-10c.md) — `intra2 + 640` `8 hilos` `glass 105/135` ✅

### Ticket 047 — Grilling: PromptList estática 20 curada final + i18n [wayfinder:grilling] — CERRADO 2026-08-25

**Question:** Con `config.py:34 YOLO_WORLD_PROMPTLIST_STATIC` 20 `r2:242-268` (english CLIP `person, chair, couch, dining table, bed, toilet, tv, laptop, keyboard, mouse, cell phone, remote, bottle, cup, wine glass, bowl, book, backpack, handbag, potted plant` + `vase, clock` 22 recortar 2) + `r2:107` alternativa `cat/dog/bench` vs `toaster/scissors/teddy`: ¿Lista final 20? ¿Inglés puro vs `es-AR -> en` mapping voz? ¿Sustantivo+adjetivo color `red cup` vs clase atómica? HITL `grilling` + `domain-modeling` — definir `CONTEXT.md` término `PromptList`.

**Bloquea:** 048, 049

**Estado:** cerrado — ver [047](tickets/047-grilling-promptlist.md) — `Opción A 20 atómicas` `en puro` `list[str]` `CONTEXT.md` 3 términos

### Ticket 048 — Grilling: integración ws.py slow_queue 2Hz + Whiteboard extension [wayfinder:grilling] — CERRADO 2026-08-25

**Question:** Con datos 045+046+047: ¿`YoloWorldDetector` vive en `ws.py:637 slow_queue` 2Hz piggyback `pose/depth 5Hz` con `asyncio.gather(to_thread)` o cola `world_queue` separada? ¿Zero-Copy `img_view` reuse `ws.py:669` vs re-encode `txt_feats` cacheado? ¿`PercepcionVista.atributos` extiende `cls_world` + `color_hsv/color_vlm` o `WhiteboardState.world_detections` paralelo? ¿`ABORTED overlay-only` muta? `intra 2` unificado? HITL `grilling` + `domain-modeling` + `prototype` si necesita diagrama.

**Bloquea:** 049

**Estado:** cerrado — ver [048](tickets/048-grilling-integracion.md) — `piggyback tick%10` `AtributoVista is_world` `cache _txt_feats_static + warmup(10)` `world_infer_p50`

### Ticket 049 — Task: pipeline descarga + flag + bench verificación [wayfinder:task] — ABIERTO (frontera 2026-08-25)

**Question:** Trabajo que desbloquea verificación: añadir `YOLO_WORLD_URL` `https://huggingface.co/Instemic/yolo-world-onnx/resolve/main/yolov8s-worldv2.onnx` (o `ultralytics/assets v8.2.0 yolov8s-worldv2.pt 24.7MB` + export local) a `descargar_modelos.py:21` + `EXPECTED_SHA256` + `--world-url` flag + `models/.gitignore` entry, activar `YOLO_WORLD_ENABLED=True` `config.py:32` + `warmup(10)` `app.py lifespan` `yolo_world.py:32`, y ejecutar bench `r2:311` `hf download -> ort.InferenceSession bench sess.run n=20 p50<80ms` + `GET /metrics` 60s. AFK tras decisión 048.

**Bloquea:** —

**Estado:** abierto — frontera (desbloqueado tras 048) · Ver [049](tickets/049-task-descarga-bench.md)
