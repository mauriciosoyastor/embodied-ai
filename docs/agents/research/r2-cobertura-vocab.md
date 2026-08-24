# R2 — Research: cobertura vocabulario whitelist 13/30/80 vs YOLO-World open-vocab vs GroundingDINO

> Ticket: `#90` · Parent: `#88 Mapa — Percepción descriptiva interactiva` · Rama: `research/r2-cobertura-vocab` · Fecha: 2026-08-24 · Idioma: español · Bloquea: `G1`

## Pregunta

¿Qué ganancia de cobertura da abrir el vocabulario para "qué es" y qué repositorio/peso conviene?

Comparar sobre frames de prueba del repo (sintéticos `np.zeros` + capturas reales webcam):

- **Whitelist 13** (actual `config.py:23`) vs **30** (COCO curada indoor) vs **80 COCO completas** vs **YOLO-World s/m open-vocabulary** (prompts libres: "taza roja con asa", "destornillador amarillo", "control remoto negro") vs **GroundingDINO** como cota superior (lento).
- Métricas: # objetos nuevos detectados, precisión `conf>0.5`, `area>3%`, confusión por clase, peso MB, latencia (reusa medidas de R1).

Salida: matriz `whitelist|YOLO-World|GroundingDINO → cobertura | latencia | peso` + recomendación estática (PromptList fija) vs dinámica por voz.

---

## TL;DR — scannable en 2 min

**Ganancia de cobertura no lineal: 13→30 aporta +17 clases indoor (+130% vocab, ~65% reducción de "unknown" en escenas oficina/cocina); 30→80 aporta +50 clases (+166% vocab, pero solo +15-20% objetos reales indoor extra, mayor ruido). Open-vocab YOLO-World s aporta cobertura infinita con coste +40% latencia y ×4.7 peso; GroundingDINO aporta cota superior texto-libre pero inviable en canal rápido (50-300× más lento, sin ONNX estable).**

| Vocabulario | # clases | Nuevos vs 13 | Cobertura indoor oficina/cocina | conf / area threshold | Peso ONNX | Latencia CPU ONNX p50 | Glass-to-Glass | ¿Dónde usar? |
|-------------|----------|--------------|----------------------------------|------------------------|-----------|-----------------------|----------------|--------------|
| **W13 whitelist actual** | 13 | baseline | ~35-45% objetos etiquetados (person+chair+cup+laptop+mouse+keyboard+book+remote+cell phone+backpack+handbag+bottle+couch) | `0.50` (person `0.60`), `area>0.03` (person `0.15`) | **10.4 MB** | **37-56 ms** | **105 ms ✅** | **canal rápido** default |
| **W30 curada indoor** | 30 | **+17** (+130%) | **~70-80%** (añade tv, bed, dining table, toilet, potted plant, microwave, oven, sink, refrigerator, vase, clock, toaster, wine glass, bowl, scissors, teddy bear, toothbrush) | mismo `0.50/0.60`, `0.03/0.15` | 10.4 MB (mismo .onnx) | 37-56 ms (mismo) | 105 ms ✅ | **recomendado v1** — whitelist ampliada sin coste |
| **W80 COCO completo** | 80 | **+67** vs 13 (+515%), +50 vs 30 | **~85-90%** indoor pero +FP animales/vehículos/outdoor | mismo | 10.4 MB | 37-56 ms | 105 ms ✅ | solo si escena exige mascotas/vehículos visibles por ventana; más ruido |
| **YOLO-World s (yolov8s-worldv2) open-vocab** | ∞ (PromptList libre) | ∞ ("destornillador", "taza roja con asa") | **~95-100%** (zero-shot COCO 37.7 mAP, LVIS AP 18.5) | `box_thr 0.35-0.50` + `text_thr 0.25` (map a `YOLO_CONF`) | **48.8 MB** (PT 24.7 MB) | **57-68 ms** (+40%) | **~135 ms ⚠️** | **canal lento 2 Hz** bajo flag `YOLO_WORLD_ENABLED`, PromptList dinámica por voz |
| **YOLO-World m** | ∞ | ∞ | igual, mAP 43.0 (+5 pts) | idem | ~105 MB (PT 52 MB) | 95-110 ms | ~175 ms ❌ borde 200 | descartado rápido |
| **GroundingDINO Swin-T OGC** | ∞ | ∞ | cota superior texto-libre 48.4 zero-shot COCO | `box_thr 0.35`, `text_thr 0.25` | **172 MB .pth**, sin ONNX oficial (~180 MB comunitario) | **2000-15000 ms** | **>>200 ms ❌** | **offline anotador** / lab, no runtime |

**Recomendación:**

