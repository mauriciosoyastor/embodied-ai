# Ticket 046 — Research: contención ONNX intra2 vs 4 y presupuesto 10Hz+2Hz en 10c i7-1255U

> Parent: `008-map-yolo-world-s-open-vocab` · Label: `wayfinder:research` · Estado: abierto · Tipo: AFK · Rama: `research/046-contencion-10c` (no prod code modificado)

## Question

¿Qué contención genera `YOLO11n 10Hz ~35ms + YOLO-World-s 2Hz ~57-68ms + YOLO11n-pose 5Hz piggyback + MiDaS small 256 42ms 5Hz` cada uno `intra_op_num_threads=2 inter_op=1 ORT_SEQUENTIAL OMP_NUM_THREADS=2` `yolo.py:302` `depth.py` `pose.py` `yolo_world.py:40` en `i7-1255U 10c/12t (2P+8E)` con `asyncio.gather(to_thread)` `ws.py:825` + `AsyncLeakyQueue N=1` dual `fast_queue 10Hz ws.py:636` / `slow_queue 5Hz ws.py:637` + `VLM 1Hz` detached?

Evaluar: `110:15` `Config 640 FP32 intra2/ALL p50 49.8 p95 54.6 glass 54.1` vs `intra4`, `110:28` `config.py ONNX_INTRA_OP 2` duplicado hardcoded deuda, `110:73` `glass 480 ~28ms + 3ms preprocess + 2ms NMS + 10ms JPEG = 75-110ms ✅` vs `640 glass 54ms solo YOLO`; `ws.py:739 fast_processor record_inference/record_total` no `record_yolo/record_glass` `metrics.py:125`; `slow_queue` параллел `pose+depth via asyncio.gather(to_thread)` con `intra=2` cada uno → contención si `intra4`; `dropped_frames_total` `metrics.py`; `MAX_FPS=10` `WS_BUFFERED_LIMIT 64KB` `ws-client.js:88`.

Resolver vía subagente `research`: leer `yolo.py:299-303 SessionOptions`, `config.py:28-30`, `ws.py:739`, `metrics.py:45-128`, `docs/agents/research/110-fp16-imgsz-yolo-30ms.md`, bench `IMGSZ 640 vs 480 vs 320` latencia `yolo_infer_p50` / `glass p50` / `achieve <30ms` + anchors 8400 vs pérdida small `<3% area` `YOLO_AREA_MIN 0.03`; producir recomendación `IMGSZ` + `intra_op` + thread pinning unificado para World-s 2Hz sin `dropped_frames`.

## Notes

- Consultar skill `research` (AFK). No modificar `ws.py` ni `yolo.py`. Capturar hallazgos en rama `research/046-contencion-10c`.
- Reusa medidas `110:73` + `r2:137` latency table; `metrics.py GET /metrics yolo_infer_p50/glass_to_glass_p50` ventana 200.

## Blocking

- Bloquea a 048. Desbloqueado (frontera).

## Resolution

> Estado: **abierto** — frontera. Claim asignando a dev antes de trabajar.
