# Ticket 045 — Research: Instemic yolo-world-s ONNX 48.8MB validez y bench p50<80ms en i7-1255U

> Parent: `008-map-yolo-world-s-open-vocab` · Label: `wayfinder:research` · Estado: abierto · Tipo: AFK · Rama: `research/045-world-onnx-validez` (no prod code modificado)

## Question

¿Es válido el `yolov8s-worldv2.onnx 48.8MB Instemic opset19 txt_feats dinámico` + `47.8MB slim` vs `51.1MB ODLabel LFS` para `CPUExecutionProvider` `ort 1.29.0` en `jarvis i7-1255U 10c/12t` (`yolo_is_stub=False` verificado), y qué `yolo_infer_p50_ms` + `glass_to_glass_p50_ms` + memoria runtime da con `letterbox 640` + `NMS IoU 0.7` + `SessionOptions ORT_ENABLE_ALL intra2 inter1 sequential` igual que `yolo.py:299-303` y `yolo_world.py:40`?

Evaluar: `Instemic/yolo-world-onnx yolov8s-worldv2.onnx 48.8MB 12.7M` `huggingface.co/Instemic` + `ODLabel/assets LFS 51,165,315 B oid ede165` `r2:158` + `ultralytics/assets v8.2.0 yolov8s-worldv2.pt 24.7MB` exportabilidad `worldv2 ✅` `docs.ultralytics.com/models/yolo-world` vs `v1 ❌`; `einsum` `use_einsum=False` `r2:164` Opset11 roto; input `image 1x3x640x640 + txt_feats 8x512 (N clases dinámico)` `Instemic torch.split` vs `text encoder` fuse `r2:173`; `huggingface.co/Instemic` slim `onnxslim` 47.8MB trade-off.

Resolver vía subagente `research`: fetch `AILab-CVC/YOLO-World`, `docs.ultralytics.com/models/yolo-world`, `assets/releases/tag/v8.2.0`, `huggingface.co/Instemic`, `Qualcomm AIHub 12.7M 48.2MB`, bench `ort.InferenceSession` dummy `1x3x640x640 + txt_feats 8x512` `n=20` con `providers=["CPUExecutionProvider"]` en `jarvis` (o documentar si headless sin peso) y medir `sess.run p50/p95`, `mem RSS`, `graph_optimization ORT_ENABLE_ALL` vs `BASIC` `HackerNoon R1`; producir tabla Peso ONNX / Mem / infer p50 / glass / exportable + recomendación fuente para `descargar_modelos.py:21`.

## Notes

- Consultar skill `research` (AFK). No modificar `plataforma/webcam/backend/yolo_world.py` ni `config.py`. Capturar hallazgos en rama `research/045-world-onnx-validez` con pointer al ticket.
- Usar medidas locales `yolo11n.onnx 10.4MB 37-56ms` `r1:2` + `r2:138` como baseline; World-s estimé `57-68ms +5ms prompt encode` `r2:138` a validar.

## Blocking

- Bloquea a 048, 049. Desbloqueado (frontera).

## Resolution

> Estado: **abierto** — asignar a dev antes de trabajar (claim). No resolver más de uno por sesión salvo research paralelos.