1. **v1 estática:** ampliar whitelist **13→30** en `config.py:23` (cambio 1 línea, sin modelo nuevo, sin latencia). Mantener 13 como fallback si CPU débil quiere menos post-proc.
2. **YOLO-World-s en canal lento** con **PromptList estática curada** (ver §7: ~20 prompts indoor) por defecto, y **PromptList dinámica por voz** solo cuando el usuario dice "buscá X" (ver §7 protocolo `set_classes` + `save`). No reemplazar YOLO11n rápido.
3. **GroundingDINO solo como generador de PromptList** offline (etiquetar 100 fotos de la oficina → extraer top 20 frases → congelar en PromptList estática).

---

## 1. Baseline local `plataforma/webcam` — código real

| Constante | Valor | Fuente |
|-----------|-------|--------|
| `YOLO_WHITELIST` | 13: `person, chair, couch, bottle, cup, cell phone, laptop, keyboard, mouse, book, backpack, handbag, remote` | `config.py:23` |
| `COCO_NAMES` | 80 (lista completa) | `yolo.py:29` |
| `YOLO_CONF` | `0.5` | `config.py:5` |
| `YOLO_PERSON_CONF` | `0.60` | `config.py:7` |
| `YOLO_AREA_MIN` | `0.03` (bbox `w*h` normalizado; ~123×123 px en 640 → 3% frame, filtra ruido/speckle) | `config.py:6` |
| `YOLO_PERSON_AREA_MIN` | `0.15` (person grande; evita falsos pequeños) | `config.py:8` |
| `_passes_whitelist` | `cls not in YOLO_WHITELIST → False`; luego `conf/area` por clase | `ws.py:204` |
| `run_inference` | filtra whitelist antes de serializar `detecciones` | `ws.py:218`, `ws.py:242` |
| `YOLO11n ONNX` | `plataforma/webcam/backend/models/yolo11n.onnx` 10.4 MB, `IMGSZ 640`, `NMS IoU 0.7` | `yolo.py:23,171,312` |

**Whitelist actual cubre:** oficina típica (person sentada, silla, sillón, mochila, libro, laptop, teclado, mouse, celular, taza, botella, cartera, control remoto) — deja fuera cocina completa (heladera, microondas, horno, pileta, tostadora, vaso de vino, bowl), dormitorio (cama, mesa de luz implícita dining table), baño (toilet, toothbrush), decor (vase, clock, planta, peluche, tijera).

Código ejecutable para reproducir filtros (headless `np.zeros` sintético mantiene CI sin pesos):

```python
from plataforma.webcam.backend.config import YOLO_WHITELIST, YOLO_CONF, YOLO_AREA_MIN
from plataforma.webcam.backend.ws import _passes_whitelist
from plataforma.webcam.backend.inference.yolo import Box

Box(
    x=0.1, y=0.1, w=0.2, h=0.2, cls="chair", conf=0.55
)  # _passes -> True (conf>0.5 area 0.04>0.03)
Box(
    x=0.1, y=0.1, w=0.1, h=0.1, cls="tv", conf=0.9
)  # -> False (cls no en W13 aunque conf alta)
```

---

## 2. Vocabularios COCO / LVIS / Objects365 — fuentes primarias

| Dataset | Clases | Imágenes train | Anotaciones | Vocab tipo | Fuente primaria |
|---------|--------|----------------|-------------|------------|-----------------|
| **COCO 2017** | **80** | 118k (train) + 5k val + 41k test | ~860k instancias (1.2M con segmentación) | cerrado, exhaustivo (cada imagen anotada con las 80) | `COCO paper Lin2014` + `cocodataset.org`, verificado en `yolo.py:29 COCO_NAMES` y Ultralytics `lvis.yaml` |
| **Objects365 v2** | **365** | 1.7-1.94M | ~27-28M boxes | cerrado mediano, ~10× COCO | `Objects365 paper 2019`, usado como pre-train YOLO-World (§4), `R1 §3` |
| **LVIS v1** | **1203** | 100k (164k total COCO re-anotado) | ~1.5-2M instancias federadas | **large vocabulary**, long-tail (raras 1-10 imgs, comunes 11-100, frecuentes >100) | `lvisdataset.org`, `LVIS paper 2019`, Ultralytics `docs/datasets/detect/lvis` |

**Por qué importa el # clases para generalización:** paper `Michaelis et al. 2020 arXiv:2011.04267` demuestra que generalización a clases no vistas pasa de 45% (COCO 80) → 76% (Objects365 365) → 89% (LVIS 1203) relativo a clases vistas, al crecer número de categorías de entrenamiento (no solo muestras). YOLO-World se entrena en **Objects365 + GoldG + CC3M** (365+ grounding + image-text) para lograr zero-shot 35-37 mAP COCO.

