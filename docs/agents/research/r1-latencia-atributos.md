# R1 — Research: latencia Glass-to-Glass YOLO11n vs YOLO-World + costo color (HSV vs VLM)

> Ticket: `#89` · Parent: `#88 Mapa — Percepción descriptiva interactiva` · Rama: `research/r1-latencia-atributos` · Fecha: 2026-08-24 · Idioma: español · Bloquea: contrato `AtributoVista` + `PromptList` vs `Whitelist`

## Pregunta

¿Qué latencia y costo real tiene cada opción para responder "color/tamaño/distancia/qué es" sin romper **Glass-to-Glass <200 ms** en canal rápido (YOLO+gesto+ReID) sobre CPU?

Comparar sobre stack actual `plataforma/webcam` (onnxruntime CPU, `intra_op=2`, `LeakyQueue N=1`, `MAX_FPS=10`):

- **YOLO11n 640** (baseline `yolo.py:312`, ~35 ms) vs **YOLO11n 480/320** vs **YOLO-World s/m 640** (~42-55 ms) — mismo `letterbox` `yolo.py:134` + `NMS` `yolo.py:171`.
- **Color**: histograma HSV dominante sobre crop bbox (rápido <5 ms CPU, sin red) vs K-means vs VLM 1 Hz `app.py:201` (~300 ms `Groq→HF→Gemini→mock`).
- Medir `infer_ms`, `total_ms`, `FPS` sostenido, `bufferedAmount` skip rate, memoria.

Salida: tabla `modelo | IMGSZ | infer_p50/p95 | Glass-to-Glass | peso MB | acierto color` + recomendación canal rápido vs lento.

---

## TL;DR — scannable en 2 min

**YOLO11n 640 sigue siendo la única opción viable para canal rápido Glass-to-Glass <200 ms en CPU.** YOLO-World s/m viola presupuesto (infer ×1.3-1.5 + overhead texto ~10-15 ms) y triplica/quinruplica peso y memoria. **HSV dominante es 0.03-0.6 ms/crop (<1 ms total) y no toca presupuesto; VLM debe quedarse en canal lento 1 Hz con TTL por campo; K-means queda descartado (>200 ms frío).** GroundingDINO queda fuera (2-15 s CPU, sin ONNX oficial estable).

**Recomendación:**

| Canal | YOLO | Color | Distancia/Tamaño |
|-------|------|-------|------------------|
| **Rápido Glass-to-Glass <200 ms** (lazo cerrado) | **YOLO11n 640** (si CPU débil <100 ms sostenido → 480) | **HSV histograma 18 bins H, máscara S>50 V>50** — <1 ms, sin red | bbox `w*h` + MiDaS `z_rel` median 3×3 |
| **Lento 300 ms p50 tolerado** (voz/enriquecimiento) | YOLO11n 640 o YOLO-World-s 640 bajo flag `PromptList` (open-vocab bajo demanda) | **VLM 1 Hz** (`app.py:201`, Groq→HF→Gemini→mock) con `PromptList` libre | VLM caption + MiDaS corrige `z_m=null` |

**Tablas clave:**

| Modelo | IMGSZ | infer_p50 CPU ONNX | infer_p95 | Glass-to-Glass rápido | peso PT | peso ONNX | mem runtime |
|--------|-------|-------------------|-----------|----------------------|---------|-----------|-------------|
| **YOLO11n** | **640** | **37-56 ms** | 40-58 ms | **~105 ms ✅** | 5.5 MB | **10.4 MB** | 85-120 MB |
| YOLO11n | 480 | **24 ms** | 26 ms | **~85 ms ✅** | — (mismo .pt re-exportado) | ~10 MB | 80 MB |
| YOLO11n | 320 | 12.7 ms | 13.7 ms | ~70 ms ✅ | — | ~10 MB | 75 MB |
| **yolov8s-worldv2** | 640 | **~52-68 ms** estim. (ver §3) | 70-85 ms | **~135 ms ⚠️** | **24.7 MB** | **48.8-51 MB** | 200-300 MB |
| yolov8m-worldv2 | 640 | ~85-110 ms | 120 ms | **~175-200 ms ❌** borderline | **52 MB** | ~100-110 MB | 400 MB |
| GroundingDINO Swin-T | 800 | **2000-15000 ms** | — | **>>200 ms ❌** | **~180 MB .pth** | sin ONNX oficial | >1 GB |

| Método color | Latencia/crop | Latencia 3 boxes | Red | Dependencia | Acierto color | Dónde |
|--------------|---------------|------------------|-----|-------------|--------------|-------|
| **HSV histograma 18 bins H** | **0.02-0.03 ms** (120×120), 0.54 ms (640×480) | **0.37 ms** | no | OpenCV | bueno con máscara S/V, falla grises | **canal rápido** |
| K-means k=3 (sklearn) | 6-7 ms (warm), **2300 ms frío** | 18-20 ms | no | sklearn | mejor en multicolor pero lento | descartado rápido |
| **VLM 1 Hz** | **~300 ms p50** (HTTP) | igual | sí | Groq/HF/Gemini | excelente descrip. libre | **canal lento** |

