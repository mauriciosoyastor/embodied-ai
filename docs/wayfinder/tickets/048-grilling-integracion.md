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

> Estado: **abierto** — bloqueado. No claim hasta desbloqueo.