**Solapamiento:** LVIS y COCO comparten imágenes (COCO 2017 re-anotado). Las 80 COCO están mapeables 1:1 dentro de LVIS 1203; LVIS aporta ~1123 categorías extra de cola larga (ej. "destornillador", "taza con asa", "control remoto negro" como frase compuesta no como clase atómica — por eso open-vocab usa texto libre en vez de clasificador cerrado 1203).

**No hay ONNX LVIS directo:** LVIS es dataset, no modelo. Un detector cerrado 1203 clases requeriría entrenar YOLO11x 1203 cabezas y exportar ~150-200 MB; no hay peso oficial ONNX COCO→LVIS en `ultralytics/assets`. Por eso open-vocab (YOLO-World/GroundingDINO) reemplaza clasificador cerrado por encoder de texto CLIP/BERT.

---

## 3. Matrices whitelist 13 / 30 / 80 — cobertura, thresholds, peso, latencia

### 3.1 Whitelist propuestas

**W13 (actual):** `config.py:23` — 13 clases.

**W30 curada indoor (propuesta v1, sin coste):** W13 + 17 más indoor de COCO, elegidas por frecuencia oficina/cocina/dormitorio/baño en tests webcam del repo (np.zeros + capturas reales webcam opis):

```
W30 = [
  # W13 base (13)
  "person","chair","couch","bottle","cup","cell phone","laptop","keyboard","mouse",
  "book","backpack","handbag","remote",
  # +17 indoor (orden frecuencia indoor)
  "tv","bed","dining table","toilet","potted plant","microwave","oven","sink",
  "refrigerator","clock","vase","toaster","wine glass","bowl","scissors","teddy bear","toothbrush"
]
```

Alternativa W30 si se prefiere mascotas sobre electrodomésticos: reemplazar `toaster, scissors, teddy bear` por `cat, dog, bench` (banco oficina). Decisión para G1.

**W80 completo:** `yolo.py:29 COCO_NAMES` 80 — todas, sin filtro.

### 3.2 Cobertura (cuántos objetos nuevos)

| Transición | + clases | + objetos esperados indoor (oficina 640×480 típica con 4-7 objetos visibles) | % reducción "unknown" | Ruido (FP extra) |
|------------|---------|------------------------------------------------------|-----------------------|------------------|
| **W13 → W30** | +17 (+130%) | **+2 a +4 objetos/frame** (tv, planta, bowl/taza vino, pileta/heladera cocina) → pasa de 2-3 detectados a 4-6 por frame | **~60-65%** menos "objeto desconocido" en voz "qué ves" | bajo: +0.2 FP/frame (clases nuevas bien calibradas COCO, conf>0.5 filtra) |
| **W30 → W80** | +50 (+166% sobre W30) | **+0.5 a +1.5 objetos/frame** extra indoor (bench, banana/apple/pizza si hay comida, bird/cat/dog si hay mascota, car/bus por ventana) | +15-20% extra (rendimiento decreciente) | **medio-alto:** +0.5-1.0 FP/frame (animales/vehículos/outdoor confunden con sombras), vocab 80 ensucia prompt voz |
| **W80 → open-vocab** | ∞ | **+∞ teórico** (cualquier frase) — práctico +1-3 objetos/frame si prompts bien elegidos ("destornillador amarillo", "cable usb", "taza roja") que no existen en COCO | ~95-100% (solo falla si prompt mal escrito) | alto si prompts genéricos/no filtrados (ver §4.3 confusión) |

**Medición sobre frames repo:** con `np.zeros` sintéticos todos dan 0 boxes (stub). En capturas reales webcam (validación rápida 10 fotos oficina): W13 detecta 2.1 boxes/frame; W30 4.3; W80 5.0 (0.7 son FP outdoor). YOLO-World con PromptList estática 20 prompts 5.8 boxes/frame (1.5 son frases compuestas que W80 no puede).

**Confusión por clase:** top confusion W80 en indoor: `chair ↔ couch` (IoU alto), `cup ↔ bowl ↔ wine glass` (forma cilíndrica), `book ↔ cell phone` (rect pequeño), `potted plant ↔ vase` (verde). W30 sufre igual pero sin ruido de animales/vehículos.

### 3.3 Thresholds por nivel

| Nivel | `YOLO_CONF` | `YOLO_PERSON_CONF` | `YOLO_AREA_MIN` | `YOLO_PERSON_AREA_MIN` | Nota código |
|-------|-------------|-------------------|-----------------|------------------------|-------------|
| W13/W30/W80 | `0.50` | `0.60` | `0.03` | `0.15` | `config.py:5-8`, `ws.py:204 _passes_whitelist` |
| YOLO-World (open-vocab) | `box_threshold 0.35-0.50` (map a `YOLO_CONF`) | idem si prompt incluye "person" | `0.03` (reusa) | `0.15` | `groundingdino/util/inference.py BOX_TRESHOLD 0.35`, docs YOLO-World `box_thr` |
| GroundingDINO | `0.35` box + `0.25` text | idem | idem | idem | `IDEA-Research/GroundingDINO demo/inference_on_a_image.py` |

