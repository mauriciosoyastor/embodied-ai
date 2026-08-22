# Ticket 002 — Research: Detector facial + embeddings para enrollment

> Label: `wayfinder:research` · Parent: `000-map-voz-camara-registro.md` · Estado: cerrado · Resolución: 2026-08-21

## Resolución

**Respondido por subagente research (branch `research/face-embedding`):**

- MediaPipe Tasks solo da landmarks (no embedding identidad 128-d), `face-api.js` 13 MB bundle y 93-97% LFW, `onnxruntime` ArcFace `mobilefacenet` 128-d 4-8 MB, 30-45 ms, 99.83% LFW, reusa `onnxruntime==1.29` y `CPUExecutionProvider` sin colisión TFLite.
- Compatibilidad: pin `numpy==1.26.*` + `opencv 4.10.*` para `onnxruntime 1.29`; TFLite hand y ONNX face coexisten secuencial en `ws.py:172` (`VIDEO` mode).
- **Decisión:** Usar `onnxruntime` ArcFace `mobilefacenet` 128-d server-side, solo si YOLO `person` >80px, embedding normalizado, threshold coseno 0.40-0.55, promediar 3-5 muestras enrollment. Detalle en mapa.

> Estado previo: abierto · Frontera

## Question

¿MediaPipe Face Detection/Tasks vs `face-api.js` vs `onnxruntime` face para extraer embedding 128-d desde recorte YOLO `person`?

Evaluar:
- Bundle size y licencia (MediaPipe Tasks ya usado para `hand_landmarker.task` — ¿comparte TFLite delegate?)
- Compatibilidad `numpy<2` y `opencv-contrib-python` ya en `plataforma/webcam/backend`
- Si puede correr junto a `hand_landmarker.task` sin colisión de `inference_feedback_manager.cc` (ya vimos warnings `feedback tensors` en `gesture.py`)
- Precisión vs latencia en CPU (meta Glass-to-Glass <200ms) y si `leaky queue N=1` aplica también a face
- Formato embedding y distancia coseno threshold para re-identificación

Resolver con research subagent — branch `research/face-embedding`.
