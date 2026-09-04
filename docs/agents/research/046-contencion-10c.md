# 046 — Research: contención ONNX intra2 vs 4 y presupuesto 10Hz+2Hz en 10c i7-1255U

> Ticket: `046 Research: contención ONNX intra2 vs 4 y presupuesto 10Hz+2Hz en 10c i7-1255U` · Parent: `008-map-yolo-world-s-open-vocab` · Fecha: 2026-08-25 · Estado: research done (no cierra ticket) · Bench host: `jarvis i7-1255U 10c/12t (2P+8E) 32GB` `ort 1.29.0 CPUExecutionProvider` `yolo11n.onnx 10.4MB` `yolo-world-s 48.8MB` sin GPU · Rama: `research/046-contencion-10c`

## Pregunta

¿Qué contención genera `YOLO11n 10Hz 37-56ms + YOLO-World-s 2Hz 57-68ms + pose 5Hz + depth MiDaS 42ms 5Hz` cada uno `intra_op=2 inter_op=1 ORT_SEQUENTIAL OMP_NUM_THREADS=2` `yolo.py:302` `yolo_world.py:40` `depth.py` `pose.py` en `i7-1255U 10c/12t`, con `asyncio.gather(to_thread)` `ws.py:825` + `AsyncLeakyQueue N=1` dual `fast 10Hz ws.py:636` / `slow 2Hz ws.py:637` + `VLM 1Hz`? ¿Qué tuning `intra2 vs 4`, `IMGSZ 640->480`, `gating %2` mantiene `glass <200ms` sin `dropped_frames_total`?

## TL;DR — 30s

**Con `intra2` el presupuesto cabe: `YOLO11n 49.8ms + World-s 57-68ms` desacoplados en `slow 2Hz` no contiende si `OMP_NUM_THREADS=2` y `to_thread` paralelo; `intra4` gana -5% (49.8→47.1, 28.3→26.6 `110:17-18`) pero satura 10c (8-10 hilos activos + `ByteTrack/HSV <1ms` `tracker.py:38` + `ws.py` loop) y sube `dropped_frames_total` con `pose+depth` simultáneos `ws.py:825`. Recomendación: `intra2 + IMGSZ 640` para World-s 2Hz `135ms glass ✅` con `yolo11n` 10Hz `105ms`; si se necesita `yolo11n <30ms`, bajar a `IMGSZ 480 28.3ms` `110:17` y mantener `intra2` (no 4) para dejar `6 hilos` libres en `12t`. `FP16` descartado CPU `110:60-63`. Métricas `metrics.py:125` `yolo_infer_p50/glass p50` + `dropped_frames_total` ya exponen contención.**

| Config i7-1255U 10c/12t | `yolo_infer p50` `yolo11n` | `world-s p50` est. | `glass p50` fast | `glass p50` slow 2Hz | Hilos activos | `dropped` | ¿Cabe <200ms? |
|------------------------|---------------------------|--------------------|------------------|-----------------------|---------------|-----------|---------------|
| **640 intra2 ALL** actual `yolo.py:299` | 49.8 `110:15` | 57-68 `r2:138` | 54.1 `110:15` | ~135 `r2:27` | 2+2+2+2=8 (yolo+world+pose+depth) | bajo | ✅ 105/135 |
| 640 intra4 | 47.1 (-5%) | ~55-65 (-4%) | ~51 | ~130 | 4+4+2+2=12 saturado | medio | ✅ pero jitter |
| **480 intra2** | 28.3 `110:17` | ~35-42 est. (0.56x) | 30.8 `110:17` | ~85-100 est. | 2+2+2+2=8 | bajo | ✅✅ con margen VLM |
| 320 intra2 | 13.2 `110:19` | ~18-22 est. | 14.2 | ~55-70 | 2+2+2+2=8 | bajo | ✅ pero pierde small 75% anchors |
| ORT_DISABLE_ALL | 62.9 `110:20` | >80 | >70 | >150 | — | — | ❌ |

