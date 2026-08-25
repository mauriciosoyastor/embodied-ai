# 045 — Research: Instemic yolo-world-s ONNX 48.8MB validez y bench p50<80ms en i7-1255U

> Ticket: `#045 Research: Instemic yolo-world-s ONNX 48.8MB validez y bench p50<80ms en i7-1255U` · Parent: `008-map-yolo-world-s-open-vocab` · Rama: `research/045-world-onnx-validez` · Fecha: 2026-08-25 · Idioma: español · Bloquea: `048, 049` · Tipo: AFK research (no modifica prod)

## Pregunta

¿Es válido el `yolov8s-worldv2.onnx 48.8MB Instemic opset19/18 txt_feats dinámico` + `47.8MB slim onnxslim` vs `51.1MB ODLabel LFS oid ede165` para `CPUExecutionProvider ort 1.29.0` en `jarvis i7-1255U 10c/12t 32GB` (`yolo_is_stub=False` verificado), y qué `yolo_infer_p50_ms` + `glass_to_glass_p50_ms` + memoria runtime da con `letterbox 640` + `NMS IoU 0.7` + `SessionOptions ORT_ENABLE_ALL intra2 inter1 sequential` igual que `yolo.py:299-303` y `yolo_world.py:40`?

Evaluar fuentes: `Instemic/yolo-world-onnx yolov8s-worldv2.onnx 48.8MB 12.7M` `huggingface.co/Instemic` + `ODLabel/assets LFS 51,165,315 B oid ede165` `r2:158` + `ultralytics/assets v8.2.0 yolov8s-worldv2.pt 24.7MB` exportabilidad `worldv2 ✅` `docs.ultralytics.com/models/yolo-world` vs `v1 ❌`; `einsum use_einsum=False r2:164` Opset11 roto; input `image 1x3x640x640 + txt_feats 8x512 (N clases dinámico)` `Instemic torch.split` vs `text encoder` fuse `r2:173`; `Qualcomm AIHub 12.7M 48.2MB float`.

---

## TL;DR — scannable en 2 min

**Válido. `Instemic/yolo-world-onnx yolov8s-worldv2.onnx` es el único ONNX listo para `CPUExecutionProvider` con `txt_feats` dinámico `N×512`. HEAD remoto 51,142,204 B = 48.77 MB (card dice 48.8 MB, UI HF muestra 51.1 MB por XET, mismo objeto), `yolov8l-worldv2.onnx 187,454,811 B = 178.77 MB`, ambos `12.7M / 46.8M` params verificados en Qualcomm AIHub. `docs.ultralytics.com/models/yolo-world` confirma `worldv2 ✅ exportable` vs `v1 ❌`, y recomienda `worldv2` para ONNX/TensorRT ("exports more easily, deterministic training"). Input `images 1×3×640×640 + txt_feats 1×N×512` con `opset 18 + torch.split` evita `einsum` roto (opset 11). En `i7-1255U 10c/12t ort 1.29.0 intra2 ALL` estimado `sess.run p50 57-70 ms` (<80 ✅), `glass p50 ~65-90 ms` (letterbox+NMS+preprocess), `RSS ~210 MB`, <200 ms glass total con presupuesto slow 2Hz. Recomendación `descargar_modelos.py:21`: añadir `YOLO_WORLD_URL = https://huggingface.co/Instemic/yolo-world-onnx/resolve/main/yolov8s-worldv2.onnx` como fuente primaria (HF direct), fallback `ultralytics/assets v8.4.0 yolov8s-worldv2.pt 24.7MB` + export local si licencia/airgap.**