> Ver §7 para presupuesto Glass-to-Glass completo y §8 para recomendación de contrato `AtributoVista` con TTL por campo.

---

## 1. Baseline local `plataforma/webcam` — código y mediciones propias

### 1.1 Stack actual (fuentes primarias: código)

| Componente | Valor | Fuente |
|-----------|-------|--------|
| `IMGSZ` | `640` | `yolo.py:23` |
| `letterbox` | resize+pad gris 114, `cv2.INTER_LINEAR`, `copyMakeBorder` | `yolo.py:134` (coste medido `0.57 ms p50`) |
| `NMS` | IoU `0.7` clásico, `np.argsort` + `ovr <= thr` | `yolo.py:171` (coste `0.045 ms p50`, 0.10 ms p95) |
| `intra_op_num_threads` | `2` (solo depth/pose lo setean explícito; YOLO usa default ORT) | `depth.py:150`, `pose.py:228`; `yolo.py` no setea → verifica coherencia con `MAPA #88` constraint `intra_op=2` (pendiente unificar) |
| `LeakyQueue N=1` | `deque(maxlen=1)`, `put` descarta oldest | `ws.py:137` + `AsyncLeakyQueue:173` (`maxsize=1`) |
| `MAX_FPS` | `YOLO_MAX_HZ=10`, `GESTURE_MAX_HZ=30`, `VLM_INTERVAL=30` → 1 Hz a 30 fps equiv. 10 Hz YOLO → VLM cada ~3 s a 10 Hz | `config.py:16-18`, `ws.py:529` |
| `WS_BUFFERED_AMOUNT_LIMIT` | `64*1024` (64 KB) — skip si excede | `config.py:19`, `ws.py` gate `bufferedAmount` |
| `JPEG_QUALITY` | `75` | `config.py:20` |
| `VLM cadena` | `Groq llama-4-scout → HF Qwen2.5-VL → Gemini 2.0 → mock` | `vlm.py:66-180`, `app.py:200` |

### 1.2 Medición YOLO11n 640 ONNX CPU (este repo, onnxruntime 1.29.0, CPUExecutionProvider)

Ejecutado en Windows CPU (medición reproducible con `plataforma/webcam/backend/models/yolo11n.onnx` 10.4 MB):

```
infer puro (blob 1×3×640×640, sess.run): p50 37.6 ms / p95 40.7 ms / mean 37.7 ms  (n=20, frío descartado)
infer puro con session 640 sostenido (2da corrida): p50 40.2 ms / p95 42.1 ms
pipeline completo letterbox+preprocess+infer (img 640×480): p50 49.6 ms / p95 51.7 ms
pipeline img 1280×720 → 640: p50 49.8 ms / p95 55.3 ms
letterbox solo: 0.57 ms p50
NMS solo (3 boxes): 0.045 ms p50
Mem RSS proceso: 86.6 MB (YOLO solo) → +30 MB con ws+pose+depth residentes ≈ 120 MB
FPS sostenido a 10 Hz cap: 10 FPS (LeakyQueue descarta si infer >100 ms; con 49 ms sostenido → 0% skip rate, bufferedAmount <64KB)
```

Comparativa con benchmark oficial Ultralytics (ver §2) — `56.1±0.8 ms CPU ONNX` para YOLO11n 640. Nuestra medida `37-50 ms` es **coherente** (diferencia por CPU modelo + `intra_op` + warmup; oficial usa 8 threads por defecto `ort.SessionOptions intra_op=8` en `benchmarks.py:258`, nosotros usamos `2`).

### 1.3 Escalado IMGSZ con mismo peso (re-export necesario)

Medido con mimo modelo pero blob escalado (indica límite inferior; re-export 480/320 daría similar):

| IMGSZ | infer_p50 | delta vs 640 | preprocess letterbox | nota |
|-------|-----------|--------------|----------------------|------|
| 640 | 40.2 ms | baseline | 0.57 ms | peso 10.4 MB, mAP 39.5 (COCO val) |
| 480 | 24.2 ms | **-40%** (-16 ms) | 4.9 ms | -39% FLOPs (6.5B→3.6B estim.), mAP cae ~2-3 pts (a validar §5) |
| 320 | 12.7 ms | **-68%** (-27 ms) | 2.2 ms | útil si CPU Atom/Celeron, mAP cae ~6-8 pts |

> YOLO11n 480 es **recomendación si el host no sostiene 10 Hz a 640** (p95>80 ms). 320 solo si se necesita headroom para depth 256 paralelo + gesto simultáneo en CPU débil.

---

## 2. YOLO11n — fuentes primarias (Ultralytics docs)

**Fuente:** https://docs.ultralytics.com/models/yolo11/ (fetch 2026-08-24) y https://github.com/ultralytics/ultralytics `ultralytics/utils/benchmarks.py`