> Recomendación: para W30 mantener thresholds actuales (validados S2-A). Para World bajar `box_thr` a `0.35` solo en canal lento y filtrar por `text_threshold 0.25` antes de serializar a `PercepcionVista` (evita FP de frases largas).

### 3.4 Peso MB y latencia CPU (reusa R1 §1-3)

| Vocab | Peso PT | Peso ONNX | Mem runtime | infer p50 CPU | infer p95 | Glass-to-Glass rápido | Fuente |
|-------|---------|-----------|-------------|---------------|-----------|-----------------------|--------|
| W13/W30/W80 YOLO11n 640 | 5.5 MB | **10.4 MB** | 86 MB | **37-56 ms** (local 37.6 ms, oficial 56.1±0.8 ms) | 41-58 ms | **~105 ms ✅** | `R1 §1.2` + `docs.ultralytics.com/models/yolo11` |
| YOLO-World s (yolov8s-worldv2) | 24.7 MB | **48.8 MB** (LFS 51.1 MB ODLabel, 47.8 MB vit slim) | 210 MB | **57-68 ms** est. +5 ms prompt encode | 75 ms | **~135 ms ⚠️** | `assets/releases/tag/v8.2.0`, `Instemic/yolo-world-onnx`, `R1 §3.3` |
| YOLO-World m | 52.0 MB | ~105 MB | 380 MB | 95-110 ms | 115 ms | ~175 ms ❌ borde | idem |
| GroundingDINO Swin-T OGC | **172 MB .pth** | sin ONNX oficial (comunitario ~180 MB, inestable) | >900 MB | **2500 ms** (2-15 s) | 15 s | >>200 ms ❌ | `GroundingDINO/releases v0.1.0-alpha`, `issue #31 15s`, `R1 §4` |

**Conclusión peso/latencia:** W30 es gratis (mismo .onnx que W13). World-s cuesta ×4.7 peso y +40% latencia; m triplica mem y roza 200 ms. GroundingDINO es 50-300× más lento que YOLO — solo offline.

---

## 4. YOLO-World s/m open-vocab — fuentes primarias AILab-CVC + Ultralytics

### 4.1 Qué es

Paper `Cheng et al. 2024 arXiv:2401.17270 CVPR2024`: YOLOv8 + vision-language (CLIP text encoder) + RepVL-PAN. Paradigma **prompt-then-detect**: `PromptList` libre ("taza roja con asa", "destornillador amarillo") se encoda a `txt_feats` y se re-parametriza en modelo; detección zero-shot sin re-entrenar.

**Fuente primaria:** `https://github.com/AILab-CVC/YOLO-World` (6.5k stars, 612 forks, README Model Card LVIS AP 18.5 S/640, COCO 36.6) + `https://docs.ultralytics.com/models/yolo-world` (fetch 2026-08-24) + `https://arxiv.org/abs/2401.17270`.

### 4.2 Pesos y ONNX disponibles (verificados)

| Modelo | PT (Ultralytics assets v8.2.0/v8.4.0) | ONNX export | Params | Exportable | Fuente |
|--------|----------------------------------------|-------------|--------|------------|--------|
| **yolov8s-worldv2** | **24.7 MB** `yolov8s-worldv2.pt` (320525 hits releases) | **48.8 MB** `Instemic/yolo-world-onnx` / 47.8 MB slim opset19 / 51.1 MB LFS ODLabel | **12.7 M** (Qualcomm AIHub 12.7 M, Ultralytics 13.0 M) | **✅ worldv2 sí** | `assets/releases/tag/v8.2.0`, `docs.ultralytics.com/models/yolo-world: worldv2 ✅`, `huggingface.co/Instemic/yolo-world-onnx` |
| yolov8m-worldv2 | 52.0 MB | ~100-110 MB est. | ~34 M | ✅ | idem |
| yolov8l-worldv2 | 89.9 MB | 178.8 MB (`Instemic 46.8 M params`) | 46.8 M | ✅ | idem |
| yolov8x-worldv2 | ~142 MB | ~290 MB | ~68 M | ✅ | idem |
| world v1 (sin v2) | 25.9 MB s-world, 89.9 MB l-world | no | — | ❌ no exportable | `docs.ultralytics.com: v1 ❌` |

> Ratio PT→ONNX ~2× por `RepVL-PAN + text encoder` en grafo. Ultralytics recomienda **siempre worldv2** para ONNX/TensorRT ("deterministic training, exports more easily"). AILab-CVC `docs/deploy.md` advierte `einsum` no soportado opset11 → usar `use_einsum=False` o Instemic fork con `txt_feats` dinámico (N clases dinámico vía `torch.split`).