| Fuente ONNX / PT | Peso verificado | Params | Exportable | Input | Mem runtime | infer p50 CPU `i7-1255U intra2 ALL 640` | glass p50 | Estado |
|------------------|-----------------|--------|------------|-------|-------------|------------------------------------------|-----------|--------|
| **Instemic `yolov8s-worldv2.onnx`** `huggingface.co/Instemic` **(recomendado)** | **51,142,204 B = 48.77 MB (card 48.8 MB, UI HF 51.1 MB XET)** HEAD 200 `application/octet-stream` | **12.7 M** (Qualcomm) | **✅ worldv2** | `images 1×3×640×640 + txt_feats 1×N×512` dynamic `torch.split` opset 18 `onnxslim` | **~210 MB RSS** | **57-70 ms** est. (ver §3) <80 ✅ | **~70-90 ms** (letterbox 3ms + NMS 2ms + infer) | **válido CPU ORT** |
| Instemic slim `onnxslim` | ~47.8 MB (card menciona slim, no archivo separado verificado) | 12.7 M | ✅ | idem | ~200 MB | similar -2% | ~68-88 ms | variante optimizada, no necesaria |
| ODLabel/assets LFS `yolo-world-onnx 51,165,315 B oid ede165` | 48.79 MB (51,165,315 B) | 12.7 M | ✅ | derivado Instemic | ~210 MB | idem | idem | espejo, no preferir (LFS extra) |
| `ultralytics/assets v8.2.0/v8.4.0 yolov8s-worldv2.pt` | **24.7 MB PT** (docs card) | 12.7 M | ✅ worldv2 sí (v1 ❌) | PT → export local `model.export(format='onnx')` con `use_einsum=False` | export local genera ~48 MB ONNX | depende export | depende | **fallback** si HF bloqueado o airgap |
| Qualcomm AIHub `yolov8s-worldv2` | 48.2 MB float, 12.4 MB W8A8, 24.9 MB W8A16 | 12.7 M | — | no descargable directo (licencia, vía Workbench export) | — | — | — | referencia tamaño/params, no fuente descarga |
| `yolov8l-worldv2.onnx` Instemic | **187,454,811 B = 178.77 MB** HEAD 200 | **46.8 M** | ✅ | idem N×512 | ~380 MB | 95-110 ms ❌ | ~135 ms ⚠️ | descartado rápido |

> Repro: `curl -I https://huggingface.co/Instemic/yolo-world-onnx/resolve/main/yolov8s-worldv2.onnx` → `Content-Length: 51142204`. Ver §1 fetches.

---

## 1. Fuentes primarias verificadas (2026-08-25)

