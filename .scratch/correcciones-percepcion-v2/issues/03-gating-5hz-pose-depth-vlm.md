# 03 — Gating 5Hz para pose/depth + VLM

**What to build:** Pose y depth corren subsampleados (cada 2º frame o solo si `fast_queue` vacía), devolviendo FPS 1→8-10 y CPU 60%→25% sin perder gestos a 10Hz.

**Blocked by:** 02 — Elimina YOLO redundante y reusa boxes_payload.

**Status:** ready-for-agent

- [ ] `ws.py:slow_processor` gate `frame_tick % 2 == 0` o `if fast_queue.qsize()>0: skip` antes de `asyncio.to_thread(pose/depth)`
- [ ] `VLM_INTERVAL=30` respeta 1Hz y no bloquea `fast_processor`; `scene_caption` sigue llegando sin jitter
- [ ] `GET /metrics` → `glass_to_glass_p50_ms <200ms`, `fps 8-10`, `CPU <30%` con `POSE_ENABLED/DEPTH_ENABLED=True`
- [ ] Overlay sigue pintando esqueleto `drawPoses` y badge `z` `<5ms` aunque se salte frames