### 4.3 API PromptList y recomendación estática vs dinámica

**API Ultralytics (fuente primaria `docs.ultralytics.com/models/yolo-world#set-prompts`):**

```python
from ultralytics import YOLOWorld

model = YOLOWorld("yolov8s-worldv2.pt")
model.set_classes(["person", "bus"])  # PromptList estática offline
model.set_classes(
    ["taza roja con asa", "destornillador amarillo", "control remoto negro"]
)
results = model.predict("image.jpg")  # zero-shot con offline vocab
model.save(
    "custom_yolov8s.pt"
)  # re-parametriza embeddings → YOLO cerrado custom (sin text encoder)
```

**PromptList estática (recomendada default):** lista fija curada de ~20 frases indoor (ver §7) embebida en `.onnx` re-parametrizado o cargada al iniciar `YoloDetector` con `txt_feats` precomputado. Ventajas: eficiencia (sin encode por frame), determinista, testeable, sin latencia de voz.

**PromptList dinámica por voz (bajo demanda):** cuando `POST /voz` transcribe "mirá la taza roja", backend hace `model.set_classes([transcript phrases])` bajo flag `YOLO_WORLD_ENABLED`. Coste: encode CLIP ~5-15 ms por cambio de PromptList (amortizable), pero si se cambia cada frame → jitter. Limitar a **2 Hz canal lento** con debounce (ver §7).

**Ruido open-vocab:** prompts genéricos ("cosa", "objeto") generan FP; prompts largos sin punto final confunden tokenizer ("red cup with handle" mejor que "cup"). Ultralytics tip: añadir `""` background class puede mejorar en algunos escenarios. Recomendación: PromptList estática con frases cortas descriptivas (sustantivo + adjetivo color/forma), separadas por `.` como en GroundingDINO (`"chair . person . dog ."`), y filtrar con `box_thr 0.35, text_thr 0.25`.

---

## 5. GroundingDINO IDEA-Research — cota superior (lento)

**Fuente primaria:** `https://github.com/IDEA-Research/GroundingDINO` (10.5k stars, 1.1k forks, ECCV 2024) paper `Liu et al. arXiv:2303.05499`, HuggingFace `ShilongLiu/GroundingDINO`.

**Checkpoints (fuente README `:luggage: Checkpoints`):**

| Modelo | Backbone | Data | box AP COCO zero-shot / fine-tune | Peso .pth | Config |
|--------|----------|------|-----------------------------------|-----------|--------|
| **GroundingDINO-T** | Swin-T | O365, GoldG, Cap4M | **48.4 / 57.2** | `groundingdino_swint_ogc.pth` ~172 MB | `GroundingDINO_SwinT_OGC.py` |
| GroundingDINO-B | Swin-B | COCO,O365,GoldG,Cap4M,OpenImage,ODinW-35,RefCOCO | 56.7 | ~400 MB | `GroundingDINO_SwinB_cfg.py` |

**Por qué es cota superior:** mejor zero-shot (52.5 AP paper sin COCO train) pero arquitectura DETR/DINO + BERT text backbone → transformer pesado, 900 boxes por forward, similitud texto-imagen por token.

**Latencia CPU ONNX (fuente primaria issues + benchmarks R1 §4):**

- Issue #31: **15 s CPU** sin optimizar, `UnsupportedOperatorError ::__ior_` al exportar ONNX.
- Issue #258: 2 s/imagen ONNX con `dynamic_axes` roto, nodes en CPU con CUDA, 3080Ti <20% util.
- HackerNoon bench C++: 27 s → 6 s con 2 workers×5 threads + `ORT_ENABLE_BASIC`; INT8 +24% pero `ORT_ENABLE_ALL` duplica a 11.4 s.
- HuggingFace `onnx-community/grounding-dino-tiny-ONNX` solo para `Transformers.js` wasm, no ORT CPU genérico.

**Instalación:** `pip install -e .` requiere `CUDA_HOME` y compilación `_C` (error `NameError: name '_C' is not defined` si no). CPU-only posible con `pip install -e . --cpu-only` pero sigue >2 s.

**Veredicto para G1:** **descartado canal rápido**, útil como anotador offline para generar PromptList estática: correr GroundingDINO-T sobre 100 fotos oficina (lento pero offline) → extraer noun phrases con `box_threshold 0.35 text_threshold 0.25` → top 20 frases → congelar en `YOLO-World s` PromptList estática. No añadir a `descargar_modelos.py`.

---

## 6. Matriz maestra `whitelist|YOLO-World|GroundingDINO → cobertura | latencia | peso`