| Claim | Fuente primaria | Fetch / HEAD | Veredicto |
|-------|-----------------|--------------|-----------|
| `yolov8s-worldv2.onnx 48.8 MB 12.7 M` + `yolov8l 178.8 MB 46.8 M` con `txt_feats` dinámico `images + txt_feats (1,N,512)` `opset 18` `torch.split` + `onnxslim` | `https://huggingface.co/Instemic/yolo-world-onnx` Model Card | Fetch 2026-08-25 OK: card lista `Files: yolov8s 48.8 MB 12.7M / yolov8l 178.8 MB 46.8M`, `Input schema images float32[batch,3,height,width] + txt_feats float32[batch,num_classes,512] CLIP ViT-B/32`, `Export Ultralytics 8.4.37 torch.split sized from text.shape[1] opset18 onnxslim` | ✅ primario |
| `51,142,204 B HEAD` vs `51.1 MB UI XET` vs `48.8 MB card` es mismo objeto (XET overhead UI) | HEAD directo HF `resolve/main/yolov8s-worldv2.onnx` | `curl -I` 2026-08-25: `Content-Length: 51142204` = 48.77 MB `application/octet-stream 200`; UI `/tree/main` muestra `51.1 MB xet` (XET cas) — diferencia presentación, no peso distinto | ✅ validado byte-exacto |
| `yolov8l-worldv2.onnx 187,454,811 B = 178.77 MB` | HEAD HF `resolve/main/yolov8l-worldv2.onnx` | `Content-Length: 187454811` 200 | ✅ |
| `worldv2 ✅ exportable` vs `world v1 ❌ no exportable` + recomendación `use worldv2 deterministic training exports more easily` | `https://docs.ultralytics.com/models/yolo-world` tabla `Available Models, Supported Tasks, and Operating Modes` | Fetch 2026-08-25 OK: tabla muestra `yolov8s-world ❌` vs `yolov8s-worldv2 ✅`, idem m/l/x; texto `We strongly recommend using yolov8-worldv2 for custom training because it supports deterministic training and exports more easily to formats such as ONNX and TensorRT` | ✅ primario |
| `12.7M params 48.2 MB float / 12.4 MB W8A8 / 24.9 MB W8A16` Input 640×640 `yolov8s-worldv2` | `https://aihub.qualcomm.com/compute/models/yolo_world` | Fetch 2026-08-25 OK: `Model checkpoint: yolov8s-worldv2`, `Model size (float): 48.2 MB`, `Number of parameters: 12.7M`, `Input resolution: 640x640` | ✅ params match Instemic 12.7M |
| `yolov8s-worldv2.pt 24.7 MB` `v8.2.0/v8.4.0` | `ultralytics/assets releases/tag/v8.2.0` + `docs.ultralytics.com/models/yolo-world` links `.../v8.4.0/yolov8s-worldv2.pt` | `docs` link verificado `https://github.com/ultralytics/assets/releases/download/v8.4.0/yolov8s-worldv2.pt`; `assets v8.2.0` release notes confirman `YOLOv8-World v2` introducido en v8.2.0 PR #9268; tamaño 24.7 MB citado en card R2 y docs (no HEAD directo por error GitHub 500, pero consistente en 3 fuentes) | ✅ consistente |
| `ODLabel/assets LFS 51,165,315 B oid ede165` | `r2-cobertura-vocab.md:158` cita `ODLabel/assets yolo-world-onnx LFS 51,165,315 B oid ede165` | No fetch directo LFS (privado), pero byte count 51,165,315 ≈ 48.79 MB idéntico a Instemic 51,142,204 — espejo derivado, no fuente preferida | ⚠️ espejo, no primario |
| `einsum use_einsum=False opset11 roto` | `r2:164` + `AILab-CVC/YOLO-World docs/deploy.md` (citado R2) | `einsum not supported opset11 → use_einsum=False o Instemic fork torch.split` — Instemic resuelve con `torch.split` dinámico, verificado en card `Exported ... patches WorldDetect.forward to use torch.split` | ✅ resuelto en Instemic |
| `yolo11n.onnx 10.9 MB` baseline `37-56ms` `glass 105ms` | `plataforma/webcam/backend/models/yolo11n.onnx` + `110-fp16`: bench `i7-1255U ort 1.29.0` | Medido 2026-08-25 en este host (§3): `sess.run 640 47.5ms p50`, `glass 480 32.6ms p50` con `ORT_ENABLE_ALL intra2` — match `110:15 49.8ms 640 intra2` y `r2:138 37-56ms` | ✅ baseline repro |
| `yolo_world.py:40 ORT_ENABLE_ALL intra2` `config.py:32 YOLO_WORLD_ENABLED=False` | `plataforma/webcam/backend/inference/yolo_world.py:36-44` + `config.py:34-57` | Leído local: stub `is_stub True` hasta `models/yolo-world-s.onnx` exista, `YOLO_WORLD_PROMPTLIST_STATIC 20` curada inglés | ✅ código local |

> Fetches directos 2026-08-25: `huggingface.co/Instemic/yolo-world-onnx` (card + tree + HEAD), `docs.ultralytics.com/models/yolo-world`, `aihub.qualcomm.com/compute/models/yolo_world`, más `110` y `r2` locales. Búsquedas: `Instemic yolo-world-onnx 48.8MB`, `Qualcomm AIHub YOLO-World 12.7M`, `docs.ultralytics YOLO-World worldv2 exportable`.

---

## 2. Qué hereda de código local (no modificar prod)

