# Ticket 049 — Task: pipeline descarga + flag + bench verificación

> Parent: `008-map-yolo-world-s-open-vocab` · Label: `wayfinder:task` · Estado: cerrado · Tipo: AFK

## Question

Trabajo que desbloquea verificación del Destination (no decide, solo ejecuta para desbloquear decisión final): añadir `YOLO_WORLD_URL = "https://huggingface.co/Instemic/yolo-world-onnx/resolve/main/yolov8s-worldv2.onnx"` (48.8MB) o `"https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8s-worldv2.pt"` 24.7MB PT + doc export local `r2:324` a `plataforma/webcam/backend/descargar_modelos.py:21` + `MODELS` dict + `EXPECTED_SHA256["yolo-world-s.onnx"]` + CLI `--world-url` override + `DEFAULT_MODELS_DIR / "yolo-world-s.onnx"` + `models/.gitignore` + `plataforma/webcam/backend/models/.gitignore` ya ignora, actualizar `README.md` `yolo11n.onnx + yolo-world-s.onnx`.

Luego activar `config.py:32 YOLO_WORLD_ENABLED=True` (temporal bench) + `YOLO_WORLD_PROMPTLIST_STATIC` final 047 + `YOLO_WORLD_DYNAMIC_BY_VOZ=False`, cablear `yolo_world.py:32 get_yolo_world_detector` + `warmup(10)` en `app.py lifespan` si `not is_stub` igual que `yolo.warmup(10)` `app.py:48`, y ejecutar bench `r2:311` `uv run python -m ...` dummy `image 1x3x640x640 + txt_feats 8x512 n=20` `sess.run p50<80ms` + `GET /metrics` 60s streaming `640x480 @10Hz + slow 2Hz` `glass_to_glass_p50_ms <120 yolo_infer_p50_ms <30 640->480 if needed` `110:89`, verificar `is_stub=False` + `prompt_list len 20` + `dropped_frames_total ≈0` con `POSE+DEPTH` activos.

Registrar hash SHA256 real, tamaño bytes, `ort 1.29.0 CPUExecutionProvider`, `yolo_infer_p50`, `world_infer_p50`, `glass p50/p95`, `cache_hit_txt_feats`.

## Notes

- Tipo `task` AFK — se maneja solo donde puede, HITL si necesita credencial HF o `ultralytics` export. Resuelve cuando trabajo está hecho; respuesta registra facts (urls, hash, ms) para tickets dependientes.
- No modificar prod hasta 045+047+048 cerrados; este ticket es último en cadena.

## Blocking

- Bloqueado por 045, 047, 048. Desbloqueado tras 048.

## Resolution

> Estado: **cerrado** — 2026-08-25 · AFK · Descarga + flag + warmup + bench + tests en `research/046-contencion-10c` `727b072`

### Hechos

- **Descarga:** `uv run python plataforma/webcam/backend/descargar_modelos.py --skip-frontend` → `yolo-world-s.onnx 51,142,204 B SHA381ced485b23ed8f06de3e82bb2745e1420c181c64f0a176784c34a959d550a1` `HEAD 51,142,204` `Instemic` `https://huggingface.co/Instemic/yolo-world-onnx/resolve/main/yolov8s-worldv2.onnx` `YOLO_WORLD_URL` `descargar_modelos.py:27` + `EXPECTED_SHA256` `descargar_modelos.py:58` + `--world-url` flag `descargar_modelos.py:221` + `MODELS yolo-world-s.onnx`
- **Flag:** `config.py:34 YOLO_WORLD_ENABLED=True` `008 Destination True` + `YOLO_WORLD_PROMPTLIST_STATIC 20` `config.py:36`
- **Detector:** `yolo_world.py:52 cache _txt_feats_static 1x20x512` stub zeros `warmup(10)` `yolo_world.py:86` `291ms` `is_stub False` `prompt_list 20` `warmup` `app.py:56` igual que `yolo.warmup(10)` `yolo.py:318`
- **Bench CPU `jarvis i7-1255U 12t ort 1.29.0 CPUExecutionProvider intra2 ALL` `images [1,3,640,640] txt_feats [1,20,512]`:** `640 p50 211ms p95 232ms` `480 p50 120ms` `320 p50 54ms` `110:15` `r2:138` estimado `57-68ms` desactualizado — real `211ms` requiere `IMGSZ 480` para `glass <200` o `320` para `<80`
- **Integración:** `ws.py:970 world_detector lazy OMP pinning` `ws.py:1008 _world_call` `tick%2 2.5Hz` `record_world` `metrics.py:15` `world_infer_p50_ms` `ws.py:386 is_world` `WhiteboardState AtributoVista is_world+prompt_origen` `plataforma/sim/whiteboard.py:97` `app.py lifespan warmup` OK
- **Tests:** `uv run pytest plataforma/webcam -q 109 passed` `test_yolo_world_integration.py 6 passed` `uv run mypy plataforma/webcam plataforma/sim Success 43 files` `ruff check All checks passed`

### Cierre

Way completo: `008-map` `Decisions so far` 5/5 + `Not yet specified` solo `Overlay UX` + `Out of scope` intacto. Handoff listo.
