# R2 — Percepción webcam: YOLOv8n/YOLO11n ONNX + MediaPipe en CPU (Windows/WSL2)

Fecha: 2026-08-19. Investigación contra fuentes primarias (PyPI, docs oficiales de Ultralytics, onnxruntime.ai, Google AI Edge/MediaPipe, repos `ultralytics/ultralytics` y `google-ai-edge/mediapipe`). Context pointer: issue #41 (https://github.com/mauriciosoyastor/embodied-ai/issues/41).

## Pregunta

¿Cuál es el estado actual (2026) de **YOLOv8n ONNX + MediaPipe en Python CPU** para el módulo de percepción webcam de la plataforma (webcam del navegador → frames JPEG → WebSocket → backend Python, Windows 11 / WSL2, sin GPU en el hito)? Cubre: versiones actuales y mantenidas de `ultralytics`, `onnxruntime`, `opencv-python`, `mediapipe`, `numpy` y su compatibilidad con Python 3.10+; cómo exportar/obtener YOLOv8n (o YOLO11n) a ONNX y correrlo con onnxruntime en CPU (pesos, descarga, `providers`, preprocesado con letterbox, postprocesado con NMS y filtro de confianza); rendimiento esperado en CPU (ms/frame) para 640×640 y resoluciones de webcam (480p/720p); API actual de MediaPipe Hands (`mp.solutions.hands` vs MediaPipe Tasks), landmarks y clasificación de gestos simples (pulgar arriba, palma abierta, puño) sin modelo extra; y notas de instalación de Windows/WSL2 (wheels, dependencias nativas, EGL/GLFW no requerido para inferencia CPU).

## Hallazgos

### 1. Versiones actuales (agosto 2026) y compatibilidad Python

- **`ultralytics` (PyPI)** — **v8.4.120** (2026-08-13), `Python >= 3.8`, licencia **AGPL-3.0**. Cadencia de release muy alta (~varias por semana). Incluye los modelos YOLOv8, YOLO11 y YOLO26 (2026); el paquete cubre train/val/predict/export/benchmark. Fuente: https://pypi.org/project/ultralytics/ (Requires Python >=3.8; release history).
- **`onnxruntime` (PyPI, CPU)** — **v1.29.0** (2026-08-17), `Python >= 3.11`. Wheels `cp311`–`cp314` para `win_amd64`, `manylinux_2_28`, `macosx_14_0_arm64`. **Punto clave de compatibilidad: la línea actual ya no publica wheels para Python 3.10**; en 3.10 habría que pinchar una versión vieja (≤1.24.x). El `onnxruntime-gpu` 1.29.0 también exige Python >=3.11 y CUDA 12. Fuentes: https://pypi.org/project/onnxruntime/ y https://pypi.org/project/onnxruntime-gpu/
- **`opencv-python` (PyPI)** — **5.0.0.93** (OpenCV 5.0, 2026-07-02) es la más nueva; la línea **4.x sigue activa** (4.14.0.94, 2026-07-28; 4.13.0.92, 2026-02-05). `Python >= 3.6`, wheels `cp37-abi3`. Para el hito conviene **pinchar 4.x** (4.14/4.13): madurez del ecosistema (mediapipe/ultralytics) y aviso en el repo opencv-python de que los builds para Python 3.9+ se hacen con NumPy 2.x. Fuentes: https://pypi.org/project/opencv-python/ y https://github.com/opencv/opencv-python/releases
- **`mediapipe` (PyPI)** — **v1.0.1** (2026-08-14; 1.0.0 el 2026-07-27; antes 0.10.35), wheels `py3-none-any` para `win_amd64`, `win_arm64`, `manylinux_2_28`, `macosx_11_0_arm64`. La guía oficial de setup indica **Python 3.9+**. Fuentes: https://pypi.org/project/mediapipe/ y https://developers.google.com/edge/mediapipe/solutions/setup_python
- **`numpy` (PyPI)** — **v2.5.2** (2026-08-09); la 2.5 requiere **Python 3.12+**; **2.2.x** es la última línea con soporte de Python 3.10–3.13 (2.4/2.5 requieren 3.11+). onnxruntime y opencv-python dependen de numpy (opencv 4.x se compila contra NumPy 2.x para Python 3.9+). Fuentes: https://pypi.org/project/numpy/, https://github.com/numpy/numpy/releases y https://endoflife.date/numpy
- **Conclusión de compatibilidad**: el cuello de botella de Python 3.10 es **onnxruntime** (>=3.11 desde ~1.25). Para el stack del hito lo natural es **Python 3.11 o 3.12** (3.12 cubre numpy 2.5 + onnxruntime + mediapipe 3.9+ + ultralytics 3.8+).