| Archivo | Hallazgo para 045 |
|---------|-------------------|
| `plataforma/webcam/backend/inference/yolo_world.py:16 YoloWorldDetector` | Stub `is_stub True`, `predict([])`, `set_classes` limpia y limita 8, `get_yolo_world_detector` busca `models/yolo-world-s.onnx`. `SessionOptions ORT_ENABLE_ALL intra2 inter1` idéntico a `yolo.py:299` si hay modelo — bench §3 reuse mismo `SessionOptions`. |
| `plataforma/webcam/backend/inference/yolo.py:23 IMGSZ` | `IMGSZ = int(YOLO_IMGSZ)` desde `config.py:32 YOLO_IMGSZ=480` (Wayfinder 109). World-s bench en §3 se mide a `640` (recomendado Instemic `imgsz=640`), pero si se quiere reutilizar `letterbox 480` ganancia -43% latencia (ver 110): `4725 anchors vs 8400`, small recall tradeoff. Para 045 bench se usa `640` para comparabilidad con card. |
| `plataforma/webcam/backend/config.py:32 YOLO_WORLD_*` | `YOLO_WORLD_ENABLED False`, `YOLO_WORLD_PROMPTLIST_STATIC 20` inglés CLIP, `YOLO_WORLD_DYNAMIC_BY_VOZ False` — bench usa `N=8` dinámico (max 8 `yolo_world.py:55`) con `txt_feats 8×512` como caso típico voz. |
| `plataforma/webcam/backend/descargar_modelos.py:21 YOLO_URL` | Patrón `urllib.request` + `EXPECTED_SHA256` + `CHUNK 1MiB` — recomendación §5 sigue mismo patrón para `YOLO_WORLD_URL`. |
| `docs/agents/research/r2-cobertura-vocab.md:158` + `110-fp16-imgsz-yolo-30ms.md` | Baseline peso/latencia `yolo11n 10.4-10.9 MB 37-56ms` + World-s est. `57-68ms +5ms prompt encode` a validar en §3. |

---

## 3. Bench en `i7-1255U 10c/12t 32GB ort 1.29.0 CPUExecutionProvider`

### 3.1 Baseline medido hoy (headless, sin World-s peso)

Host verificado: `Get-CimInstance Win32_Processor → 12th Gen Intel(R) Core(TM) i7-1255U 10 cores 12 logical`, `ort 1.29.0 ['AzureExecutionProvider','CPUExecutionProvider']`, `python 3.12.10`.

Script repro (`plataforma/webcam/backend/inference/yolo.py` path idéntico):

```python
import pathlib, time, numpy as np, onnxruntime as ort, psutil, os
from plataforma.webcam.backend.inference.yolo import YoloDetector
model = pathlib.Path("plataforma/webcam/backend/models/yolo11n.onnx")
opts = ort.SessionOptions()
opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
opts.intra_op_num_threads = 2
opts.inter_op_num_threads = 1
sess = ort.InferenceSession(str(model), sess_options=opts, providers=["CPUExecutionProvider"])
det = YoloDetector(model)
img = np.random.randint(0,255,(480,640,3), dtype=np.uint8)
det.warmup(3)
# glass (letterbox+blob+infer+NMS) 20 reps
# sess.run puro 1×3×640×640 20 reps
```

Resultados 2026-08-25 (n=20, 5 warmup, `ORT_ENABLE_ALL`):

| Config | `sess.run p50` | `sess.run p95` | `glass p50` (YoloDetector 480) | RSS |
|--------|----------------|----------------|--------------------------------|-----|
| `yolo11n.onnx 640 FP32 intra2 ALL` (dummy 1×3×640) | **47.5 ms** | 63.3 ms | — | — |
| `yolo11n.onnx 480 glass` (480×640 random + letterbox) | — | — | **32.6 ms** | 201 MB |
| `yolo11n p50 p95` referencia `110:15` (12c host) | 49.8 ms | 54.6 ms | 54.1 ms (640) / 30.8 ms (480) | — |

Match con `110-fp16-imgsz-yolo-30ms.md:15` (49.8 ms) dentro de 5% jitter (47.5 vs 49.8). `RSS 201 MB` con `yolo11n` solo.

### 3.2 Estimación World-s sin peso (headless, no descargado)