> `OMP_NUM_THREADS=2` + `ORT_SEQUENTIAL` unificado `yolo.py:302`/`yolo_world.py:40`/`depth.py`/`pose.py` aísla vs `ByteTrack/HSV LRU 64` `<1ms` `config.py:25`. `intra4` + `8E cores` pequeños → thread thrashing y `slow_processor` `asyncio.gather` serializa.

## 1. Hallazgos código local

| Archivo | Hallazgo |
|---------|----------|
| `plataforma/webcam/backend/inference/yolo.py:23 IMGSZ=640` `298-303` | `SessionOptions.graph_optimization_level=ORT_ENABLE_ALL`, `intra_op=2`, `inter_op=1`, `execution_mode=ORT_SEQUENTIAL`, `providers=["CPUExecutionProvider"]`. `warmup(n=10)` dummy `1x3x640x640` amortiza cold-start. No lee `config.py:29`. |
| `plataforma/webcam/backend/inference/yolo_world.py:36-44` | Idéntico `SessionOptions` `intra2 inter1 ALL SEQUENTIAL` `yolo.py:302`. `is_stub True` sin peso, `set_classes(cleaned[:8])` `yolo_world.py:51` + `txt_feats` cache implica 1 encode 8-15ms amortizado `r2:284`. No `warmup` aún (deuda → `app.py lifespan`). |
| `plataforma/webcam/backend/inference/pose.py:228` `depth.py:150` | Mismo pinning `intra2 inter1 ALL`. `MiDaS small 256` ~42ms 5Hz piggyback `ws.py:825`. |
| `plataforma/webcam/backend/config.py:28-30` | `ONNX_INTRA_OP=2 ONNX_INTER_OP=1` desacoplados de `yolo.py` hardcode (deuda `Ticket 046`). `YOLO_AREA_MIN=0.03` small thr, `WS_BUFFERED_AMOUNT_LIMIT 64KB` `config.py:19`, `YOLO_WORLD_ENABLED False` `config.py:32`. |
| `plataforma/webcam/backend/ws.py:584-825` | `perception_ws_handler` dual `AsyncLeakyQueue N=1` `fast_queue 10Hz YOLO+gesto ws.py:636` + `slow_queue 5Hz pose+depth ws.py:637` (+ `VLM 1Hz` detached `ws.py:742` cada 30 frames `create_task`). `fast_processor ws.py:739` mide `infer_ms/total_ms` `record_inference/record_total` pero no `record_yolo/record_glass` puro `metrics.py:125`. `slow_processor ws.py:825` `await asyncio.gather(to_thread(_pose_call), to_thread(_depth_call))` con `intra2` cada uno → contención si intra4. `receiver ws.py:669` Zero-Copy `img_view` reference evita re-Base64 en slow. |
| `plataforma/webcam/backend/metrics.py:45-128` | `record_yolo(ms)` `record_glass(ms)` `record_dropped_frame()` → `render_prometheus()` `yolo_infer_p50_ms` `glass_to_glass_p50_ms` ventana 200 `GET /metrics` + `dropped_frames_total` counter `ws.py:157 discarded`. Ya listo para profiling 60s `112`. |
| `plataforma/webcam/backend/app.py:48` | `lifespan` `yolo.warmup(10)` si `not is_stub` para `yolo11n`; falta `world.warmup(10)` para World-s (añadir en 049). |
| `docs/agents/research/110-fp16-imgsz-yolo-30ms.md:15` | Bench `640 intra2 49.8 p95 54.6 glass 54.1` `480 intra2 28.3 p95 30.1 glass 30.8` `320 intra2 13.2` `intra4 -5%` `ORT_DISABLE_ALL 62.9` → `ALL` -25% ya activo. |

## 2. Contención 10c — modelado hilos

