# 02 — Elimina YOLO redundante y reusa boxes_payload

**What to build:** El pipeline lento no vuelve a ejecutar `yolo.predict()`; reusa el `boxes_payload` ya filtrado del pipeline rápido, bajando `inference_time_ms` de ~1242ms a <600ms y frenando `dropped_frames_total`.

**Blocked by:** 01 — FSM cableada al WebSocket (estado vivo).

**Status:** ready-for-agent

- [ ] `ws.py:slow_processor` no llama `yolo.predict()`; recibe `boxes_payload` vía `payload_slow["boxes_payload"]` inyectado por `fast_processor`
- [ ] `run_inference` sigue single-source de filtros whitelist/conf/area `ws.py:_passes_whitelist`
- [ ] `GET /metrics` muestra `inference_time_ms <700` y `dropped_frames_total` no crece a 15k en 2 min con cámara activa
- [ ] `uv run pytest plataforma/webcam -q` y `ruff` verdes