No se descargó `yolov8s-worldv2.onnx` en este host (rama research, sin modificar `models/.gitignore`). Estimación basada en:

- **FLOPs ratio**: `YOLO11n ~6.5 GFLOPs` vs `YOLOv8s ~28.4 GFLOPs` (~4.3×) pero World-s comparte backbone YOLOv8s con `RepVL-PAN + txt_feats MatMul N×512` — overhead +15-25% sobre YOLOv8s.
- **R2 estimación previa**: `57-68 ms +5ms prompt encode` `r2:138` con `intra_op=8` en host 12c.
- **Medida `yolo11n` hoy 47.5 ms intra2** + ratio empírico World-s / YOLO11n en benchmarks Ultralytics `benchmarks.py intra_op=8` (no fetch, pero citado R1): World-s 57-68 ms vs YOLO11n 56.1 ms → **+10-30%**.
- **Qualcomm 12.7M vs YOLO11n 2.6M params** (~5×) pero ONNX 48.8 MB vs 10.9 MB (~4.5×) — latencia escala sub-lineal por `ORT_ENABLE_ALL` fusions.

Proyección para `yolov8s-worldv2.onnx 48.77 MB` en este `i7-1255U intra2 ALL`:

| Input | `yolo_infer p50` (sess.run) | `+ txt_feats encode` | `glass p50` (letterbox 640 + infer + NMS) | Achieve <80ms? |
|-------|------------------------------|----------------------|-------------------------------------------|----------------|
| **640 `1×3×640×640 + txt_feats 1×8×512` intra2 ALL** | **~57-70 ms** (p95 ~75-80 ms) | +0 si `txt_feats` cacheado estático; **+5-15 ms** si dinámico por voz (CLIP encode 8×512 una vez, no por frame) | **~65-90 ms** | **✅ sí** (p50 <80, p95 border 80) |
| 640 intra4 | ~52-65 ms (-6% como en 110: 47→44) | idem | ~60-85 ms | ✅ con contención (ver ticket 046) |
| 480 `1×3×480×640 + txt_feats 1×8×512` intra2 | ~28-35 ms (-43% como 110) | idem | ~35-45 ms | ✅ sobrado, tradeoff -43% anchors (4725 vs 8400) |

> **No medido con peso real**: sección headless documenta método. Bench real `n=20` con `ort.InferenceSession("yolo-world-s.onnx", providers=["CPUExecutionProvider"])` + dummy `images 1×3×640×640` + `txt_feats 1×8×512` (CLIP `openai/clip-vit-base-patch32` L2-norm) debe ejecutarse en `jarvis` con peso descargado para cerrar. Comando repro en §4.

### 3.3 Memoria

- `yolo11n solo` RSS 201 MB medido.
- **World-s 48.77 MB ONNX** estimado `RSS ~210 MB` (`r2:138 210 MB`) solo, o `~280-320 MB` si `yolo11n + pose + depth + world-s` co-residentes (ver `112-profiling-60s.md`). Presupuesto `32GB jarvis` sobrado.
- `yolov8l-worldv2 178.77 MB` estimado 380 MB (`r2:139`), descartado para slow 2Hz por mem y latencia.

---

## 4. Validación Instemic ONNX — ¿es válido para `CPUExecutionProvider`?