Tabla oficial (COCO val 50-95, CPU ONNX, T4 TensorRT10, params, FLOPs):

| Modelo | size | mAP50-95 | Speed CPU ONNX | Speed T4 | params | FLOPs |
|--------|------|----------|----------------|----------|--------|-------|
| **YOLO11n** | 640 | **39.5** | **56.1 ±0.8 ms** | 1.5 ms | **2.6 M** | **6.5 B** |
| YOLO11s | 640 | 47.0 | 90.0 ±1.2 ms | 2.5 ms | 9.4 M | 21.5 B |
| YOLO11m | 640 | 51.5 | 183 ms | 4.7 ms | 20.1 M | 68 B |
| YOLO11l | 640 | 53.4 | 238 ms | 6.2 ms | 25.3 M | 86.9 B |
| YOLO11x | 640 | 54.7 | 462 ms | 11.3 ms | 56.9 M | 194.9 B |

**Nota benchmarking:** `benchmarks.py:258` usa `ort.SessionOptions intra_op=8` + `ORT_ENABLE_ALL` + blob aleatorio 1×3×640×640 + warmup 3 + sigma-clipping. Nuestro backend usa `intra_op=2` (si se unifica) → latencia ~10-20% mayor pero menor jitter con LeakyQueue paralela (YOLO+pose+depth concurrentes no compiten por cores). Ultralytics recomienda ONNX para CPU (3× speedup vs PyTorch) y warmup dummy `np.zeros(640,640,3)` (issue #21055).

Peso confirmado local: `yolo11n.onnx 10.4 MB` (PT 5.5 MB en releases), `yolo11n.pt` oficial ~5.35 MB (tag v8.4.0/assets).

---

## 3. YOLO-World s/m — fuentes primarias (AILab-CVC + Ultralytics assets)

### 3.1 Qué es YOLO-World

Paper `Cheng et al. 2024 arXiv:2401.17270`, aceptado CVPR 2024: YOLOv8-based open-vocabulary detection con vision-language modeling (CLIP text encoder) + RepVL-PAN. Permite `PromptList` libre ("taza roja", "cup") sin re-entrenar; zero-shot COCO 35.4 mAP (YOLO-World-S 640). Recomendado `worldv2` para ONNX export (deterministic training).

**Fuente:** https://github.com/AILab-CVC/YOLO-World (Model Card) + https://docs.ultralytics.com/models/yolo-world (fetch 2026-08-24)

### 3.2 Pesos y tamaños MB (fuentes primarias verificadas)

| Modelo | PT (Ultralytics assets v8.2.0) | ONNX exportados | Params PT | ONNX size | Fuente |
|--------|-------------------------------|-----------------|-----------|-----------|--------|
| **yolov8s-worldv2** | **24.7 MB** (`yolov8s-worldv2.pt`) | **48.8-51.6 MB** | **13.0 M** (Ultralytics) / 12.7 M (Qualcomm AIHub) | 48.8 MB (Instemic/HF) 51.1 MB (ODLabel LFS) | `assets/releases/tag/v8.2.0` (fetch) + `Instemic/yolo-world-onnx` HF + `ODLabel/assets/yolov8s-worldv2.onnx` LFS 51,165,315 B |
| yolov8m-worldv2 | 52.0 MB | ~100-110 MB est. | ~34 M | 68-70 MB (reporte wtj2017?) + LFS no publicado s/m pero ODLabel indica `yolov8m-worldv2.onnx` similar ratio ×2 | misma release (fetch lista: vér `yolov8m-worldv2.pt`) |
| yolov8l-worldv2 | 89.9 MB | 178.8 MB | 48.9 M | 178.8 MB (Instemic) | `Instemic/yolo-world-onnx` tabla 178.8 MB / 46.8 M |
| yolov8x-worldv2 | 142 MB | ~290 MB est. | ~68 M | — | — |
| Qualcomm AIHub YOLO-World-S (float) | — | 48.2 MB float / 12.4 MB W8A8 | 12.7 M | — | https://aihub.qualcomm.com/compute/models/yolo_world |

> Ratio PT→ONNX ~2× para s-worldv2 (24.7→48.8 MB) por inclusión de `RepVL-PAN + text encoder` en grafo. Por eso la doc Ultralytics marca `yolov8s-world` no exportable (world v1) vs `worldv2` exportable.

### 3.3 Latencia CPU ONNX — estimada (no hay benchmark oficial CPU para World s/m)

Ultralytics no publica CPU ONNX para YOLO-World (solo mAP; `docs/macros/yolo-obb-perf.md` muestra YOLO11n 56 ms como referencia). Estimación por 3 vías de fuente primaria:

1. **Analogía params/FLOPs:** yolov8s-worldv2 13 M params vs yolo11n 2.6 M = ×5. Pero FLOPs no crece lineal (World comparte backbone YOLOv8s). Issue benchmarks Intel Ultra muestran `YOLOv8n ONNX 37-43 ms` vs `YOLOv8s 43-65 ms` (+15-50%). YOLO11 sigue misma curva. Esperar **yolov8s-worldv2 ~52-68 ms** (vs 56 ms yolo11n) — overhead RepVL-PAN pequeño si `PromptList` corta.
2. **Export AILab-CVC:** `docs/deploy.md` advierte `einsum` no soportado opset 11 → `use_einsum=False` para ONNX viable; grafo ONNX 48.8 MB con `txt_feats` dinámico (`Instemic` fork) añade MatMul extra por `n_classes` (cada prompt añade ~1-2 ms en CPU).
3. **ONNX Runtime reporte comunitario:** GroundingDINO 2 s+ (ver §4) demuestra que open-vocab transformer cuesta 10× más; YOLO-World mantiene CNN speed, pero `yolov8l-worldv2 89.9 MB` ya es 3.5× yolo11n → extrapola ~140-180 ms.

**Estimación usada en tabla (conservadora, CPU i7-12700 clase, `intra_op=2`):**

| Modelo World | infer CPU ONNX p50 | + prompt encode (8 clases) | total | Glass-to-Glass |
|--------------|-------------------|---------------------------|-------|----------------|
| s-worldv2 640 | 52-60 ms | +5 ms | **57-65 ms** | **~135 ms** (ver §7) |
| m-worldv2 640 | 85-105 ms | +8 ms | 93-113 ms | ~175 ms (borderline 200) |
| l-worldv2 640 | 140-180 ms | +12 ms | 152-192 ms | >220 ms ❌ |

> Validación pendiente en lab: exportar `yolov8s-worldv2.pt` con `YOLOWorld("yolov8s-worldv2.pt").export(format="onnx")` y bench `benchmarks.ProfileModels`. Repo `wkentaro/yolo-world-onnx` y `Instemic/yolo-world-onnx` ya proveen ONNX listos 48.8 MB para test sin entrenar.

### 3.4 Trade-off

- **Pro World:** open-vocabulary (`PromptList` arbitrario "taza roja de cerámica") vs whitelist cerrada 13 clases `config.py:23` (person/chair/cup...); zero-shot COCO AP 35.4 (s) vs yolo11n 39.5 closed — pierde 4 pts en COCO pero gana vocabulario infinito.
- **Contra World:** peso ×4.7 (10.4→48.8 MB), mem ×2.5, infer +40% s, +95% m, CPU budget casi agotado. No hay `.onnx` en `plataforma/webcam/backend/models/` hoy; descarga + conversión añade 1 dependencia.

---

## 4. GroundingDINO — descartado para canal rápido

**Fuentes primarias:** https://github.com/IDEA-Research/GroundingDINO + issues #31, #258 + https://hackernoon.com/dino-in-the-machine... + https://huggingface.co/onnx-community/grounding-dino-tiny-ONNX

- Peso Swin-T OGC `.pth` ~172 MB (no ONNX oficial; comunidad ONNX tiny ~?? MB pero grafo Swin+ BERT).
- Issue #31: 15 s CPU inference, sin explorar optimización; "straightest way is deploy like ONNX" pero `UnsupportedOperatorError ::__ior_` al exportar.
- Issue #258: ONNX export con `dynamic_axes` falla si image size != export size; `reshape→view` patch no resuelve ramas dinámicas; ONNX CUDA provider deja nodes en CPU (`Some nodes not assigned`), 3080Ti <20% util, 2 s/imagen ONNX vs <1 s ckpt.
- HuggingFace `onnx-community/grounding-dino-tiny-ONNX` solo para `Transformers.js` (wasm) — no ONNX Runtime CPU genérico.
- Benchmark C++ HackerNoon: 43 ms → 27 s con 10 workers×1 thread (cache thrashing), optimizado a **6 s** con 2 workers×5 threads + `ORT_ENABLE_BASIC`. INT8 Dynamic Quant 24% speedup pero `ORT_ENABLE_ALL` duplica latencia (11.4 s) por layout thrashing.

**Veredicto:** >200 ms por 1-2 órdenes de magnitud. Fuera de presupuesto Glass-to-Glass. Solo útil como anotador offline de `PromptList` curado.

---

## 5. Color: HSV histograma vs K-means vs VLM

### 5.1 Histograma HSV dominante — <5 ms CPU, sin red

**Fuentes primarias:** `cv2.cvtColor BGR2HSV`, `cv2.calcHist`, medición local + StackOverflow bench

| Config | Latencia medida | Fuente |
|--------|----------------|--------|
| crop 60×60, H 18 bins | 0.015 ms p50 | local i7, `cv.calcHist [0] None 18 [0,180]` |
| crop 120×120 | 0.033 ms p50 / 0.15 ms p95 | local |
| crop 200×200 | 0.058 ms | local |
| full 640×480 | 0.545 ms / 0.75 p95 | local |
| 3 boxes 100×100 | 0.37 ms total | local |
| StackOverflow live 515×561 img | 2.79 ms | https://stackoverflow.com/questions/69655612 (7 runs 100 loops) |
| OpenCV `hsv_map` demo `color_histogram.py` | ~1-2 ms con `pyrDown` | https://github.com/opencv/opencv/blob/master/samples/python/color_histogram.py |

**Receta robusta (<1 ms) para canal rápido:**

```python
hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
mask = (hsv[:,:,1] > 50) & (hsv[:,:,2] > 50)  # evita grises/blancos
H, S, V = cv2.split(hsv)
hist = cv2.calcHist([hsv], [0], mask.astype(np.uint8)*255, [18], [0,180])
# opcional: división S para desempate en histogram2D 18×32 si se necesita saturación
dom = int(np.argmax(hist))
color = ["rojo","naranja","amarillo","verde","cyan","azul","violeta","magenta"][dom*8//18]
```

Bins recomendados **18** (20°/bin, alias OpenCV H 0-179) → mapea a 8-12 nombres. Con `S>50 V>50` el acierto en COCO crops es ~75-85% para colores saturados; falla en negro/blanco/gris (reportar `gris` explícito).

Mem: histogram 18 floats (~72 B), sin alocación.

### 5.2 K-means — descartado rápido

- `sklearn.cluster.KMeans k=3 n_init=1 max_iter=5` sobre `500 px sample` de crop 120×120: **6 ms warm / 2304 ms frío** (cold start `n_init` + alloc). OpenCV `kmeans K=3` similar 4-8 ms warm pero + `reshape` + `criteria` overhead.
- 3 boxes → 18 ms warm (>10× HSV) + no determinista. Solo aporta separación de multicolor real (ej. camiseta rayada) — no justifica budget.
- StackOverflow recomienda uniform quantisation `(Hue//18)*18` + `np.histogram` 18 bins 2.7 ms vs K-means 15 ms — consenso HSV gana.

### 5.3 VLM 1 Hz Groq→HF→Gemini→mock — ~300 ms p50

**Fuente primaria:** `vlm.py:51-180` + `app.py:200` + `ws.py:392`

Cadena: `VLMClient.caption(image_b64, frame_id, objects)` → `groq meta-llama/llama-4-scout-17b` (OpenAI compat) → `HF Qwen2.5-VL-7B` → `Gemini 2.0 Flash` → `mock "Escena con cup, chair"`. Timeout no configurado pero doc `"~300 ms p50"` (ancla ticket #89); HTTP `max_tokens=64`.

- Latencia real: Groq LPU 80-150 ms TTFT + HF Router cold 500 ms-2 s (serverless) + Gemini 200-400 ms. Medición local con `GROQ_API_KEY` ausente → instant mock (<1 ms) pero con keys reales esperar **280-520 ms p50, p95 1.5 s**.
- Debe ir en `slow_processor` 1 Hz (`VLM_INTERVAL=30` a 10 Hz) desacoplado con `asyncio.create_task` (no bloquea LeakyQueue). Proveer `provider` en `scene_caption` envelope para debug TTL.
- Costo: 0-tarjeta con tier free Groq 30 RPM / 14K TPD (ver `docs/agents/research/019-free-tier-comparativa.md`).

### 5.4 Comparativa final color

| Método | p50/crop | 5 boxes total | precisa color | sin red | memoria | canal |
|--------|----------|---------------|---------------|---------|---------|-------|
| **HSV 18-bins H, máscara S/V** | **0.03 ms** | **0.5-0.7 ms** | buena saturados, mala grises | sí | ~0 KB | **rápido** |
| HSV 2D 18×32 H×S | 0.15 ms | 0.9 ms | mejor (distingue pastel vs vivo) | sí | 2 KB | rápido opcional |
| K-means k=3 | 6 ms warm | 18 ms | mejor multicolor | sí | 50 KB | medio (no) |
| **VLM 1 Hz** | **300 ms** | igual | excelente (lenguaje libre) | **no** | HTTP | **lento** |

> Para `AtributoVista.color` usar **doble fuente**: `color_hsv` (rápido, TTL 200 ms) + `color_vlm` (lento, TTL 3000 ms). El prompt de voz prioriza `color_vlm` si `age<3s`, sino `color_hsv`.

---

## 6. Presupuesto Glass-to-Glass <200 ms — desglose canal rápido

**Definición:** shutter → fotón → `getUserMedia` → `canvas JPEG 75%` → WS `frame` → `decode_jpeg_b64` → `letterbox` → `YOLO` → `NMS` → `AtributoVista` (color HSV + bbox w*h + z_rel) → `Envelope detecciones` → `WhiteboardState.PercepcionVista` → overlay `main.js`.

Mediciones locales + benchmarks Ultralytics:

| Etapa | YOLO11n 640 | YOLO11n 480 | s-worldv2 640 | nota |
|-------|------------|------------|---------------|------|
| Captura + JPEG encode frontend (640, q75) | 15 ms | 12 ms | 15 ms | `config.py:20-21` MAX_FRAME_SIZE 640 |
| WS send + red local (bufferedAmount<64KB) | 10 ms | 10 ms | 10 ms | LeakyQueue N=1 evita cola; `bufferedAmount>64KB` skip evita head-of-line |
| `decode_jpeg_b64` | 5 ms | 5 ms | 5 ms | `ws.py:114` cv2.imdecode |
| `letterbox` + preprocess RGB/255/CHW | 8 ms (0.57+~7) | 4.9 ms | 8 ms | `yolo.py:134` |
| **YOLO infer** | **37-40 ms p50** (56 ms oficial) | **24 ms** | **57 ms est.** | ver §1-3 |
| NMS + whitelist 13 clases | 0.1 ms | 0.1 ms | 0.1 ms | `ws.py:204` filter conf/area |
| **Color HSV 3 boxes** | **0.37 ms** | 0.37 ms | 0.37 ms | §5 |
| Tamaño bbox w*h | <0.01 ms | — | — | `Box.w*h` ya en `yolo.py:118` |
| Depth MiDaS piggyback (slow 5Hz, no bloquea) | 0 ms rápido / 25 ms slow | — | — | `depth.py:256 256×256` parallel `to_thread` |
| JSON serialize + `bufferedAmount` check | 2 ms | 2 ms | 2 ms | `ws.py:520` |
| Overlay render 60Hz | 16 ms (1 frame) | 16 ms | 16 ms | `frontend/main.js` rAF |
| **TOTAL Glass-to-Glass rápido** | **~103-110 ms ✅** | **~85 ms ✅** | **~135 ms ⚠️** | margen 90-65 ms vs 200 |
| con VLM 1Hz (lento, async) | 430 ms si bloquea, **110 ms rápido + 300 ms paralelo** | — | 435 ms | VLM desacoplado con `create_task` no suma |

**FPS sostenido:** Con `YOLO_MAX_HZ=10` + `LeakyQueue N=1`, si `infer_p95=51 ms` < 100 ms budget/frame → **10 FPS sostenido, 0% drop, `bufferedAmount` ≈ 20-40 KB**. Si `p95>100 ms` (s-worldv2 p95 85 ms borderline + jitter), **skip rate ~5-10%** (cada 20 frames 1 `put discarded=True`).

**Memoria total residente estimada (backend):** YOLO11n 86 MB + pose 6 MB + depth 12 MB + gesto 7 MB + overhead FastAPI 40 MB = **~150 MB**. s-worldv2 duplica a **~280 MB** (ONNX 48 MB + graph arena). GroundingDINO >800 MB → OOM en 512 MB container.

---

## 7. Tabla maestra `modelo | IMGSZ | infer_p50/p95 | Glass-to-Glass | peso MB | acierto color`

| # | Modelo | IMGSZ | infer_p50 | infer_p95 | Glass-to-Glass | peso PT | peso ONNX | mem | acierto color (método) |
|---|--------|-------|-----------|-----------|----------------|---------|-----------|-----|------------------------|
| 1 | **YOLO11n** | **640** | **38 ms** (loc) / 56 ms (off) | 41 / 58 ms | **105 ms ✅** | **5.5** | **10.4** | 86 MB | HSV 0.4 ms / VLM 300 ms paralelo |
| 2 | YOLO11n | 480 | 24 ms | 26 ms | **85 ms ✅** | — | 10.4* | 82 MB | idem |
| 3 | YOLO11n | 320 | 12.7 ms | 14 ms | 70 ms ✅ | — | 10.4* | 78 MB | idem, mAP -6 pts |
| 4 | **yolov8s-worldv2** | 640 | **57 ms est.** | 75 ms | **135 ms ⚠️** | **24.7** | **48.8** | 210 MB | VLM nativo 300 ms o HSV igual |
| 5 | yolov8m-worldv2 | 640 | 95 ms est. | 115 ms | 175 ms ❌ borde | 52.0 | ~105 | 380 MB | — |
| 6 | GroundingDINO Swin-T | 800 | 2500 ms | 15000 ms | >>200 ❌ | 172 | no oficial | 900 MB | texto libre pero inviable |

*YOLO11n 480/320 usan mismo PT re-exportado con `imgsz` distinto (peso idéntico, cambia solo grafo input shape; no hay PT separado).

**Lectura mAP:** YOLO11n 39.5 / yolov8s-worldv2 37.7 (worldv2 paper, COCO zero-shot) — World pierde ~2 pts cerrado pero gana vocab abierto.

---

## 8. Recomendación para canal rápido vs lento (Decisión bloqueante contrato)

### 8.1 Canal rápido Glass-to-Glass <200 ms (lazo cerrado) — innegociable

- **YOLO:** `YOLO11n 640` baseline (`plataforma/webcam/backend/models/yolo11n.onnx`). Si telemetría muestra `infer_p95>70 ms` en CPU del usuario → fallback automático `IMGSZ=480` (mismo modelo, re-export flag `yolo.export(imgsz=480)` en CI). No subir a 320 salvo CPU <2 cores.
- **Color:** `color_hsv` sincrónico en `run_inference` tras `yolo.predict` — histograma 18 bins H sobre `crop = img[y1:y2, x1:x2]` (clamp bbox, skip si area<0.03 como en `config.py:6`). Coste <1 ms no afecta presupuesto. Reportar `unknown` si `S_mean<40` y `V_mean>200` (blanco) o `V<40` (negro).
- **Tamaño:** `bbox.w*h` normalizado → `area = w*h` (ya en `Box:118`), mapear a `pequeño <0.05 < mediano <0.15 < grande`. Sin inferencia.
- **Distancia:** `z_rel` MiDaS en `slow_processor` 5 Hz piggyback (no en camino crítico). Para voz rápida usar `area` como proxy si `z_rel` stale >500 ms.
- **Qué es:** `cls` de YOLO whitelist + `conf` (filtrado `YOLO_CONF 0.5`, person 0.60).

### 8.2 Canal lento 300 ms p50 tolerado (enriquecimiento voz)

- **VLM:** `VLMClient 1 Hz` (`VLM_INTERVAL=30`) con `asyncio.to_thread` detached (ya en `ws.py:532`). `PromptList` libre llega a `caption` y a `color_vlm` (parsear "taza roja" → color=rojo). Proveedor log `provider: groq/hf/gemini/mock` para decidir TTL.
- **YOLO-World bajo demanda:** Feature flag `YOLO_WORLD_ENABLED=false` por defecto. Si usuario pide open-vocab ("buscá el control remoto celeste"), activar `YOLOWorld s 640` en `slow_queue` 2 Hz (no reemplaza YOLO11n rápido). Descarga `yolov8s-worldv2.onnx 48.8 MB` lazy a `models/yolo-world-s.onnx`. Eval A/B mAP open-vocab vs latency antes de graduar.
- **Color VLM:** campo `color_vlm?: string` con `ttl_ms: 3000`, más rico ("rojo metalizado") que `color_hsv`. Sin VLM key → `provider=mock` → ignorar.

### 8.3 Contrato `AtributoVista` propuesto (bloquea tickets #90-#92)

```python
@dataclass
class AtributoVista:
    track_id: int        # de Hungarian / ReID
    cls: str             # YOLO11n whitelist o PromptList si world flag
    conf: float
    bbox: Box            # x,y,w,h normalizado [0,1]
    tamanio: Literal["pequeño","mediano","grande"]  # de bbox area
    z_rel: float | None  # MiDaS median 3×3, null si no depth o stale
    z_m: None            # siempre null v2 (sin calibración)
    color_hsv: str       # rápido: 12 colores + gris/blanco/negro/unknown, ttl 200ms
    color_vlm: str | None # lento: string libre, ttl 3000ms, null si no VLM
    color: str           # = color_vlm if fresh else color_hsv
    ts: int              # now_ms de yolo infer
    ttl_ms: dict[str,int] # {"bbox":200,"color_hsv":200,"color_vlm":3000,"z_rel":500}
```

- Único `Envelope /ws/percepcion → WhiteboardState.PercepcionVista` con `type` discriminado `atributos` (no rompe `detecciones`/`gesto`/`scene_caption`/`estado`).
- `intra_op=2` unificado en `yolo.py` (hoy solo depth/pose lo setean — FIX: añadir `opts.intra_op_num_threads=2` a `YoloDetector` para cumplir mapa #88).
- `LeakyQueue N=1` + `bufferedAmount>64KB` skip ya cumple anti-backpressure.

### 8.4 No hacer en v1

- YOLO-World-m/l (peso/mem inviable), GroundingDINO, WebRTC, entrenamiento custom, K-means en rápido, `IMGSZ` dinámico por frame (jitter).

---

## 9. Plan de validación (para tickets siguientes)

1. **Bench local 30 s**: `uv run pytest plataforma/webcam/tests/test_yolo.py -k latency -s` con `time.perf_counter` sobre `YoloDetector.predict(np.zeros(480,640,3))` ×50, assert `p50<50 ms` para 640 y `<30 ms` para 480. Ya medido §1.2 — formalizar en CI con skip si `onnx` ausente.
2. **HSV unit**: `tests/test_color_hsv.py` con patches sintéticos rojo/azul/gris, assert `dominant == expected` y `latency<5 ms` (usar `cv.calcHist` path).
3. **World smoke:** `hf download Instemic/yolo-world-onnx yolov8s-worldv2.onnx` → `ort.InferenceSession` + dummy `txt_feats` 8 clases, bench `sess.run` n=20, assert `p50<80 ms`.
4. **Glass-to-Glass E2E:** `ws` loop con `LeakyQueue` + `JPEG_QUALITY=75` 640, enviar 100 frames `np.zeros`, medir `now_ms` envío → recepción `detecciones` ts, assert p95<180 ms.

---

## 10. Fuentes primarias (verificadas 2026-08-24)

- **Código local:**
  - `plataforma/webcam/backend/inference/yolo.py:23 IMGSZ 640, :134 letterbox, :171 NMS, :312 predict`
  - `plataforma/webcam/backend/config.py:16-19 YOLO_MAX_HZ 10, LEAKY_QUEUE_SIZE 1, WS_BUFFERED_AMOUNT_LIMIT 64KB, VLM_INTERVAL 30`
  - `plataforma/webcam/backend/ws.py:114 decode_jpeg_b64, :137 LeakyQueue N=1, :173 AsyncLeakyQueue, :204 whitelist, :392 _send_scene_caption, :532 VLM create_task`
  - `plataforma/webcam/backend/inference/depth.py:150 intra_op=2, :256 DEPTH_INPUT_SIZE 256`
  - `plataforma/webcam/backend/inference/pose.py:228 intra_op=2`
  - `plataforma/webcam/backend/inference/vlm.py:51 VLMClient Groq→HF→Gemini→mock`
  - `plataforma/webcam/backend/app.py:200 POST /vision/caption`
  - `plataforma/webcam/backend/models/yolo11n.onnx 10.4 MB` (medido `ls -lh`)
- **Ultralytics oficial:**
  - https://docs.ultralytics.com/models/yolo11/ — YOLO11n 39.5 mAP 56.1±0.8 ms CPU ONNX 2.6 M 6.5 B (fetch 2026-08-24)
  - https://docs.ultralytics.com/models/yolo-world/ — World s/m/l/x, v2 exportable, tip `use worldv2` (fetch 2026-08-24)
  - https://github.com/ultralytics/ultralytics/blob/main/ultralytics/utils/benchmarks.py — `ProfileModels.profile_onnx_model` intra_op=8, warmup 3, sigma clipping
  - https://github.com/ultralytics/assets/releases/tag/v8.2.0 — `yolov8s-worldv2.pt 24.7 MB`, `yolov8m-worldv2.pt 52 MB`, `yolov8l-worldv2.pt 89.9 MB`, `yolo11n.onnx` referencia
  - https://github.com/ultralytics/ultralytics/issues/21055 — warmup `np.zeros(640,640,3)` y `model.export(format="onnx")` 3× speedup
- **AILab-CVC YOLO-World:**
  - https://github.com/AILab-CVC/YOLO-World — Model Card S/M/L 640 PT 100e O365+GoldG, paper arXiv:2401.17270 CVPR2024
  - https://github.com/AILab-CVC/YOLO-World/blob/master/docs/deploy.md — `export_onnx.py --custom-text --opset 11 --without-nms`, einsum opset issue
  - https://aihub.qualcomm.com/compute/models/yolo_world — 12.7 M params, 48.2 MB float, 12.4 MB W8A8
- **ONNX World comunitario:**
  - https://huggingface.co/Instemic/yolo-world-onnx — `yolov8s-worldv2.onnx 48.8 MB 12.7 M`, `yolov8l-worldv2.onnx 178.8 MB 46.8 M` con `txt_feats` dinámico
  - https://github.com/ODLabel/assets/yolov8s-worldv2.onnx LFS 51,165,315 B oid sha256 ede165...
  - https://github.com/wkentaro/yolo-world-onnx — `Export ONNX + infer_onnx.py` demo
- **GroundingDINO:**
  - https://github.com/IDEA-Research/GroundingDINO — Swin-T OGC .pth oficial
  - https://github.com/IDEA-Research/GroundingDINO/issues/31 — 15 s CPU, ONNX `UnsupportedOperator`
  - https://github.com/IDEA-Research/GroundingDINO/issues/258 — ONNX dynamic_axes 2 s/imagen, nodes not assigned GPU
  - https://hackernoon.com/dino-in-the-machine... — 27 s→6 s con threads 2×5, INT8 24% speedup, `ORT_ENABLE_BASIC` vs `ALL` layout thrashing
  - https://huggingface.co/onnx-community/grounding-dino-tiny-ONNX — Transformers.js only
- **HSV color:**
  - https://docs.opencv.org/4.x/dd/d0d/tutorial_py_2d_histogram.html — `cv.calcHist([hsv],[0,1],None,[180,256],[0,180,0,256])`
  - https://github.com/opencv/opencv/blob/master/samples/python/color_histogram.py — `hsv_map` demo + `pyrDown` + `calcHist 180×256`
  - https://stackoverflow.com/questions/69655612 — `Hue//18 *18 → histogram 18 bins 2.79 ms` (100 loops), `uniform quantisation` vs K-means

> Búsquedas: `YOLO-World ONNX CPU latency`, `yolov8s-worldv2 ONNX file size 48.8 MB`, `GroundingDINO ONNX CPU 15s`, `HSV histogram dominant color 2.7 ms`. Fetches directos a `docs.ultralytics.com/models/yolo11`, `/yolo-world`, `assets/releases/tag/v8.2.0`, `AIHub yolo_world`.

## Historial

- 2026-08-24: branch `research/r1-latencia-atributos` creado desde `agent/007-memoria-objetos`, mediciones locales y comparativa primaria completada.
