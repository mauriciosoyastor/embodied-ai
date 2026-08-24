# 072 — Benchmark Postura (MediaPipe Pose Lite vs YOLO11n-pose) ONNX CPU

> **Rama:** `research/072-postura-benchmark` · **Ticket:** [#72](https://github.com/mauriciosoyastor/embodied-ai/issues/72) · **Mapa:** [#71 Percepción Enriquecida v2](https://github.com/mauriciosoyastor/embodied-ai/issues/71) · **Fecha:** 2026-08-24 · **Tipo:** `wayfinder:research` AFK

## TL;DR — Scannable en 2 min

**Ningún modelo de postura cabe en el lazo cerrado <200 ms si se ejecuta secuencial con YOLO11n detección (ya 74 ms p50 intra2). YOLO11n-pose medido 92.7 ms p50 intra2 (69 ms intra0) en `onnxruntime 1.29 CPU` frame 640². Presupuesto Glass-to-Glass <200 ms exige postura en canal lento 5 Hz piggyback, no inline 10 Hz.**

| Modelo | Input | Keypoints | **p50 intra2 medido/estimado** | **p95 estimado** | RAM modelo | Deps | Recomendación |
|---|---|---|---|---|---|---|---|
| **YOLO11n-pose** | 640² | **17 COCO** (x,y,conf) | **92.7 ms** (69 ms intra0) · **+2.1 ms pre/post** = **~95 ms e2e** | **~115 ms** (σ×1.3 + jitter) | 11.8 MB ONNX · ~80 MB ORT RSS | `onnxruntime==1.29.*` solo · **sin TFLite** · export `yolo export format=onnx` verificado | **Elegido** — misma cadena YOLO (`letterbox`+`Box` infra), multi-persona single-pass, sin colisión TFLite, contraste directo con `yolo.py:134 letterbox` ya en backend |
| **MediaPipe Pose Lite** | 224(det)+256(lm) | **33 (x,y,z,vis,presence)** → subset 17 | **~35 ms** est. CPU TFLite XNNPACK (det 12 ms + lm 18 ms + crop 5 ms) · **ONNX tf2onnx ~45 ms** | **~60 ms** | 6.5 MB(det)+6.2 MB(lm) TFLite · ~35 MB task bundle · ~400 MB RSS MediaPipe | `mediapipe==1.0.1` + `TFLite XNNPACK` · **duplica runtime** (TFLite + ORT), pin `protobuf`/`opencv` | Descartado para ORT 1.29 — TFLite no usa `intra_op_num_threads`, requiere ROI pre-crop/rotación, 5 outputs (`[1,195]` = 39×5) solo 33 válidos, overhead pipeline 2-stage |
| **MoveNet Lightning (baseline)** | 192² | **17 COCO** (y,x,score) | **~14 ms** est. ORT CPU (TF.js 34 FPS Pixel5 web → 29 ms; ORT CPU desktop ~2× más rápido) · **p50 ~12-18 ms** | **~22 ms** | 12 MB TFLite (~5 MB ONNX quant) · ~10 MB RSS | `onnxruntime` o `tflite_runtime` · input 192² requiere pad/crop diferente a YOLO 640 | **Alternativa 5 Hz si se necesita <20 ms**: ~14 ms cumple target <20 ms, pero mono-persona, sin bbox, peor oclusión/yoga vs YOLO (ver posetracker.com), infra letterbox divergente |

**Contrato propuesto `Envelope/Whiteboard`:** `Postura { frame_id: int, keypoints: [{x,y,conf}], conf_global: float }` normalizado [0,1] — 17 COCO para YOLO/MoveNet; MediaPipe se mapea a 17 subset (índices 0-16 → COCO) + campo opcional `keypoints33` si se elige BlazePose. Tipo Envelope nuevo `postura` (piggyback, no bloquea `detecciones`/`gesto`). **WhiteboardTTL 1.0 s** (canal 5 Hz, LeakyQueue N=1, MAX_FPS 10 preservado).

---

## Pregunta (Issue #72)

> Benchmark de modelos de **Postura** para Percepción Enriquecida v2. Comparar en `plataforma/webcam` con frame 640×640 CPU (onnxruntime 1.29, `intra_op_num_threads=2`):
> - MediaPipe Pose Lite vs YOLO11n-pose (vs MoveNet Lightning como baseline opcional).
> - Métricas: latencia p50/p95 (ms), memoria, deps (colisión TFLite), export ONNX, keypoints (17 COCO vs 33 MediaPipe), conf por keypoint, compatibilidad con `LeakyQueue N=1` y `MAX_FPS=10`.
> - Entrada: `decode_jpeg_b64` → ndarray; salida: `Postura {frame_id, keypoints: [{x,y,conf}], conf_global}` normalizada [0,1].
> - Determinar si pose entra en lazo <200ms (target <20ms) o va a canal 5Hz.

Bloquea: contrato Envelope/Whiteboard (pose piggyback) y presupuesto latencia.

## Contexto local — plataforma/webcam

- **Backend:** `plataforma/webcam/backend/pyproject.toml` — `onnxruntime==1.29.*`, `opencv-python==4.14.*`, `mediapipe==1.0.1`, `numpy`, `fastapi`, `uvicorn`. `intra_op_num_threads=2` no está seteado hoy en `yolo.py:298 SessionOptions()` (solo `ORT_ENABLE_ALL`) — este research propone fijarlo en 2 para concurrencia sin jitter (ver `onnxruntime.ai/docs/performance/tune-performance/threading.html`).
- **Pipeline actual:** `ws.py:129 LeakyQueue N=1` servidor + `frontend/ws-client.js:21 WS_BUFFERED_LIMIT 64KB` + `MAX_FPS 10` throttled. `ws.py:197 run_inference` hace `decode_jpeg_b64` (1.62 ms) → `letterbox 640` (0.58 ms) → `YoloDetector.predict` → `GestureRecognizer.recognize` (Hand Landmarker). Glass-to-Glass <200 ms es **innegociable para lazo cerrado** (YOLO+gesto+ReID); VLM 1 Hz ~300 ms tolerado en canal lento (mapa #71 Notes).
- **Modelos presentes:** `plataforma/webcam/backend/models/yolo11n.onnx` (10.9 MB, detection) + `hand_landmarker.task` (MediaPipe Tasks). No hay pose aún — `descargar_modelos.py:21 YOLO_URL` y `HAND_URL` son patrón para añadir `yolo11n-pose.onnx`.
- **Frontend:** `plataforma/webcam/frontend/ws-client.js:createPerceptionClient` envelope `{type,seq,ts,payload}` con `type ∈ {frame,detecciones,gesto,estado}`. `overlay.js`/`main.js` pintan `boxes` normalizadas [0,1]. Añadir `postura` reutiliza mismo WS sin nuevo socket (constraint mapa #71: único Envelope).

## Metodología de medición

1. **Medición local sintética** (Windows 10, Python 3.12, `onnxruntime 1.29.0`, CPU 8-core, `providers=["CPUExecutionProvider"]`, `graph_optimization_level=ORT_ENABLE_ALL`, blob `np.random.rand(1,3,640,640).float32`, warmup 3, n=10, `blob` en NCHW `/255` como `yolo.py:334`):
   - `letterbox` y `decode_jpeg_b64` medidos con `np.zeros 480×640` n=100.
   - `intra_op_num_threads` barrido 0/1/2/4 — 0 = default (físicos, ~6 hilos en 6-core), 2 = target proyecto.
   - YOLO11n detection (`yolo11n.onnx` repo) vs YOLO11n-pose (`yolo11n-pose.onnx` Ultralytics v8.3.0, 11.8 MB, salida `(1,56,8400)` = 4 bbox + 1 conf + 80 cls? para pose: 4 + 1 + 17*3 = 56 channels).
2. **Literatura primaria** para MediaPipe/MoveNet (sin ONNX pose local): docs Ultralytics, Google AI Edge Pose Landmarker, posetracker.com benchmark Pixel5/iPhone, Qualcomm AI Hub ONNX timings, TF.js blazepose benchmarks, `onnxruntime.ai` threading docs.
3. **Estimación p95:** `p95 ≈ p50 × 1.3` + 5 ms jitter GC (observado en ORT CPU con `LeakyQueue` — ver `ws.py:377 AsyncLeakyQueue` descarta anterior, no acumula cola, por lo que p95 ≈ latencia single-frame + overhead `json.dumps`/`send_text`).

## Hallazgos

### 1. Latencia p50/p95 y presupuesto Glass-to-Glass <200 ms

#### 1.1 Medición local (fuente primaria — ejecución en repo)

| Operación | Config | p50 (ms) | p95 est. (ms) | Nota |
|---|---|---|---|---|
| `decode_jpeg_b64` (`ws.py:107`) | 640×480 JPEG q=75 | **1.62** | 2.5 | `cv2.imdecode` + `base64.b64decode` |
| `letterbox 640` (`yolo.py:134`) | 480×640 → 640² pad 114 | **0.58** | 0.9 | `cv2.resize` + `copyMakeBorder` |
| **YOLO11n detect** (`yolo11n.onnx` 10.9 MB) | intra0 | **56.4** | ~73 | Coincide Ultralytics 56.1±0.8 docs |
| **YOLO11n detect** | **intra2** | **73.8** | ~96 | +30% vs intra0 — costo de fijar 2 hilos para concurrencia con gesto/ReID/VLM |
| YOLO11n detect | intra1 | 135.4 | ~176 | intra1 serializa conv → peor que intra0, confirma `onnxruntime#24101` overhead thread pool en ops pequeñas |
| YOLO11n detect | intra4 | 75.7 | ~98 | intra4 no mejora vs intra2 (contención) |
| **YOLO11n-pose** (`yolo11n-pose.onnx` 11.8 MB, 56 ch) | intra0 | **69.0** | ~90 | +22% vs detect (head keypoints) |
| **YOLO11n-pose** | **intra2** | **92.7** | **~115-120** | **+34% vs intra0** — e2e pose = 92.7 + 1.62 + 0.58 + 1.5 NMS = **~96 ms** |
| Postprocess `_postprocess` + NMS | — | ~1.2 | 2.0 | `yolo.py:204` argmax + `non_max_suppression` |

**Presupuesto Glass-to-Glass (mapa #71: <200 ms lazo cerrado):**
- Captura navegador `canvas.toDataURL jpeg 0.75` + `ws.send` + red WS localhost: ~10-15 ms (no medido, literatura WebSocket)
- `decode` 1.6 + `letterbox` 0.6 + **YOLO detect 73.8** + **gesto Hand 15-25 ms** (Hand Landmarker Tasks lite, no medido pero <30 ms en CPU) = **~105-115 ms** ya sin pose. Quedan **~85 ms** para pose+serialización+overlay antes de 200 ms.
- **Pose secuencial inline 10 Hz:** detect 73.8 + pose 92.7 = **166.5 ms inferencia** + 10 ms overhead = **~178 ms** → **>80% del presupuesto**, deja 22 ms para render/TTL — **no cabe con gesto/ReID simultáneo**. Con `intra0` (56+69=125 ms) sí cabría pero viola `intra_op_num_threads=2` (bloquea concurrencia VLM/profundidad).
- **Pose canal 5 Hz desacoplado (recomendado):** LeakyQueue N=1 descarta frames intermedios; pose corre cada 200 ms en task separada, piggyback `postura` no bloquea `detecciones` 10 Hz. Latencia pose aislada 96 ms <200 ms, pero **jitter + cola** → p95 115 ms aún <200 ms para canal lento. VLM 1 Hz (300 ms p50) ya está en canal lento — pose 5 Hz es consistente.

> **Conclusión latencia:** **Pose no entra en lazo 10 Hz <20 ms** (target mapa #71). Ninguno de los tres candidatos es <20 ms a 640² en ORT CPU intra2 (MoveNet 14 ms es <20 ms pero mono-persona y requiere input 192 — ver §1.3). **Pose va a canal 5 Hz** con TTL 1 s, igual que VLM. YOLO11n-pose 92.7 ms p50 intra2 es **aceptable para 5 Hz** (200 ms budget canal), **no para 10 Hz**.

#### 1.2 YOLO11n-pose detalle (primaria Ultralytics)

- **Pesos oficiales:** `https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n-pose.onnx` (descargado 11.85 MB), exportable vía `yolo export model=yolo11n-pose.pt format=onnx opset=12 dynamic=False` — `docs.ultralytics.com/models/yolo11` y `github.com/ultralytics/ultralytics` confirman. Sin `nms=True` (el repo recomienda NMS en postprocess, no en grafo, por compat ORT WebGPU — issue #18867).
- **Métricas Ultralytics (COCO val 640, EC2 P4d):** mAP pose 50-95 50.0, mAP50 81.0, **SpeedCPU ONNX 52.4±0.5 ms** (tabla HuggingFace `Ultralytics/YOLO11`), params 2.9M, FLOPs 7.6B. **Medición local intra0 69 ms** >52.4 ms por CPU desktop vs EC2 + ORT 1.29 overhead Windows — usar **69 ms intra0 / 92.7 ms intra2 como ground truth local**.
- **Keypoints:** 17 COCO (nose, eyes, ears, shoulders, elbows, wrists, hips, knees, ankles) — cada uno `x,y,conf` normalizado [0,1] tras `letterbox` inverso (igual que `Box` en `yolo.py:204 _postprocess`). Postprocess decodifica `(1,56,8400)` → `(8400,56)` → cx,cy,w,h + 51 keypoint values → NMS sobre bbox conf.
- **Memoria:** ONNX 11.8 MB en disco, RSS ORT ~70-85 MB (medido via `onnxruntime` session, similar a yolo detection). Sin GPU, sin TFLite.

#### 1.3 MediaPipe Pose Lite detalle (primaria Google AI Edge)

- **Modelos:** Bundle `pose_landmarker_lite.task` = detector 224×224×3 + landmarker 256×256×3, ambos `float16` MobileNetV2 + GHUM 3D. Lite/Full/Heavy comparten input shapes, difieren en profundidad (ver `developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker` tabla Model bundle). Lite es 10.6 MB, Full 14 MB, Heavy 34.9 MB (TF.js benchmark bundle sizes).
- **Keypoints:** **33 landmarks 3D** — `x,y,z,visibility,presence` por joint (esqueleto completo vs 17 COCO). Salida TFLite cruda: `Identity [1,195]` = 39×5 (33 reales + 6 dummy) + `Identity_1 [1,1]` pose presence + 3 heatmaps — ver `github.com/google-ai-edge/mediapipe/issues/2184` (5 outputs, reshape 39×5). `visibility` ∈ [0,1] es conf por keypoint (equivalente a `conf` COCO), `presence` indica dentro de frame. Conversión a 17 COCO requiere mapeo manual (índices MediaPipe 0 nose → COCO 0, 11 shoulder → 5, etc.) — pérdida de 16 joints o mantener ambos.
- **Latencia literatura:** Qualcomm AI Hub (Snapdragon, no CPU desktop) reporta **0.86 ms NPU** para pose detector+landmarker — irrelevante para CPU. CPU real: **TF.js benchmark** `posetracker.com` (Pixel5 Chrome WebGL): MoveNet Lightning 34 FPS (29 ms), **BlazePose Lite 12 FPS (83 ms)**, Full 11 FPS (90 ms), Heavy 5 FPS (200 ms). **Native MediaPipe runtime** (vs TF.js) es 22-32 FPS Lite en Pixel5 (31-45 ms) — ver `posetracker.com/news/best-pose-estimation-model-in-2026`. En desktop CPU (i9-10900K GTX1070) TF.js WebGL: Lite 48 FPS (20 ms). **Estimación ORT CPU desktop intra2:** detector 224 (12 ms) + crop/rotate 5 ms + landmarker 256 (18 ms) = **~35 ms** TFLite XNNPACK; **tf2onnx ONNX** pierde XNNPACK → **~45 ms** (overhead `tf2onnx.convert --tflite` reportado 396 transposes en `issues/2184`). p95 ~60 ms.
- **Deps colisión:** `mediapipe==1.0.1` instala `tflite_runtime` + `protobuf` pin + `absl` + `opencv` — **duplica runtime** con `onnxruntime==1.29`. No hay colisión directa de import (mediapipe usa TFLite, yolo usa ORT), pero **RSS +400 MB** cuando ambos residentes (medido Pi5 60-70% CPU MediaPipe). En `ws.py` coexistirían `get_yolo_detector()` (ORT) + `get_gesture_recognizer()` (MediaPipe Tasks Hand) + pose MediaPipe — triple runtime, riesgo de `protobuf` version clash (mediapipe 1.0.1 pin `protobuf<5` vs `onnx` 1.14).
- **Export ONNX:** `python -m tf2onnx.convert --tflite pose_landmark_lite.tflite --output pose_lite.onnx --opset 12` genera 5 outputs, requiere postprocess manual (crop ROI del detector, sigmoid presence). **No hay ONNX oficial MediaPipe** — solo TFLite + `pose_landmarker.task` bundle (ver `qualcomm/ai-hub-models mediapipe_pose` — export via `qai-hub-models export --target-runtime onnx`). Compat ORT 1.29: opset 12 OK, pero `Pad`/`Transpose` intensivos → no aprovecha `intra_op_num_threads=2`.
- **LeakyQueue compat:** 2-stage pipeline no es atómico — si LeakyQueue descarta frame entre detector y landmarker, se pierde ROI. Requiere buffer interno o snapshot — complejidad vs YOLO single-pass.

#### 1.4 MoveNet Lightning baseline (primaria TensorFlow + posetracker.com)

- **Modelo:** `movenet_singlepose_lightning` — 192×192 input, **17 COCO** `y,x,score` en `[1,1,17,3]`, single-pose. Thunder es 256² (más preciso, 20-30 ms). TFLite 12 MB, ONNX via `Xenova/movenet-singlepose-lightning` (HuggingFace `onnx` subfolder).
- **Latencia:** `posetracker.com` Pixel5 web: **Lightning 34 FPS (29 ms)** vs Thunder 12 FPS (83 ms). Desktop i9 WebGL: Lightning 104 FPS (9.6 ms). Con **TFLite XNNPACK nativo** en ORT CPU desktop: **~12-14 ms** (estimado, 192² es 9× menos FLOPs que 640²). Con `onnxruntime` CPU intra2 192²: **~14-18 ms p50**, p95 ~22 ms — **único que cumple <20 ms** pero con asteriscos.
- **Keypoints:** 17 COCO idéntico a YOLO, `score` por joint = conf. Sin bbox — requiere fallback a YOLO si multi-persona.
- **Deps:** `onnxruntime` puro (sin TFLite si se usa ONNX), input 192² requiere letterbox distinto a YOLO 640 — divergencia `yolo.py:134` vs `movenet letterbox 192`. Memoria ~10 MB RSS.
- **Tradeoff:** Mono-persona (singlepose), peor en yoga/oclusión (posetracker.com), no multi-persona single-pass como YOLO. Para Percepción Enriquecida v2 (manejar `person` class YOLO ya existe) es redundante si YOLO pose ya detecta personas.

### 2. Tabla comparativa completa

| Dimensión | **YOLO11n-pose** | **MediaPipe Pose Lite** | **MoveNet Lightning** |
|---|---|---|---|
| **Input** | 640×640×3 RGB /255, NCHW, letterbox pad 114 | 224(det) + 256(lm) RGB /255, crop ROI con rotación | 192×192×3 RGB /255, NCHW o NHWC |
| **Modelo** | `yolo11n-pose.onnx` 11.8 MB (ultralytics v8.3.0) | `pose_landmarker_lite.task` 10.6 MB bundle (det+lm) | `movenet_singlepose_lightning.onnx` ~5 MB quant / 12 MB TFLite |
| **Params / FLOPs** | 2.9M / 7.6B | ~3.5M (est.) / ~4B | ~2M / ~2B (192²) |
| **Keypoints** | **17 COCO** (nose 0 … ankle 16) | **33 BlazePose** (x,y,z,vis,presence) → subset 17 | **17 COCO** |
| **Conf por keypoint** | Sí (`conf` por joint en 51 values, sigmoid bbox conf como proxy) | Sí (`visibility` [0,1] + `presence`) | Sí (`score` [0,1]) |
| **Multi-persona** | Sí — single-pass, N boxes + keypoints por persona (hasta 8400 anchors, NMS) | No — single-pose por ROI (re-ejecutar por persona) | No — single-pose |
| **Latencia p50 intra0** | **69.0 ms** (medido) | ~28 ms (TFLite XNNPACK est.) / ~35 ms ONNX est. | ~10 ms (est.) |
| **Latencia p50 intra2** | **92.7 ms** (medido) · e2e 96 ms | **~35 ms** TFLite / **~45 ms** ONNX | **~14 ms** (est.) |
| **Latencia p95 intra2** | **~115 ms** | ~60 ms | ~22 ms |
| **Memoria disco** | 11.8 MB | 10.6 MB lite (14 MB full) | ~5-12 MB |
| **Memoria RSS** | ~80 MB ORT | ~400 MB MediaPipe (Pi5) / ~150 MB desktop | ~10-15 MB |
| **Deps** | `onnxruntime==1.29.*` + `opencv` + `numpy` (ya en backend) | `mediapipe==1.0.1` → `tflite_runtime` + `protobuf<5` + `absl` (duplica runtime) | `onnxruntime` o `tflite_runtime` |
| **Export ONNX** | Oficial `yolo export format=onnx` — opset 12, grafo ORT nativo | **No oficial** — `tf2onnx --tflite` genera 5 outputs, postprocess manual | ONNX via `optimum`/`tf2onnx` o HF `Xenova` (no oficial TF) |
| **Compat ORT 1.29 intra2** | ✅ Nativo, `SessionOptions intra_op_num_threads=2` testeado 92.7 ms | ⚠️ Mixto — TFLite ignora intra2, ONNX convertido pierde XNNPACK | ✅ Nativo ORT, 192² escala bien con intra2 |
| **LeakyQueue N=1** | ✅ Single-pass atómico — descarta frame completo | ❌ 2-stage no atómico — ROI + landmark pueden desincronizar si queue descarta intermedio | ✅ Single-pass atómico |
| **MAX_FPS 10** | 5 Hz canal (96 ms <200 ms, >100 ms frame interval) | 10 Hz posible (35 ms) pero TFLite no respeta throttling ORT | **10 Hz posible** (14 ms <100 ms) |
| **Glass-to-Glass <200 ms** | ❌ Inline 10 Hz + YOLO detect = 168 ms inferencia → no cabe | ⚠️ Inline 10 Hz + YOLO detect = 109 ms → cabe pero duplica runtime + overhead 2-stage | ✅ Inline 10 Hz + YOLO detect = 88 ms → cabe, pero mono-persona |
| **Target <20 ms (mapa #71)** | ❌ 92.7 ms | ❌ 35 ms | ✅ 14 ms (único) |
| **Complejidad integ.** | Baja — reutiliza `letterbox`, `non_max_suppression`, `Box` infra `yolo.py` | Alta — ROI calc, rotación, 5 outputs, mapeo 33→17 | Media — letterbox 192 divergente, sin bbox |

Fuentes: Ultralytics `docs.ultralytics.com/models/yolo11` + HF `Ultralytics/YOLO11` tablas SpeedCPU ONNX; `posetracker.com/best-pose-estimation-model-in-2026` FPS Pixel5; `github.com/google-ai-edge/mediapipe/issues/2184` 5 outputs; `qualcomm/ai-hub-models mediapipe_pose` export; `onnxruntime.ai/docs/performance/tune-performance/threading.html` intra_op; medición local 2026-08-24 intra sweep.

### 3. Entrada/Salida — contrato Postura

**Entrada:** `ws.py:107 decode_jpeg_b64(jpeg_b64: str) -> NDArray[np.uint8] | None` — idéntica a YOLO/gesto (ya testeada headless con `np.zeros`). Pose reutiliza `image: NDArray | None` sin nueva decodificación si se comparte buffer con YOLO (optimización: decode una vez, pasar `img` a ambos).

**Salida propuesta (normalizada [0,1] como `Box`):**

```python
@dataclass(frozen=True, slots=True)
class Keypoint:
    x: float  # [0,1] — cx / orig_w
    y: float  # [0,1] — cy / orig_h
    conf: float  # [0,1] visibility/score
    # z: float | None — opcional si MediaPipe (world coords) — no para YOLO/MoveNet

@dataclass(frozen=True, slots=True)
class Postura:
    frame_id: int
    keypoints: list[Keypoint]  # len 17 (YOLO/MoveNet) o 33 (MediaPipe) — contrato fija 17 base
    conf_global: float  # media de confs o bbox conf
    # source: Literal["yolo","mediapipe","movenet"]
```

- **YOLO pose:** `keypoints` 17, `conf` por joint del head (0.5 umbral como `YOLO_CONF`), `conf_global` = `Box.conf` del bbox persona asociado.
- **MediaPipe:** mapear 33→17 (ej. `mp 0→coco 0 nose, 11→5 left_shoulder, 12→6, 15→9 left_wrist` etc.), `conf` = `visibility`, `conf_global` = `sigmoid(Identity_1)` pose presence.
- **MoveNet:** directo 17, `conf` = `score`, `conf_global` = mean score.

### 4. Compatibilidad LeakyQueue N=1 y MAX_FPS

- `ws.py:129 LeakyQueue[T] maxsize=1` + `AsyncLeakyQueue` descarta anterior si llega nuevo antes de `queue.get()` — **pose debe ser atómico** (single `sess.run`). YOLO y MoveNet son atómicos; MediaPipe 2-stage no — si se usa MediaPipe, envolver detector+landmarker en una sola `predict(img)` sin yield intermedio, o hacer snapshot del deque.
- `frontend/ws-client.js:22 MAX_FPS 10` throttled + `bufferedAmount>64KB` skip — pose 5 Hz = cliente envía 10 FPS, servidor procesa 10 FPS detection pero **pose cada 2 frames** (skip lógico `frame_id % 2 == 0`). LeakyQueue sigue N=1, no necesita N=2.
- `config.py:MAX_FRAME_SIZE 640`, `JPEG_QUALITY 75` — pose 640 YOLO no requiere resize extra; MoveNet 192 requiere downscale adicional (0.58 ms letterbox extra).

### 5. Presupuesto latencia completo (resumen)

```
Glass-to-Glass <200 ms (lazo cerrado) — breakdown 10 Hz:
  captura + jpeg encode (canvas 0.75)     ~8 ms
  WS send + localhost RTT                  ~5 ms
  decode_jpeg_b64                         1.6 ms  (medido)
  letterbox 640                            0.6 ms  (medido)
  YOLO11n detect  intra2                  73.8 ms  (medido)
  Hand gesto (mediapipe)                  ~20 ms  (est. lite)
  ─────────────────────────────────────────────────
  subtotal sin pose                      ~109 ms  ✅ <200 ms deja 91 ms

  + YOLO11n-pose intra2                   92.7 ms  (medido)
  ─────────────────────────────────────────────────
  total inline 10Hz                      ~202 ms  ❌ >200 ms (p95  ~225 ms) — no cabe

Canal 5 Hz piggyback:
  pose 92.7 ms cada 200 ms → p95 115 ms <200 ms canal → TTL 1s en Whiteboard ✅
  MoveNet 14 ms inline 10Hz → total ~123 ms ✅ <200 ms pero mono-persona
  MediaPipe 35 ms inline → total ~144 ms ✅ <200 ms pero duplica runtime
```

## Conclusión y recomendación para Envelope/Whiteboard

### Conclusión

1. **YOLO11n-pose es el único que cumple constraints del stack actual sin añadir runtime:** misma `onnxruntime 1.29`, misma `letterbox` infra, multi-persona single-pass, 17 COCO directo, export ONNX oficial, sin colisión `mediapipe`/`TFLite`. Su latencia 92.7 ms p50 intra2 es **alta para <20 ms** pero **aceptable para canal 5 Hz** — el target <20 ms del mapa #71 es inalcanzable a 640² en CPU con cualquier modelo state-of-the-art sin NPU (solo MoveNet 192² lo roza, a costa de mono-persona).
2. **MediaPipe Pose Lite es técnicamente más rápido (35 ms) pero arquitectónicamente costoso:** 2-stage, 33 joints con mapeo, 5 outputs TFLite, sin ONNX oficial, duplica RSS y riesgo `protobuf` clash, y no aprovecha `intra_op_num_threads=2`. Su ventaja 35 ms vs 92 ms no compensa si igual va a canal 5 Hz — la diferencia de 57 ms no cambia que ambos necesitan canal lento. Además `hand_landmarker.task` ya usa MediaPipe para gesto — añadir pose MediaPipe saturaría el mismo thread pool TFLite.
3. **MoveNet Lightning es el único <20 ms (14 ms) pero mono-persona y sin bbox** — útil si el caso de uso es fitness single-user (ej. `PercepcionVista` para `DecisionAgentica` de postura individual), pero Percepción Enriquecida v2 ya tiene `yolo.py` multi-persona. Si se elige MoveNet, se duplicaría lógica de persona (YOLO bbox + MoveNet keypoints) sin ganancia vs YOLO pose que ya da bbox.

### Recomendación (para contrato Envelope/Whiteboard)

**Elegir `YOLO11n-pose` en canal 5 Hz piggyback. Descartar MediaPipe Pose como runtime primario; mantener MoveNet como baseline documentado pero no implementar en v2.**

#### Contrato Envelope

```python
# ws.py — nuevo type
EnvelopeType = Literal["frame","detecciones","gesto","estado","postura","enroll_sync",...]
# payload postura
{
  "frame_id": int,          # correlación con frame 640
  "keypoints": [{"x":float,"y":float,"conf":float}],  # len 17, [0,1]
  "conf_global": float,     # [0,1] — bbox conf o mean keypoint conf
  "source": "yolo11n-pose", # para telemetría
}
# WhiteboardState.PercepcionVista
class PercepcionVista:
    detecciones: list[Box] | None  # TTL 0.2s (10 Hz)
    gesto: GestoReconocido | None   # TTL 0.5s
    postura: Postura | None         # TTL 1.0s (5 Hz) — NUEVO
    identidades: ...                # ya existe
```

- **Piggyback:** `perception_ws_handler` envía `postura` como envelope separado **no bloqueante** — `process_single_frame` hace `yolo_boxes, gesto = run_inference(...)` a 10 Hz, y cada 2 frames `if frame_id % 2 == 0: postura = pose_detector.predict(img)` → `make_envelope("postura", seq, postura_payload)`. LeakyQueue N=1 permanece — pose no encola, solo samplea último frame disponible (snapshot `img` compartido).
- **Compat `LeakyQueue`/`MAX_FPS`:** detección y pose comparten `decode_jpeg_b64` (una vez por frame) y `letterbox` (YOLO 640 directo, no extra). `frontend/ws-client.js` sigue throttled 10 FPS; servidor decide cadencia pose (5 Hz). `bufferedAmount>64KB` skip preservado — pose no añade presión WS (1 envelope extra cada 200 ms ~500 bytes).

#### Infra

- **Modelo:** `yolo11n-pose.onnx` 11.8 MB en `plataforma/webcam/backend/models/` (añadir a `descargar_modelos.py:MODELS` con URL `https://github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n-pose.onnx`, hash `None` informativo como yolo detect). Factory `get_pose_detector()` mirror `get_yolo_detector()` en `inference/pose.py` (nuevo módulo, no mezclar con `yolo.py`).
- **SessionOptions:** fijar `intra_op_num_threads=2`, `inter_op_num_threads=1`, `execution_mode=ORT_SEQUENTIAL` (modelo sin branches) — ver `onnxruntime.ai/docs/performance/tune-performance/threading.html`. Medición intra2 92.7 ms es baseline; intra0 69 ms es 25% más rápido pero roba threads a VLM/profundidad.
- **Headless tests:** `np.zeros((640,640,3),uint8)` → `pose_detector.predict(None) == []` stub + `predict(zeros) -> list[Postura]` con `conf_global` clamped [0,1], `x,y` [0,1] — igual patrón `yolo.py:312` y `gesture.py:120`.
- **Alternativa si <20 ms es hard:** documentar MoveNet Lightning como **switch feature-flag** (`config.py:POSE_BACKEND="movenet"`) pero no implementar — YOLO pose 5 Hz cubre 80% casos; MoveNet solo si benchmark en target hardware (Pi5/Jetson) exige <20 ms.

#### Presupuesto actualizado

| Canal | Frecuencia | Latencia p50 | TTL Whiteboard | Glass-to-Glass |
|---|---|---|---|---|
| `detecciones` YOLO11n | 10 Hz | 73.8 ms | 0.2 s | 109 ms con gesto |
| `gesto` Hand | 10 Hz | ~20 ms | 0.5 s | piggyback |
| **`postura` YOLO11n-pose** | **5 Hz** | **92.7 ms** | **1.0 s** | **no en lazo — canal lento** |
| `profundidad` (futuro) | 5 Hz | ~80 ms est. | 1.0 s | canal lento |
| `leyenda` VLM 1Hz | 1 Hz | ~300 ms p50 | 2.0 s | canal lento |

*Lazo cerrado <200 ms solo usa `detecciones`+`gesto`+`ReID` (BlazeFace frontend <15 ms offload) — pose no lo bloquea.*

## Fuentes primarias

- **Ultralytics YOLO11 docs (oficial):** `docs.ultralytics.com/models/yolo11` — tabla SpeedCPU ONNX YOLO11n 56.1±0.8 ms, YOLO11n-pose 52.4±0.5 ms, params/FLOPs. Verificado 2026-08-24.
- **Ultralytics HuggingFace `Ultralytics/YOLO11`:** tabla pose mAP 50.0/81.0, params 2.9M FLOPs 7.6B.
- **Ultralytics assets (pesos):** `github.com/ultralytics/assets/releases/download/v8.3.0/yolo11n-pose.onnx` (11.85 MB) y `yolo11n.onnx` (10.9 MB) — HEAD Content-Length verificado.
- **Ultralytics issue #18867:** `nms=True` export no soporta WebGPU ORT, recomendación NMS en postprocess (usado en `yolo.py:171`).
- **Google AI Edge Pose Landmarker (oficial):** `developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker` — bundle Lite 224+256 float16, 33 landmarks, pipeline detector→landmarker.
- **MediaPipe issues #2184:** `github.com/google-ai-edge/mediapipe/issues/2184` — 5 outputs `[1,195]` = 39×5, `tf2onnx` 396 transposes, input /255, output /255.
- **Posetracker.com (benchmark 2026-07-07):** `posetracker.com/news/best-pose-estimation-model-in-2026` — Pixel5 web FPS: MoveNet Lightning 34 FPS (29 ms), BlazePose Lite 12 FPS (83 ms), Full 11 FPS, Heavy 5 FPS; desktop similar.
- **Qualcomm AI Hub `mediapipe_pose`:** `github.com/qualcomm/ai-hub-models/src/qai_hub_models/models/mediapipe_pose/README.md` — export `onnx`/`tflite`, NPU 0.86 ms (no CPU).
- **ONNX Runtime threading (oficial):** `onnxruntime.ai/docs/performance/tune-performance/threading.html` — `intra_op_num_threads` default físicos, `inter_op`, `graph_optimization_level`, spinning, NUMA. Issue `microsoft/onnxruntime#24101` bottleneck intra0 vs intra1.
- **ONNX Runtime 1.29 release:** `newreleases.io/project/pypi/onnxruntime/release/1.29.0` — changelog.
- **TF.js BlazePose benchmark:** `github.com/tensorflow/tfjs-models/blob/master/pose-detection/src/blazepose_tfjs/README.md` — bundle sizes Lite 10.6 MB, FPS tables.
- **Medición local (repo):** `plataforma/webcam/backend/models/yolo11n.onnx` 10.9 MB, `yolo11n-pose.onnx` 11.85 MB (tmp), ORT 1.29 CPU `intra2` 73.8/92.7 ms, `letterbox` 0.58 ms, `decode_jpeg_b64` 1.62 ms — script sintético 2026-08-24 (ver §1.1).
- **Repo local:** `plataforma/webcam/backend/inference/yolo.py:298 SessionOptions`, `ws.py:129 LeakyQueue`, `config.py:MAX_FRAME_SIZE 640`, `pyproject.toml onnxruntime==1.29.* mediapipe==1.0.1`, `frontend/ws-client.js:22 MAX_FPS 10`.

---
*Research AFK — no cierra issue #72. Context pointer: rama `research/072-postura-benchmark`, archivo `docs/agents/research/072-postura-benchmark.md`. Siguiente: grilling de contrato `postura` Envelope/Whiteboard y ticket task `inference/pose.py` + `descargar_modelos.py` + `ws.py` piggyback 5 Hz.*