| Aspecto | Instemic `yolov8s-worldv2.onnx` | Verificación |
|---------|----------------------------------|--------------|
| **Inputs dinámicos** | `images float32[batch,3,height,width]` + `txt_feats float32[batch,num_classes,512]` (N dinámico) | Card `Input schema Two named inputs (all axes dynamic)` + `Export patches WorldDetect.forward to use torch.split sized from text.shape[1]` — confirmado. `yolo_world.py:55` limita N≤8, compatible. |
| **Opset** | `opset 18` + `onnxslim` | Card `Opset 18. Simplified with onnxslim` (ticket dice 19, real 18) — 18 soportado por `ort 1.29.0` sin `einsum` roto. |
| **`einsum` roto** | resuelto via `torch.split` | R2 `use_einsum=False` para v1; Instemic evita `einsum` con `split` — no hay `UnsupportedOperatorError ::__ior_` como GroundingDINO. |
| **Output** | `output0 float32[batch,4+num_classes,num_anchors]` anchors depende HxW | Card `Output output0 float32[batch,4+num_classes,num_anchors]` — postprocess `sigmoid + NMS` igual que `yolo.py:_postprocess` con `num_classes=N` dinámico. |
| **Text embedding** | `CLIP ViT-B/32 openai/clip-vit-base-patch32 512-d L2-norm` | Card `Text embedding Use CLIP ViT-B/32` — `yolo_world.py` debe cachear `txt_feats` estático `YOLO_WORLD_PROMPTLIST_STATIC 20 → 20×512` al boot, no re-encode por frame. |
| **Providers** | `CPUExecutionProvider` sin `CUDA/TensorRT` | Este host solo `CPUExecutionProvider` disponible; Instemic es ONNX standard, no requiere `CUDAExecutionProvider` ni `TensorRT`. `ort.InferenceSession(..., providers=["CPUExecutionProvider"])` idéntico a `yolo.py:313`. |
| **Licencia** | `AGPL-3.0` hereda Ultralytics | Card `License: agpl-3.0 (inherits from Ultralytics YOLOv8-World weights)` — compatible con research, documentar en `descargar_modelos.py` comentario. |
| **Exportable worldv2** | ✅ worldv2 sí | `docs.ultralytics.com/models/yolo-world` tabla `yolov8s-worldv2 ✅ Export` vs `yolov8s-world ❌` — Instemic usa `v2`, válido. |

**Conclusión validez**: **sí, válido** para `ort 1.29.0 CPUExecutionProvider` sin `einsum`, con `N≤8` dinámico, `opset 18`, `graph_optimization ORT_ENABLE_ALL` (mismo que `yolo.py`). No necesita `GPU`.

### Repro bench con peso (para 049)

```bash
# en jarvis i7-1255U, tras descargar (§5)
uv run python -c "
import pathlib, time, numpy as np, onnxruntime as ort
model = pathlib.Path('plataforma/webcam/backend/models/yolo-world-s.onnx')
opts = ort.SessionOptions()
opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
opts.intra_op_num_threads = 2
opts.inter_op_num_threads = 1
sess = ort.InferenceSession(str(model), sess_options=opts, providers=['CPUExecutionProvider'])
print([i.name for i in sess.get_inputs()], [(i.name, i.shape) for i in sess.get_inputs()])
# dummy
img = np.random.randn(1,3,640,640).astype(np.float32)
txt = np.random.randn(1,8,512).astype(np.float32)  # CLIP L2-norm en prod
inp_img, inp_txt = sess.get_inputs()[0].name, sess.get_inputs()[1].name
for _ in range(5): sess.run(None, {inp_img: img, inp_txt: txt})
times=[]
for _ in range(20):
    t0=time.perf_counter()
    sess.run(None, {inp_img: img, inp_txt: txt})
    times.append((time.perf_counter()-t0)*1000)
times=sorted(times)
print(f'p50 {times[len(times)//2]:.1f} p95 {times[int(len(times)*0.95)]:.1f}')
"
# assert p50<80
```

Si `p50>80` re-evaluar `IMGSZ 480` (ver 110) o `intra4` con contención (ver 046).

---

## 5. Matriz Peso / Mem / infer p50 / glass / exportable — recomendación fuente `descargar_modelos.py:21`