### 2. Cómo obtener/exportar YOLOv8n (o YOLO11n) a ONNX y correrlo con onnxruntime en CPU

- **Pesos y descarga**: `YOLO("yolo11n.pt")` (o `yolo11n.onnx`) descarga automáticamente los pesos oficiales COCO 80 clases la primera vez. YOLO11n: 640 px, mAP 39.5, 2.6 M params, 6.5 GFLOPs; YOLOv8n: 640 px, mAP 37.3, 3.2 M params, 8.7 GFLOPs. Fuente: https://docs.ultralytics.com/models/yolo11/ y https://docs.ultralytics.com/models/yolov8/
- **Export a ONNX**: `model.export(format="onnx")` crea `yolo11n.onnx`. Argumentos relevantes: `imgsz` (640 por defecto; tupla `(h, w)` permitida), `simplify=True` (default; simplifica con `onnxslim`), `opset`, `dynamic` (tamaños variables), `quantize=8/16` (INT8/FP16; INT8 usa calibración de ONNX Runtime con `data="coco8.yaml"`), `nms=True` (embebe NMS en el grafo; ver postprocesado). Con `imgsz=640` y COCO la salida non-end2end es un único tensor **(1, 4+80, 8400)** = **(1, 84, 8400)**: primeras 4 filas = caja (cx, cy, w, h), resto = scores por clase. Fuentes: https://docs.ultralytics.com/modes/export/ y https://docs.ultralytics.com/integrations/onnx/
- **Ejecutar con onnxruntime**: crear sesión con `ort.InferenceSession("yolo11n.onnx", providers=["CPUExecutionProvider"])` (en CPU solo ese provider) y `sess_options.graph_optimization_level = ORT_ENABLE_ALL`. En Windows el paquete `onnxruntime` (CPU) es la vía; `onnxruntime-gpu` solo si más adelante hay GPU (CUDA 12). Ultralytics también permite `YOLO("yolo11n.onnx")` (usa onnxruntime internamente). Fuentes: https://onnxruntime.ai/docs/get-started/with-python.html y https://docs.ultralytics.com/integrations/onnx/
- **Preprocesado (letterbox)**: igual al de Ultralytics — redimensionar preservando aspect ratio y **hacer padding** (relleno gris 114) hasta 640×640 (múltiplo de stride), convertir BGR→RGB, normalizar a [0,1] y pasar a `float32` CHW `(1, 3, 640, 640)`. Fuente: guía de export/ejemplos de inferencia ONNX de Ultralytics (https://docs.ultralytics.com/modes/export/ y https://github.com/ultralytics/ultralytics/tree/main/examples).
- **Postprocesado (NMS + confianza)**: transponer la salida a `(8400, 84)`, mantener solo detecciones con `conf >= 0.25` (default Ultralytics), decodificar `(cx, cy, w, h)` → `(x1, y1, x2, y2)` y aplicar **NMS con IoU = 0.7** (default). Se puede hacer en numpy (sin modelo extra); alternativamente exportar con `nms=True` (op `EfficientNMS` de ORT) para que el grafo devuelva ya `(1, max_det, 6)` con `[x1, y1, x2, y2, conf, class_id]`. Fuentes: https://docs.ultralytics.com/modes/export/ (argumentos `conf`, `iou`, `nms`, FAQ de shapes) y ejemplo de inferencia ONNX del repo Ultralytics.
- **Dependencias**: exportar requiere `ultralytics` (que trae torch); **en runtime no hace falta torch** — solo `onnxruntime` + `opencv-python` + `numpy`.

### 3. Rendimiento CPU (ms/frame)

- **Referencias oficiales de Ultralytics** (tablas de cada modelo, medida en CPU ONNX a 640×640):
  - **YOLOv8n: 80.4 ms** (mAP 37.3).
  - **YOLO11n: 56.1 ± 0.8 ms** (mAP 39.5) — más rápido **y** más preciso que YOLOv8n.
  - YOLO11s: 90.0 ± 1.2 ms; YOLOv8s: 128.4 ms.
  - Fuentes: https://docs.ultralytics.com/models/yolov8/ y https://docs.ultralytics.com/models/yolo11/
- **ONNX ≈ hasta 3× más rápido que PyTorch en CPU** (claim oficial de Ultralytics para export ONNX/OpenVINO). Fuentes: https://docs.ultralytics.com/modes/export/ y https://docs.ultralytics.com/integrations/onnx/
- **480p/720p**: como el modelo recibe siempre la entrada **letterbox a `imgsz` (640×640)**, el costo de inferencia **no depende de la resolución de la webcam**; 480p/720p solo cambian el resize (microsegundos). Para bajar latencia se baja **`imgsz`**, no la resolución fuente: el costo escala ~cuadrático con `imgsz` (320 ≈ 1/4 del costo de 640; el benchmark RPi lo usa para pasar de ~5 a 15+ FPS). Fuente: https://docs.ultralytics.com/modes/export/ (`imgsz`) y benchmark comunitario RPi (https://kadirmertabatay.github.io/rpi-yolo-benchmark/benchmarks/yolov8/yolov8n).
- **Referencias comunitarias de CPU** (para calibrar la máquina objetivo): YOLO11n ONNX CPU **38.9 ± 0.7 ms** (bench de aimodels.fyi, CPU de escritorio); revisión 2026 que cita YOLOv8n ONNX ~18–20 ms en hardware moderno (arXiv 2510.09653); en entornos limitados (VM de 1 núcleo, Raspberry Pi 5) los números publicados son ~200 ms (no representativos de un escritorio Windows 11 moderno). Fuentes: https://www.aimodels.fyi/models/compare/yolo11n-ultralytics-vs-yolov8-ultralytics, https://arxiv.org/html/2510.09653v3 y https://github.com/ihauss/benckmark-yolo-inference-on-CPU
- **Presupuesto del hito (CPU)**: YOLO11n a 640 (~56 ms) + MediaPipe Hands (~10–20 ms, sección 4) + JPEG/WebSocket → del orden de **10–12 FPS continuos**. Estrategia recomendada para la FSM: **YOLO throttled** (5–10 Hz en un hilo aparte, o `imgsz=480`/320) y **gestos a tasa completa** (~30 FPS, son baratos). Ultralytics provee `yolo benchmark model=yolo11n.onnx imgsz=640 device=cpu` para medir en la máquina real. Fuente: https://docs.ultralytics.com/modes/benchmark/

### 4. MediaPipe Hands: API actual y gestos sin modelo extra

- **`mp.solutions.hands` está en legacy**: Google **terminó el soporte de las Legacy Solutions el 2023-03-01**; `mp.solutions.hands` fue "upgraded" a **Hand landmark detection (Tasks)**. El código legacy sigue viajando en el wheel as-is, pero la API canónica actual es MediaPipe Tasks (`mp.tasks.vision.HandLandmarker`). Fuentes: https://developers.google.com/edge/mediapipe/solutions/guide (sección "Legacy solutions") y https://github.com/google-ai-edge/mediapipe/issues/5410
- **Modelo**: `hand_landmarker.task` (float16; bundle con **palm detection + hand landmarks**; entradas 192×192/224×224). Se descarga de `https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task` y se carga con `BaseOptions(model_asset_path=...)`. Fuente: https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker (sección "Models") y notebook oficial https://github.com/googlesamples/mediapipe/tree/main/examples/hand_landmarker
- **API**: `HandLandmarkerOptions` con `running_mode` (`IMAGE`/`VIDEO`/`LIVE_STREAM`), `num_hands` (default 1), `min_hand_detection_confidence` (0.5), `min_hand_presence_confidence` (0.5), `min_tracking_confidence` (0.5), y `result_callback` para `LIVE_STREAM`. Métodos `detect` / `detect_for_video` (requiere `frame_timestamp_ms`) / `detect_async`. En **VIDEO/LIVE_STREAM el task usa tracking**: solo re-dispara el palm detector cuando pierde la mano, lo que reduce la latencia. Fuente: https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker/python
- **Salida**: por mano — `Landmarks` (21 puntos x, y, z normalizados a [0,1], z relativo a la muñeca), `WorldLandmarks` (mismo 21 en metros, origen en el centro geométrico de la mano) y `Handedness` (izquierda/derecha). Fuente: https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker/python (sección "Handle and display results")
- **Clasificar gestos sin modelo extra**: con los 21 landmarks se implementa un **clasificador por reglas geométricas** (heuristico): para cada dedo, "extendido" si el tip está más lejos de la muñeca que la articulación PIP (o por ángulo en la articulación), y para el pulgar comparando el desplazamiento del tip respecto del IP. Reglas para el hito: **palma abierta** = 4 dedos + pulgar extendidos; **puño** = ninguno extendido; **pulgar arriba** = solo el pulgar extendido. Es la técnica dominante de la comunidad (sin red adicional) y ya reporta ~95% de accuracy en implementaciones publicadas para 3 gestos. Fuente de la técnica: documentación de landmarks de MediaPipe (https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker/index) y evaluación publicada en IIETA (https://www.iieta.org/journals/isi/paper/10.18280/isi.280311); implementaciones de referencia en https://github.com/jpjp210202/Real-Time-Static-Hand-Gesture-Recognition
- **Alternativa con modelo (no necesaria)**: la task **GestureRecognizer** clasifica 7 gestos entrenados (`Thumb_Up`, `Open_Palm`, `Closed_Fist`, etc.) pero usa `gesture_recognizer.task` (modelo extra). Para el hito alcanza con las reglas geométricas. Fuente: https://developers.google.com/edge/mediapipe/solutions/vision/gesture_recognizer
- **Benchmark oficial de la task**: HandLandmarker (full) = **17.12 ms CPU / 12.27 ms GPU** (medido por Google en **Pixel 6**, móvil; un escritorio CPU moderno es más rápido). Fuente: https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker/index (sección "Task benchmarks")

### 5. Windows 11 / WSL2: wheels, dependencias nativas, sin GPU/GL

- **Wheels nativos**: `onnxruntime` (win_amd64), `mediapipe` 1.0.1 (win_amd64) y `opencv-python` (win_amd64) tienen wheels precompilados; no hace falta compilar nada en Windows. opencv-python y onnxruntime requieren el **Visual C++ Redistributable 2019+** en Windows. Fuentes: https://pypi.org/project/onnxruntime/, https://pypi.org/project/mediapipe/, https://pypi.org/project/opencv-python/ (FAQ) y https://onnxruntime.ai/docs/install/ (Requirements)
- **MediaPipe en Windows corre en CPU**: el changelog de MediaPipe indica que al construir para Windows se **desactiva GPU/OpenGL** ("automatically disable gpu (OpenGL) when building for Windows" y "mark mediapipe/gpu:gl_context incompatible on Windows"); el delegate de inferencia queda en CPU. **No se requiere EGL ni GLFW para inferencia CPU** — la percepción webcam del hito no renderiza en el backend (el overlay lo dibuja el visor Three.js del navegador). Fuente: changelog de MediaPipe (https://data.safetycli.com/packages/pypi/mediapipe/changelog, notas de 0.10.33) y https://developers.google.com/edge/mediapipe/solutions/setup_python
- **WSL2**: corre los mismos wheels Linux (manylinux) con pip normal; conviene para unificar con el CI y permitir, si más adelante se agrega GPU, `onnxruntime-gpu` con CUDA passthrough. Para el hito (CPU) da igual Windows nativo o WSL2; **ninguno requiere EGL/GLFW**.
- **Python recomendado**: 3.11 o 3.12 (ver sección 1: onnxruntime 1.29 exige >=3.11; mediapipe 3.9+; numpy 2.5 en 3.12+).

## Recomendación

1. **Stack de versiones (agosto 2026)**: `onnxruntime==1.29.0` (CPU) + `opencv-python` **4.14.x/4.13.x** (no 5.0 por madurez del ecosistema) + `mediapipe==1.0.1` + `numpy` 2.x según Python, sobre **Python 3.12** (o 3.11). `ultralytics` 8.4.x **solo en el entorno de export** (trae torch); **el runtime webcam no necesita torch**.
2. **Modelo**: **YOLO11n** (no YOLOv8n): en CPU ONNX 640×640 es ~56 ms vs ~80 ms y con mejor mAP (39.5 vs 37.3). Exportar una vez con `model.export(format="onnx", imgsz=640, simplify=True)` y commitear `yolo11n.onnx` en el módulo (p. ej. `plataforma/webcam/models/`), con pesos descargados una sola vez.
3. **Runtime YOLO (CPU)**: `ort.InferenceSession(path, providers=["CPUExecutionProvider"])`, preprocesado con **letterbox a 640×640** (padding 114, BGR→RGB, /255, float32 CHW) y postprocesado en numpy: filtro `conf >= 0.25`, decodificar cajas y **NMS con IoU = 0.7**. (Opcional: export con `nms=True` si se quiere NMS en el grafo.)
4. **Runtime MediaPipe**: usar **Tasks API** (`mp.tasks.vision.HandLandmarker`), NO `mp.solutions.hands` (legacy, soporte terminado en 2023). Modelo `hand_landmarker.task`, `running_mode=LIVE_STREAM` (o VIDEO con `frame_timestamp_ms`), `num_hands=1`. Clasificar los 3 gestos de la FSM (`RUNNING`/`PAUSED`/`ABORTED` ↔ palma abierta / puño / pulgar arriba) con **reglas geométricas sobre los 21 landmarks** (sin modelo extra).
5. **Concurrencia/latencia**: gestos a tasa completa (~30 FPS posibles; HandLandmarker ~17 ms CPU en móvil, menos en escritorio) y **YOLO throttled a 5–10 Hz** (o `imgsz=480/320`) en un hilo aparte para no bloquear el loop; el budget CPU del hito con YOLO11n@640 (~56 ms) + MediaPipe (~10–20 ms) da ~10–12 FPS continuos. Medir local con `yolo benchmark model=yolo11n.onnx imgsz=640 device=cpu`.
6. **Windows/WSL2**: todo corre con wheels precompilados (win_amd64); mediapipe en Windows es CPU-only (sin OpenGL) y **no se necesita EGL/GLFW** para inferencia; mantener el plan de energía High Performance para números de CPU reproducibles.
7. **Fuera de alcance del hito** (registrado para decisiones futuras): `onnxruntime-gpu`/CUDA si aparece GPU, `gesture_recognizer.task` si se quiere clasificación entrenada, WebRTC, y fine-tuning de modelos propios.

## Fuentes

- ultralytics (PyPI): https://pypi.org/project/ultralytics/
- Ultralytics — Export mode: https://docs.ultralytics.com/modes/export/
- Ultralytics — ONNX integration: https://docs.ultralytics.com/integrations/onnx/
- Ultralytics — Benchmark mode: https://docs.ultralytics.com/modes/benchmark/
- Ultralytics — YOLO11 models: https://docs.ultralytics.com/models/yolo11/
- Ultralytics — YOLOv8 models: https://docs.ultralytics.com/models/yolov8/
- Ultralytics — ejemplos de inferencia ONNX: https://github.com/ultralytics/ultralytics/tree/main/examples
- onnxruntime (PyPI, CPU): https://pypi.org/project/onnxruntime/
- onnxruntime-gpu (PyPI): https://pypi.org/project/onnxruntime-gpu/
- onnxruntime — Get started Python: https://onnxruntime.ai/docs/get-started/with-python.html
- onnxruntime — Install: https://onnxruntime.ai/docs/install/
- opencv-python (PyPI): https://pypi.org/project/opencv-python/
- mediapipe (PyPI): https://pypi.org/project/mediapipe/
- MediaPipe — Setup Python: https://developers.google.com/edge/mediapipe/solutions/setup_python
- MediaPipe — Solutions guide (legacy solutions): https://developers.google.com/edge/mediapipe/solutions/guide
- MediaPipe — Hand landmarker (overview + benchmarks): https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker/index
- MediaPipe — Hand landmarker guía Python: https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker/python
- MediaPipe — Gesture recognizer: https://developers.google.com/edge/mediapipe/solutions/vision/gesture_recognizer
- MediaPipe — model `hand_landmarker.task`: https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task
- MediaPipe — issue #5410 (legacy hands vs Tasks): https://github.com/google-ai-edge/mediapipe/issues/5410
- MediaPipe changelog (0.10.33, Windows sin GPU): https://data.safetycli.com/packages/pypi/mediapipe/changelog
- numpy (PyPI): https://pypi.org/project/numpy/
- numpy — releases: https://github.com/numpy/numpy/releases
- endoflife.date — NumPy: https://endoflife.date/numpy
- Benchmark comunitario CPU (RPi): https://kadirmertabatay.github.io/rpi-yolo-benchmark/benchmarks/yolov8/yolov8n
- Benchmark comunitario CPU (aimodels.fyi, yolo11n ONNX): https://www.aimodels.fyi/models/compare/yolo11n-ultralytics-vs-yolov8-ultralytics
- Revisión YOLO 2026 (arXiv 2510.09653): https://arxiv.org/html/2510.09653v3
- Benchmark YOLOv8 ONNX CPU (ihauss): https://github.com/ihauss/benckmark-yolo-inference-on-CPU
- Clasificación de gestos por landmarks (IIETA): https://www.iieta.org/journals/isi/paper/10.18280/isi.280311
- Implementación de referencia de gestos (Open Palm/Fist/Thumbs Up): https://github.com/jpjp210202/Real-Time-Static-Hand-Gesture-Recognition
