# 05 — Inferencia en proceso dedicado (SharedMemory)

**What to build:** YOLO corre en proceso hijo vía `multiprocessing` + `SharedMemory` para `img_view` zero-copy, liberando el GIL del loop principal.

**Blocked by:** 02 — Elimina YOLO redundante, 03 — Gating 5Hz.

**Status:** ready-for-agent

- [ ] Nuevo `InferenceProcess` que expone `predict(img_shm)` y `ws.py:receiver` envía solo handle `shm.name`
- [ ] Main loop no bloquea en `asyncio.to_thread(yolo)`; `dropped_frames_total` ≈0 con `POSE_ENABLED` y `DEPTH_ENABLED` activos
- [ ] Una sola sesión ONNX en hijo (`onnxruntime` intra_op=2) — memoria deja de duplicarse por fork `--reload`
- [ ] `uv run pytest plataforma/webcam -q` headless sigue verde (stub si proceso no disponible)