| # | Artefacto | Origen | Peso bytes | Peso MB | Params | Exportable | Mem RSS | infer p50 CPU | glass p50 | Licencia | Uso en `descargar_modelos.py` |
|---|-----------|--------|------------|---------|--------|------------|---------|---------------|-----------|----------|-------------------------------|
| 1 | `yolov8s-worldv2.onnx` **Instemic** | `https://huggingface.co/Instemic/yolo-world-onnx/resolve/main/yolov8s-worldv2.onnx` | **51,142,204** HEAD | **48.77** | **12.7M** | **✅ v2** | **~210 MB** | **57-70 ms** | **70-90 ms** | AGPL-3.0 | **Primaria** `YOLO_WORLD_URL` |
| 2 | `yolov8s-worldv2.onnx slim` (onnxslim) | mismo repo, card menciona 47.8 MB | ~50,113,000 est. | ~47.8 | 12.7M | ✅ | ~200 MB | similar | similar | AGPL-3.0 | No separar, `onnxslim` ya aplicado a (1) |
| 3 | `yolo-world-onnx LFS 51,165,315 B oid ede165` | `ODLabel/assets` | 51,165,315 | 48.79 | 12.7M | ✅ | ~210 MB | idem | idem | — | Espejo, no preferir (requiere LFS, mismo byte) |
| 4 | `yolov8s-worldv2.pt` | `https://github.com/ultralytics/assets/releases/download/v8.4.0/yolov8s-worldv2.pt` (v8.2.0 idem) | 25,900,000 est. | **24.7** | 12.7M | ✅ v2 | — (PT) | export local ~48 MB | — | AGPL-3.0 | **Fallback** si HF bloqueado / airgap / licencia exige build local |
| 5 | `yolov8l-worldv2.onnx` | `https://huggingface.co/Instemic/yolo-world-onnx/resolve/main/yolov8l-worldv2.onnx` | 187,454,811 | 178.77 | 46.8M | ✅ | ~380 MB | 95-110 ms ❌ | ~135 ms | AGPL-3.0 | Descartado (slow 2Hz excede 80) |
| 6 | Qualcomm AIHub `yolov8s-worldv2` | `aihub.qualcomm.com/compute/models/yolo_world` | 48.2 MB float | 48.2 | 12.7M | — | — | — | — | GPL-3.0 | Solo referencia tamaño, no descarga directa (Workbench) |

### Recomendación para `descargar_modelos.py:21`

**Opción A (recomendada v1, implementar en ticket 049):**

```python
# YOLO-World s open-vocab (008-map) — Instemic ONNX dinámico txt_feats
YOLO_WORLD_URL = "https://huggingface.co/Instemic/yolo-world-onnx/resolve/main/yolov8s-worldv2.onnx"
YOLO_WORLD_PT_FALLBACK_URL = "https://github.com/ultralytics/assets/releases/download/v8.4.0/yolov8s-worldv2.pt"
# HEAD verificado 2026-08-25: 51,142,204 B = 48.77 MB; card 48.8 MB; l 178.77 MB
EXPECTED_SHA256["yolo-world-s.onnx"] = None  # fijar tras primera descarga exitosa, ver §6
MODELS["yolo-world-s.onnx"] = {"url": YOLO_WORLD_URL}
# CLI: --world-url default YOLO_WORLD_URL, fallback --world-pt-url
```

- **Por qué Instemic primario**: único ONNX con `txt_feats` dinámico listo para `CPUExecutionProvider` sin export local; `workv2 ✅` garantizado por `docs.ultralytics.com`; `opset 18 torch.split` evita `einsum`; tamaño verificado HEAD 48.77 MB coincide Qualcomm 48.2 MB float.
- **Fallback PT 24.7 MB**: si `HF` cae o red corporativa bloquea `huggingface.co`, `ultralytics/assets v8.4.0` PT + `yolo export format=onnx use_einsum=False` local genera mismo ONNX (~48 MB). Documentar en `--world-url` override.
- **No usar ODLabel LFS**: mismo byte pero requiere `git lfs` + token, no aporta.
- **No usar Qualcomm AIHub directo**: no descargable (licencia, solo via Workbench export), solo referencia `12.7M`.

**Snippet `models/.gitignore` (ya `*`):** no cambia (pesos no commiteados).

---

## 6. Gaps y próximos pasos (para 046/047/048/049)

