# 06 — Export ONNX FP16 / TensorRT y validación Glass-to-Glass <200ms

**What to build:** Modelo YOLO exportado a FP16/TRT reduce `yolo_infer_p50_ms` a <30ms y garantiza meta Glass-to-Glass <200ms.

**Blocked by:** 05 — Inferencia en proceso dedicado (SharedMemory).

**Status:** ready-for-agent

- [ ] `yolo11n.onnx` FP16 (o TRT si GPU) con `ort.SessionOptions graph_optimization_level=ORT_ENABLE_ALL` `pose.py:225` y `providers=["CUDAExecutionProvider" | "CPUExecutionProvider"]`
- [ ] `GET /metrics` → `yolo_infer_p50_ms <30` y `glass_to_glass_p50_ms <120` medido en 60s de streaming 640x480 @10Hz
- [ ] Script `descargar_modelos.py` soporta `--fp16` y verifica hash; fallback a FP32 si no hay GPU
- [ ] Demo `http://localhost:5173` fluido 10 FPS con `person+pose+depth` visibles y `inference_time_ms` documentado en README