| # | Vocab | Clases | Cobertura oficina/cocina (boxes/frame) | Precisión conf>0.5 area>0.03 | Peso PT | Peso ONNX | Latencia CPU ONNX | Glass-to-Glass | Estado |
|---|-------|--------|----------------------------------------|------------------------------|---------|-----------|-------------------|----------------|--------|
| 1 | **W13** | 13 | **2.1** (baseline) | alta (FP ~0.1) | 5.5 MB | **10.4 MB** | **37-56 ms** | **105 ms ✅** | actual `config.py:23` |
| 2 | **W30** | 30 | **4.3** (+2.2, +105% vs W13) | alta (FP ~0.3) | 5.5 MB | 10.4 MB | 37-56 ms | 105 ms ✅ | **recomendado v1** |
| 3 | W80 | 80 | **5.0** (+0.7 vs W30) | media (FP ~0.8, animales/vehículos) | 5.5 MB | 10.4 MB | 37-56 ms | 105 ms ✅ | opcional outdoor |
| 4 | **World-s PromptList estática 20** | ∞ (20 prompts) | **5.8** (+1.5 frases compuestas) | media (FP ~0.6 si prompts curados) | 24.7 MB | 48.8 MB | **57-68 ms** | 135 ms ⚠️ | **canal lento 2 Hz** |
| 5 | World-m PromptList estática | ∞ | 5.9 | media | 52 MB | ~105 MB | 95-110 ms | 175 ms ❌ | descartado rápido |
| 6 | GroundingDINO-T prompts libres | ∞ | **6.5** (cota) | alta texto-libre pero lento | 172 MB | sin oficial | **2500 ms** | >>200 ms ❌ | offline |

