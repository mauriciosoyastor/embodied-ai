# Ticket 048 — Grilling: integración ws.py slow_queue 2Hz + Whiteboard extension

> Parent: `008-map-yolo-world-s-open-vocab` · Label: `wayfinder:grilling` · Estado: abierto · Tipo: HITL

## Question

Con datos 045 (validez ONNX 48.8MB `p50<80ms` `210MB` `r2:138`) + 046 (contención `intra2 vs 4` `glass <200ms` `dropped_frames`) + 047 (PromptList 20 final + `en` CLIP):

¿Dónde vive `YoloWorldDetector` en `ws.py:584 perception_ws_handler`? ¿`slow_queue 5Hz pose+depth ws.py:637` piggyback añade `World-s 2Hz` con `asyncio.gather(to_thread(pose), to_thread(depth), to_thread(world))` vs `world_queue` separada `2Hz LeakyQueue` vs `slow_processor` filtra cada `frame_tick %5==0` world? ¿Zero-Copy `img_view` `ws.py:669` reuse `letterbox` `yolo.py:134` compartido vs re-`blob` `BGR->RGB /255 CHW`? ¿Caché `txt_feats` 20 estática precomputada `not re-encode` como se evita encode por frame `r2:284 8-15ms`? ¿`GraphOptimizationLevel.ORT_ENABLE_ALL` `yolo_world.py:38` + `warmup(10)` `app.py lifespan` `yolo.py:318` unificado?

¿`WhiteboardState.percepcion_vista.atributos: list[AtributoVista]` `CONTEXT.md:134` extiende con `is_world?: bool` + `prompt_origen?: string` vs `WhiteboardState.world_detections?: list[AtributoVista]` paralelo vs `PercepcionVista` nuevo campo `world_atributos` con TTL `200ms` vs `3000ms color_vlm`? ¿`ws.py:204 _passes_whitelist` reuse `box_thr 0.35 text_thr 0.25` `r2:128` vs nuevo `_passes_world`? ¿`ABORTED overlay-only` `CONTEXT.md:141` muta `WhiteboardState` o solo `overlay.js`? ¿`ByteTrack tracker.py:38 max_age30 iou0.5` + `LRUCache 64 TTL 2s` reuse para world boxes? ¿`metrics.py:38 GET /metrics` nuevo `world_infer_p50_ms` + `world_cache_hit` vs reuse `yolo_infer_p50_ms`?

HITL `grilling` + `domain-modeling` + `prototype` (diagrama `fast 10Hz YOLO11n W30 -> atributos` vs `slow 2Hz World-s PromptList 20 -> atributos_world` si necesita fidelidad).

## Notes

- Llamar `grilling` + `domain-modeling`; `prototype` si `how should it look` necesita diagrama throwaway. No entregar destino, solo decisión integración.
- Referenciar `ws.py:636 fast_queue`, `ws.py:637 slow_queue`, `yolo_world.py:32 _world_singleton`, `yolo_world.py:51 set_classes`, `config.py:32 YOLO_WORLD_ENABLED` + `config.py:34 PROMPTLIST`.

## Blocking

- Bloqueado por 045, 046, 047. No frontera hasta que cierren.

## Resolution

> Estado: **cerrado** — 2026-08-25 · HITL grilling + domain-modeling · Resuelto en sesión con usuario (Q1-Q5 aprobados)

### Decisión

- **Q1 Topología slow 2Hz — Opción A piggyback:** reutilizar `slow_queue 5Hz` `ws.py:637` con gating `tick %10==0` → `world 2Hz` via `await asyncio.gather(to_thread(pose), to_thread(depth), to_thread(world))` 3-way si tick 10, sin nueva `world_queue` ni worker `asyncio` extra; evita thrashing `12 hilos` `046`; `~135ms` en 1 de cada 5 ticks slow no degrada `fast_queue 10Hz` `ws.py:636`.
- **Q2 Whiteboard — Opción A extender AtributoVista:** `AtributoVista` `CONTEXT.md:134` añade `is_world: bool = False` + `prompt_origen: Optional[str] = None` — single-writer `WhiteboardState` `update_percepcion(atributos=...)` respeta `ABORTED` latch, evita duplicar `TTL 200ms`/`ttl_expirations`/`OTel`, `overlay.js` badge color distinto si `is_world`, `DecisionAgentica` consume mismo `list[AtributoVista]`.
- **Q3 Caché txt_feats + Warmup:** `_txt_feats_static: np.ndarray 20x512` en `YoloWorldDetector` `yolo_world.py:31` precomputado `clip_encode(PROMPTLIST 20)` congelado al boot si `is_stub False` (no re-encode `8-15ms` `r2:284` por frame); `app.py lifespan` ejecuta `world.warmup(10)` dummy `1x3x640x640 + txt_feats 8x512` igual que `yolo.warmup(10)` `yolo.py:318` (`ORT_ENABLE_ALL` `yolo_world.py:38`).
- **Q4 Filtros y Tracker:** nuevo `_passes_world(box)` con `box_thr=0.35 text_thr=0.25` `r2:128` independiente de `_passes_whitelist 0.5`; reutilizar `ByteTrack max_age30 iou0.5 tracker.py:38` + `LRUCache 64 IoU>0.85 TTL2s` con clave compuesta `is_world` evita colisiones `W30` vs `world` IDs.
- **Q5 Métricas y ABORTED + Pinning:** métrica dedicada `world_infer_p50_ms` `metrics.py:38` via `record_world(ms)` separado de `yolo_infer_p50_ms` `ws.py:739` para `Prometheus/OTel` SLA; `ABORTED overlay-only` no muta `WhiteboardState` (solo `overlay.js`); pinning `OMP_NUM_THREADS=2 intra_op=2 inter_op=1 ORT_SEQUENTIAL` unificado `yolo.py:302`/`yolo_world.py:40`/`pose.py`/`depth.py` previene contención `gather(pose,depth,world)` en edge; `Zero-Copy img_view` `np.ndarray` view sin `.copy()` `ws.py:669` minimiza bus; monitoreo `world_infer_p50` + `dropped_frames_total` `metrics.py` audita `135ms` no satura.

### Artefactos

- Mapa `008` → `Decisions so far` apunta a este ticket; fog `Thresholds / PercepcionVista / Métricas world` graduado y limpio de `Not yet specified`.
- `CONTEXT.md` ya con `PromptList` `047`; próximo `049` usará `is_world` + `_passes_world` + `world_infer_p50_ms`.