**i7-1255U topología:** 2 P-cores (4t) + 8 E-cores (8t) = 12t logical. `OMP_NUM_THREADS=2` + `intra2` significa cada `InferenceSession` pide 2 hilos intra-op (ONNX) + 2 hilos OMP (CV2 postprocess) = ~2-3 cores efectivos por inferencia.

**Escenario A — Recomendado `intra2` (8 hilos activos):** `yolo11n 10Hz` (2) `pose 5Hz` (2) `depth 5Hz` (2) `world-s 2Hz` (2) = 8 hilos pico cuando `fast_processor` + `slow_processor` corren paralelos `asyncio.gather` `ws.py:825` (+ world). Con `LeakyQueue N=1` `slow` cada `500ms` y `fast` cada `100ms`, solapamiento ocurre 1 de cada 5 fast frames → `p95` no sube, `dropped_frames_total` bajo. `ByteTrack tracker.py:38 <1ms` + `HSV hist 18 bins <0.1ms` caben en E-cores.

**Escenario B — `intra4` (12 hilos saturado):** cada sesión pide 4 hilos → 4+4+2+2=12 hilos activos, excede 10c físicos + `ws.py` event loop + `uvicorn` workers. Medido `110:16-18` `640 intra4 47.1` solo -5% vs intra2 pero con `pose+depth` en paralelo el `p95` sube `54.6→~60` por thrashing E-cores → `dropped_frames` `fast_qsize>0 skip` `ws.py:845` aumenta. `112-profiling-60s.md` reporta `dropped_frames_total` +30% con intra4.

**Conclusión:** mantener `intra2 inter1 SEQUENTIAL` unificado en `yolo.py:302`/`yolo_world.py:40`/`pose.py`/`depth.py` + `OMP_NUM_THREADS=2` (ver `AGENTS.md` Thread Pinning). No usar `intra4` en 10c a menos que `slow` se serialice (no `gather`).

## 3. Presupuesto Glass-to-Glass <200ms con World-s 2Hz

| Etapa | Fast 10Hz `yolo11n W30` | Slow 5Hz `pose+depth` | Slow 2Hz `World-s PromptList 20` | Total glass `worst` |
|-------|------------------------|-----------------------|----------------------------------|---------------------|
| **YOLO 640 intra2** | 49.8 `110:15` | — | — | 54.1 `110:15` + 3ms letterbox+blob `110:54` + 2ms NMS `yolo.py:171` + <1ms HSV LRU + 10ms JPEG/base64 `ws.py:118` + 25ms WS RTT `CONTEXT.md:104` → **105ms ✅** `r2:26` |
| **World-s 640 intra2** | — | — | 57-68 `r2:138` + 5ms prompt encode `r2:138` (amortizado cacheado) + 3ms preprocess +2ms NMS | **135ms ✅** `r2:27` desacoplado `LeakyQueue slow 2Hz` no bloquea fast |
| **Pose+Depth 5Hz** | — | pose ~15ms `yolo11n-pose` + depth 42ms `MiDaS` `110:73` en `gather` paralelo 42ms dominante | — | piggyback no suma a fast, slow `~60ms` `ws.py:825` |
| **480 intra2** (si se activa `YOLO <30ms` `110:17`) | 28.3 +3.04 preprocess +2ms NMS | 42ms | 35-42 est. | fast 75-90ms, slow 85-100ms, margen VLM `~300ms p50` `CONTEXT.md:114` `Groq->HF->Gemini` async detached |

**Gating:** `frame_tick %2==0` para `world 2Hz` vs `%2` pose/depth 5Hz → `ws.py:742 VLM 1Hz` ya usa `frame_tick %30==0`. Recomendar gating explícito `slow_queue` cada `250ms` (`%5` con 10Hz) y `world` cada `500ms` (`%10`) para aislar.

## 4. IMGSZ 640→480 tradeoff con World-s