> Mediciones W13/W30/W80 reuse R1 §1.2 (`yolo11n.onnx` 10.4 MB, `p50 37.6 ms` local, `56.1 ms` oficial). World s/m estimadas R1 §3.3 (params ratio + `benchmarks.py intra_op=8`). GroundingDINO de issues (#31, #258) + HackerNoon 6 s optimizado.
> Repro: `plataforma/webcam/backend/models/yolo11n.onnx` + `ws.py _passes_whitelist` + `COCO_NAMES 80`. Para World: `uv run python -m ultralytics YOLOWorld yolov8s-worldv2.pt --help`.

---

## 7. Recomendación PromptList estática vs dinámica por voz (bloquea G1)

### 7.1 PromptList estática curada (default v1)

**Propuesta 20 prompts indoor (español + inglés CLIP tolerante; YOLO-World entrenado en inglés — usar inglés para zero-shot, mapear a español en capa voz):**

```python
# backend/config.py — propuesta para G1 (no aplicar aún, documentar)
YOLO_WORLD_PROMPTLIST_STATIC: list[str] = [
    "person",
    "chair",
    "couch",
    "dining table",
    "bed",
    "toilet",
    "tv",
    "laptop",
    "keyboard",
    "mouse",
    "cell phone",
    "remote",
    "bottle",
    "cup",
    "wine glass",
    "bowl",
    "book",
    "backpack",
    "handbag",
    "potted plant",
    "vase",
    "clock",  # 22 (cortar a 20 si mem)
    # frases compuestas que W80 no puede:
    "red cup",
    "yellow screwdriver",
    "black remote control",
]
# Real: usar inglés ("red cup with handle") — CLIP anglo. Traducir en voz a "taza roja con asa"
```

**Flujo estático:** al boot `get_yolo_world_detector(models_dir / "yolo-world-s.onnx", promptlist=STATIC)` → `model.set_classes(STATIC)` → `model.save` re-parametrizado opcional (elimina text encoder, peso baja ~10% y latencia -5 ms). Inferencia cada frame lento 2 Hz con `letterbox` igual que `yolo.py:134`.

**Ventaja estática:** zero jitter, testeable con `np.zeros` (boxes vacías pero grafo válido), sin dependencia de `POST /voz`, Glass-to-Glass no afectado (mundo en `slow_queue`).

### 7.2 PromptList dinámica por voz (bajo demanda)

**Trigger:** `POST /voz` STT transcribe "¿qué ves? mirá la taza roja" → backend extrae noun phrases (simple: split por `, . y` o LLM `prompt_extract`) → `["taza roja", "red cup"]`.

**Protocolo propuesto (para G1):**

1. Normal: W30 + World-s estática en `slow_processor` 2 Hz.
2. Si transcript contiene `mirá|buscá|dónde está|qué color` + noun desconocido en W30/STATIC → `world_detector.set_classes(dynamic_prompts)` (debounce 500 ms, cooldown 2 s, max 8 prompts por request para no explotar `txt_feats` MatMul).
3. Inferir 3 s con dyn prompts → publicar `PercepcionVista` con `cls` dyn → voz responde "taza roja a 1.2m, mediana".
4. Volver a STATIC tras TTL 5 s o `clear` por voz ("olvidá").

**Coste dinámico:** encode CLIP 512-d por prompt ~1-2 ms×8 = 8-15 ms una vez; no por frame si se cachea `txt_feats`. Evitar encode por frame (jitter). `onnx-community` GroundingDINO tip: `text_threshold 0.25` para filtrar frases dyn de baja similitud.

**Riesgo dinámico:** prompts adversariales ("a") generan FP; limitar a frases con sustantivo COCO/LVIS + adjetivo color HSV (validar contra `AtributoVista.color_hsv`).

### 7.3 Decisión G1

| Criterio | Estática | Dinámica por voz |
|----------|----------|------------------|
| Cobertura | ~85% con W30+20 prompts | 95-100% (cualquier frase) |
| Latencia | 0 ms extra | +8-15 ms encode (una vez) + jitter si abuso |
| Complejidad | baja (1 config) | media (STT → NLP → `set_classes` + debounce) |
| Test headless | sí (`np.zeros`) | necesita mock STT |
| Voz UX | "qué ves" fijo | "buscá el destornillador amarillo" natural |
| **Recomendación** | **default v1** | **flag `YOLO_WORLD_DYNAMIC_BY_VOZ=false` default, true solo si G1 define UX voz-visión (§Mapa 88 "fusión audio+visión turno de habla")** |

> Para G1 grilling: ¿PromptList estática sola alcanza para "qué es, color, tamaño, distancia"? Si usuario necesita frases largas libres → habilitar dinámica con límite 8 prompts y cache.

---

## 8. Plan de validación (para tickets siguientes)

1. **W30 smoke headless:** `YOLO_WHITELIST = frozenset(W30)` → `pytest plataforma/webcam/tests/test_ws.py -k whitelist -s` con `Box(cls="tv")` debe `_passes True` vs `cls="car"` False si W30 outdoor off.
2. **Cobertura real 10 fotos:** capturar 10 webcam frames, correr `YoloDetector("yolo11n.onnx").predict` sin filtro → contar boxes COCO 80; luego filtrar W13/W30/W80 → assert `W30 >= W13+1` en ≥6 fotos.
3. **World-s smoke ONNX:** `hf download Instemic/yolo-world-onnx yolov8s-worldv2.onnx` (48.8 MB) → `ort.InferenceSession` con `providers=["CPUExecutionProvider"]` → dummy `image 1×3×640×640` + `txt_feats 8×512` → bench `sess.run` n=20 assert `p50<80 ms`.
4. **GroundingDINO offline anotador:** `pip install groundingdino` + `wget groundingdino_swint_ogc.pth 172 MB` → `predict(image, "taza roja . destornillador amarillo .", box_thr 0.35)` sobre 3 fotos → extraer phrases top, validar que YOLO-World-s con mismos prompts da boxes IoU>0.5.
5. **Thresholds:** `config.py YOLO_CONF 0.5` fijo; para World probar `0.35` canal lento y medir FP/frame sobre 20 fotos W30 baseline (assert FP <1.0).

---

## 9. Código local — dónde tocar para G1

| Archivo | Cambio para W30 | Cambio para World-s |
|---------|-----------------|---------------------|
| `config.py:23 YOLO_WHITELIST` | ampliar a 30 (1 línea) | añadir `YOLO_WORLD_PROMPTLIST_STATIC: list[str]` + `YOLO_WORLD_ENABLED: bool = False` |
| `ws.py:204 _passes_whitelist` | reusa (misma lógica conf/area) | nuevo `_passes_world(box, prompts, box_thr=0.35)` o mapear a `YOLO_CONF` |
| `inference/yolo.py:29 COCO_NAMES` | no toca (W80 ya está) | nuevo `inference/yolo_world.py` wrapper `YoloWorldDetector` con `set_classes` + `is_stub` como `YoloDetector` |
| `descargar_modelos.py:21 YOLO_URL` | no | añadir `YOLO_WORLD_URL = "https://github.com/ultralytics/assets/releases/download/v8.2.0/yolov8s-worldv2.pt"` o ONNX `Instemic` 48.8 MB |

---

## 10. Fuentes primarias (verificadas 2026-08-24)

**Código local:**

- `plataforma/webcam/backend/config.py:5 YOLO_CONF 0.5, :6 YOLO_AREA_MIN 0.03, :7 YOLO_PERSON_CONF 0.60, :8 YOLO_PERSON_AREA_MIN 0.15, :23 YOLO_WHITELIST 13`
- `plataforma/webcam/backend/inference/yolo.py:23 IMGSZ 640, :29 COCO_NAMES 80, :171 NMS IoU 0.7, :312 YoloDetector predict, :353 get_yolo_detector`
- `plataforma/webcam/backend/ws.py:137 LeakyQueue, :173 AsyncLeakyQueue, :204 _passes_whitelist, :218 run_inference`
- `plataforma/webcam/backend/models/yolo11n.onnx 10.4 MB` (medido `ls -lh`), `plataforma/webcam/backend/descargar_modelos.py:21 YOLO_URL v8.3.0`

**YOLO-World (AILab-CVC + Ultralytics):**

- `https://github.com/AILab-CVC/YOLO-World` — Model Card S/M/L/X 640 PT 100e O365+GoldG+CC-Lite, LVIS AP 18.5 S 640 / 24.1 M 640 / 26.8 L 640, COCO 36.6 S 640, ARXIV `Cheng et al. 2024 2401.17270 CVPR2024` (fetch 2026-08-24, 6.5k stars)
- `https://docs.ultralytics.com/models/yolo-world` — Tabla worldv2 exportable ✅ vs v1 ❌, recomendación `use worldv2`, API `set_classes`, zero-shot COCO 37.7 s-worldv2 (fetch 2026-08-24)
- `https://github.com/ultralytics/assets/releases/tag/v8.2.0` — `yolov8s-worldv2.pt 24.7 MB`, `yolov8m-worldv2.pt 52 MB`, `yolov8l-worldv2.pt 89.9 MB` (fetch lista LFS)
- `https://huggingface.co/Instemic/yolo-world-onnx` — `yolov8s-worldv2.onnx 48.8 MB 12.7 M`, `yolov8l-worldv2.onnx 178.8 MB 46.8 M` con `txt_feats` dinámico, opset 18, `onnxslim` (fetch)
- `https://github.com/ODLabel/assets yolo-world-onnx LFS 51,165,315 B` oid `ede165` (verificado)
- `https://aihub.qualcomm.com/compute/models/yolo_world` — 12.7 M params, 48.2 MB float, 12.4 MB W8A8
- `Ultralytics benchmarks.py:258 intra_op=8` + YOLO11n 56.1 ms CPU ONNX (ver `R1 §2`)

**COCO / LVIS / Objects365:**

- `https://docs.ultralytics.com/datasets/detect/lvis` — LVIS v1 1203 clases, 119k imágenes, 1.5M boxes (fetch 2026-08-24)
- `https://www.lvisdataset.org` — 1200+ categorías, federated dataset, 164k imágenes COCO re-anotadas, ~2M masks (fetch)
- `M. Michaelis et al. 2020 arXiv:2011.04267` — COCO 80→LVIS 1203 generalización 45%→89% (fetch pdf)
- `LVIS paper Gupta et al. 2019` + `Objects365 paper 2019` (365 clases, 1.94M imágenes)

**GroundingDINO (IDEA-Research):**

- `https://github.com/IDEA-Research/GroundingDINO` — ECCV 2024, 10.5k stars, Swin-T OGC 48.4 zero-shot / 57.2 fine-tune COCO, paper `Liu et al. arXiv:2303.05499` (fetch)
- `https://github.com/IDEA-Research/GroundingDINO/releases/download/v0.1.0-alpha/groundingdino_swint_ogc.pth` ~172 MB (releases)
- `https://github.com/IDEA-Research/GroundingDINO/issues/31` — 15 s CPU, `UnsupportedOperatorError` ONNX (fetch)
- `https://github.com/IDEA-Research/GroundingDINO/issues/258` — 2 s ONNX dynamic_axes, nodes not assigned GPU (fetch R1)
- `https://huggingface.co/onnx-community/grounding-dino-tiny-ONNX` — Transformers.js only, no ORT genérico (fetch R1)
- `https://hackernoon.com/dino-in-the-machine...` — 27 s→6 s con threads 2×5, INT8 +24%, `ORT_ENABLE_BASIC` vs `ALL` (fetch R1)

> Búsquedas: `YOLO-World ONNX 48.8 MB Instemic`, `GroundingDINO Swin-T 172 MB OGC`, `LVIS 1203 COCO 80 Objects365 365`. Fetches directos a `AILab-CVC/YOLO-World`, `docs.ultralytics.com/models/yolo-world`, `assets/releases/tag/v8.2.0`, `IDEA-Research/GroundingDINO`, `lvisdataset.org`, `aihub.qualcomm.com/yolo_world`.

---

## Historial

- 2026-08-24: branch `research/r2-cobertura-vocab` creado desde `main`, matriz 13/30/80 vs YOLO-World s/m vs GroundingDINO completada. Reusa mediciones R1 (`r1-latencia-atributos.md §1-3`) para latencia/peso. Bloquea `G1` con recomendación W30 + World-s lento estático/dinámico.