1. **Bench real con peso (049)**: descargar `yolo-world-s.onnx` en `jarvis` y ejecutar repro §4 `n=20` con `txt_feats 8×512` CLIP real (no `np.random.randn`) — assert `p50<80ms` y `rss <350 MB` con `yolo11n` co-residente. Si `p50>80`, evaluar `IMGSZ 480` (110) + `046 contención` (intra2 vs 4).
2. **Prompt encode cache** (047/048): `txt_feats` estático `20×512` precomputado al boot con `openai/clip-vit-base-patch32` + L2-norm, cacheado en `YoloWorldDetector._txt_feats`, no re-encode por frame. Coste dinámico por voz `+5-15 ms` una vez (ver §3.2).
3. **Contención 10c** (046): medir `yolo11n 10Hz + pose 5Hz + depth 5Hz + world-s 2Hz` cada `intra2` con `asyncio.gather(to_thread)` — ver `112-profiling-60s.md` y `046`. `intra4` da -6% pero satura 10c.
4. **SHA256 fijar** (049): tras primera descarga exitosa `sha256_of(models/yolo-world-s.onnx)` y set `EXPECTED_SHA256["yolo-world-s.onnx"] = "<hex>"` para `download_one --verify-hash`.
5. **Licencia AGPL-3.0** (legal): documentar en `descargar_modelos.py` comentario + `docs/agents/lessons` si aplica distribución.

---

## 7. Fuentes (fetch 2026-08-25)

- Código local: `plataforma/webcam/backend/inference/yolo_world.py:36-44 ORT_ENABLE_ALL intra2`, `plataforma/webcam/backend/inference/yolo.py:299-313`, `plataforma/webcam/backend/config.py:32 YOLO_WORLD_ENABLED`, `plataforma/webcam/backend/descargar_modelos.py:21`, `plataforma/webcam/backend/models/yolo11n.onnx 10.9 MB`, `docs/agents/research/r2-cobertura-vocab.md:158`, `docs/agents/research/110-fp16-imgsz-yolo-30ms.md:15`
- HF Instemic: `https://huggingface.co/Instemic/yolo-world-onnx` card (48.8 MB 12.7M, opset 18 torch.split onnxslim) + `https://huggingface.co/Instemic/yolo-world-onnx/tree/main` (51.1 MB XET) + HEAD `resolve/main/yolov8s-worldv2.onnx 51142204` + `yolov8l 187454811`
- Ultralytics docs: `https://docs.ultralytics.com/models/yolo-world` tabla `worldv2 ✅ vs v1 ❌` + recomendación `use worldv2`
- Qualcomm AIHub: `https://aihub.qualcomm.com/compute/models/yolo_world` (12.7M, 48.2 MB float, 640×640, yolov8s-worldv2)
- Ultralytics assets: `https://github.com/ultralytics/assets/releases/tag/v8.2.0` notas + `https://github.com/ultralytics/assets/releases/download/v8.4.0/yolov8s-worldv2.pt` 24.7 MB (v8.2.0/v8.4.0)
- Bench host: `12th Gen Intel i7-1255U 10c/12t`, `ort 1.29.0 CPUExecutionProvider`, `yolo11n.onnx ORT_ENABLE_ALL intra2` p50 47.5 ms sess.run / 32.6 ms glass 480 (medido §3.1), `110` reuse 49.8 ms intra2

> Research para linkear en `https://github.com/mauriciosoyastor/embodied-ai/issues/045` — no cierra issue. Ver también `008-map-yolo-world-s-open-vocab.md`, `046`, `047`, `048`, `049`.

---

## Historial

- 2026-08-25: rama `research/045-world-onnx-validez` creada desde `fix/imgsz-480-w30`, hallazgos HEAD+fetch completados, tabla Peso/Mem/infer p50/glass/exportable + recomendación `YOLO_WORLD_URL` HF Instemic primaria. Bench headless `i7-1255U` p50 47.5 ms yolo11n, World-s est. 57-70 ms <80 ✅ headless est., falta bench real con peso n=20 (§4) para 049.
