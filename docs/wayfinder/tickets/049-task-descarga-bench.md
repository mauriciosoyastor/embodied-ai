# Ticket 049 — Task: pipeline descarga + flag + bench verificación

> Parent: `008-map-yolo-world-s-open-vocab` · Label: `wayfinder:task` · Estado: abierto · Tipo: AFK (tras HITL 048)

## Question

Trabajo que desbloquea verificación del Destination (no decide, solo ejecuta para desbloquear decisión final): añadir `YOLO_WORLD_URL = "https://huggingface.co/Instemic/yolo-world-onnx/resolve/main/yolov8s-worldv2.onnx"` (48.8MB) o `"https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8s-worldv2.pt"` 24.7MB PT + doc export local `r2:324` a `plataforma/webcam/backend/descargar_modelos.py:21` + `MODELS` dict + `EXPECTED_SHA256["yolo-world-s.onnx"]` + CLI `--world-url` override + `DEFAULT_MODELS_DIR / "yolo-world-s.onnx"` + `models/.gitignore` + `plataforma/webcam/backend/models/.gitignore` ya ignora, actualizar `README.md` `yolo11n.onnx + yolo-world-s.onnx`.

Luego activar `config.py:32 YOLO_WORLD_ENABLED=True` (temporal bench) + `YOLO_WORLD_PROMPTLIST_STATIC` final 047 + `YOLO_WORLD_DYNAMIC_BY_VOZ=False`, cablear `yolo_world.py:32 get_yolo_world_detector` + `warmup(10)` en `app.py lifespan` si `not is_stub` igual que `yolo.warmup(10)` `app.py:48`, y ejecutar bench `r2:311` `uv run python -m ...` dummy `image 1x3x640x640 + txt_feats 8x512 n=20` `sess.run p50<80ms` + `GET /metrics` 60s streaming `640x480 @10Hz + slow 2Hz` `glass_to_glass_p50_ms <120 yolo_infer_p50_ms <30 640->480 if needed` `110:89`, verificar `is_stub=False` + `prompt_list len 20` + `dropped_frames_total ≈0` con `POSE+DEPTH` activos.

Registrar hash SHA256 real, tamaño bytes, `ort 1.29.0 CPUExecutionProvider`, `yolo_infer_p50`, `world_infer_p50`, `glass p50/p95`, `cache_hit_txt_feats`.

## Notes

- Tipo `task` AFK — se maneja solo donde puede, HITL si necesita credencial HF o `ultralytics` export. Resuelve cuando trabajo está hecho; respuesta registra facts (urls, hash, ms) para tickets dependientes.
- No modificar prod hasta 045+047+048 cerrados; este ticket es último en cadena.

## Blocking

- Bloqueado por 045, 047, 048. No frontera.

## Resolution

> Estado: **abierto** — bloqueado. Claim tras desbloqueo, luego ejecutar `uv run python plataforma/webcam/backend/descargar_modelos.py` + bench.