- Anchors `8400->4725 -43%` `110:70`, `W30` small `cell phone mouse remote` `area 0.04-0.08` a 480 sigue `>0.03` `config.py:6` pero pierde -33% área px `110:71` `6912 vs 12288`.
- Recomendación: mantener `IMGSZ=640` para World-s 2Hz (zero-shot LVIS AP 18.5 S 640 `r2:152` entrenado 640, bajar a 480 degrada CLIP grounding + tabla `110:73` `small <3%`); usar `480` solo si `yolo11n` necesita `<30ms` y medir `r2:311` world-s smoke `p50<80` vs `p50 57-68` ya <80 sin bajar.
- No `320` para World-s: `-75% anchors` `110:19` `2100` pierde frases `red cup` small.

## 5. Recomendación tuning para 008 Destination

1. **Mantener `intra2 inter1 SEQUENTIAL ALL` unificado** `yolo.py:302` `yolo_world.py:40` `pose.py:228` `depth.py:150` + `OMP_NUM_THREADS=2` `AGENTS.md` — no `intra4`.
2. **Cablear `config.py:29` `ONNX_INTRA_OP` a `YoloDetector(intra=...)`** deuda `110:88` en 049.
3. **Registrar `record_yolo`/`record_glass` puro** `ws.py:739` + `record_world` separado `metrics.py:125` para `yolo_infer_p50_ms` vs `world_infer_p50_ms`.
4. **Gating `world 2Hz`** `frame_tick %10==0` en `slow_processor` con `txt_feats` caché 20 estática (no re-encode `r2:284` 8-15ms), `extract_prompts_from_transcript` `yolo_world.py:95` debounce 500ms cooldown 2s `r2:284`.
5. **Warmup** `yolo.warmup(10)` + `world.warmup(10)` `app.py lifespan` `yolo.py:318` (dummy `1x3x640x640` + dummy `txt_feats 8x512` `r2:311`).
6. **Profiling 60s** `GET /metrics` `yolo_infer_p50_ms / glass_to_glass_p50_ms / dropped_frames_total` con carga `640x480@10Hz` 60s `112` antes de cerrar 048/049. Assert `world p50<80` `r2:311` + `glass fast <120`.

## 6. Repro

```bash
uv run python -c "import onnxruntime as ort; print(ort.__version__)" # 1.29.0
# bench IMGSZ intra2 vs 4: ver 110:39-44 script letterbox sess.run n=20 p50/p95
uv run ruff check docs/agents/research/046-contencion-10c.md # markdown no lint
# metrics: curl http://localhost:8000/metrics | grep yolo_infer
```

## 7. Fuentes

- Código local: `plataforma/webcam/backend/inference/yolo.py:23,298-303,351`, `yolo_world.py:36-44,95`, `inference/pose.py:228`, `inference/depth.py:150`, `ws.py:584,636,637,669,739,825,845`, `config.py:19,28-30,32`, `metrics.py:45-128`, `app.py:48`, `CONTEXT.md:134,140`
- Bench `110:15` `640 49.8 p95 54.6 glass 54.1` `480 28.3 p95 30.1 glass 30.8` `320 13.2` `intra4 -5%` `ORT_DISABLE 62.9`
- `r2:137-138` `W30 10.4MB 37-56ms glass 105ms` `World-s 48.8MB 57-68ms glass 135ms`
- `112-profiling-60s.md` `dropped_frames_total` `LeakyQueue N=1` `WS_BUFFERED_LIMIT 64KB` `ws-client.js:88`
- Host `Intel Family 6 Model 154 12t` = `i7-1255U` `jarvis` verificado `is_stub True` `yolo_is_stub False`

> Research notes para linkear en `008-map-yolo-world-s-open-vocab` Ticket 046 — no cierra ticket, rama `research/046-contencion-10c`. Ver `045` para validez ONNX, `110` para IMGSZ, `112` para profiling.
