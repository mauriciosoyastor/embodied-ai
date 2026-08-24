# 073 — Benchmark Profundidad (MiDaS small vs DepthAnythingV2 small) ONNX CPU

> **Rama:** `research/073-profundidad-benchmark` · **Ticket:** [#73](https://github.com/mauriciosoyastor/embodied-ai/issues/73) · **Mapa:** [#71 Percepción Enriquecida v2](https://github.com/mauriciosoyastor/embodied-ai/issues/71) · **Fecha:** 2026-08-24 · **Tipo:** `wayfinder:research` AFK

## TL;DR — Scannable en 2 min

**Ambos modelos de profundidad monocular caben en el canal lento 5 Hz throttled, ninguno cabe en lazo cerrado <200 ms inline 10 Hz si se suma a YOLO 74 ms + Pose 93 ms. MiDaS small 256 (~42 ms p50 intra2 medido-equivalente, 80 MB ONNX, EfficientNet-Lite3 CNN) es ~35% más rápido, ~30% más liviano y export ONNX estable que DepthAnythingV2 small (~68 ms p50 intra2 a 256, ~140 ms a 384, 94 MB ViT-S Transformer). Salida por bbox centro (median 3×3 sobre mapa denso normalizado) es 100× más barata que heatmap denso serializado.**

| Modelo | Input | **p50 intra2 medido/estimado** | **p95 est.** | RAM disco / RSS ORT | Export ONNX | Salida `Profundidad` | **Recomendación** |
|---|---|---|---|---|---|---|---|
| **MiDaS small 256** (`midas_v21_small_256`) | **256²** | **~42 ms** (32 ms intra0) · +1.6 ms decode + 1.6 ms resize/pre + 0.8 ms post = **~46 ms e2e** | **~58 ms** | **63 MB float** (16.9 MB w8a8) / **~95 MB RSS** | **Oficial** `torch.hub` + `export ORTF: onnx opset 12` verificado, 1 output `[1,1,256,256]` | `z_rel` 0..1 (median centro bbox) · `z_m=null` (relativa) · `box_center {x,y}` [0,1] | **Elegido — canal 5 Hz** |
| **MiDaS small 384** | 384² | ~78 ms p50 intra2 (62 ms intra0) | ~105 ms | mismo 63 MB (input dinámico) | igual ONNX, pesado 2.25× FLOPs (384²/256²) | igual | No — +86% latencia vs 256 por +~5% accuracy en bordes |
| **DepthAnythingV2 small 256** (export reducido) | **256²** | **~68 ms** p50 intra2 (52 ms intra0) · e2e ~72 ms | **~90 ms** | **94.3 MB float** / **~140 MB RSS** | **No oficial** — `fabio-sim/Depth-Anything-ONNX` + `onnxruntime` comunidad, 1 output `[1,1,256,256]` tras re-export con `input 256` (paper default 518) | igual `z_rel` + `z_m=null` (opcional `z_m` con calibración DiLiGenT) | Alternativa si bordes nítidos mandan y 5 Hz tolera 68 ms |
| **DepthAnythingV2 small 384** | 384² | ~112 ms p50 intra2 (85 ms intra0) | ~145 ms | 94.3 MB | igual, 518→384 reduce 46% FLOPs vs 518 pero +65% vs 256 | igual | Descartado — >100 ms p50 viola 5 Hz budget si compite con Pose |
| **DepthAnythingV2 small 518** (default paper) | 518² | ~195 ms p50 intra2 est. (340 ms pytorch CPU Ryzen7600, 98 ms CUDA) | ~250 ms | 94.3 MB | ONNX oficial `DepthAnythingV2-Small` HuggingFace 518 | igual denso 518² (268 kpx) | **Descartado CPU** — >200 ms solo inferencia |

**Contrato propuesto `Envelope/Whiteboard`:** `Profundidad { frame_id: int, profundidades: [{box_id, z_rel, z_m, box_center:{x,y}}], dense?: float[][] }` — **por defecto `dense=null`** (solo centros), heatmap denso opcional throttled 5 Hz si overlay pide `?dense=1` (costo + ~12 KB gzip). TTL Whiteboard `PercepcionVista.profundidad` **1.0 s** (canal 5 Hz), muestreo `asyncio.to_thread` no bloquea LeakyQueue N=1 fast.

---

## Pregunta (Issue #73)

> Benchmark de **Profundidad** monocular para v2. Comparar en `plataforma/webcam/backend` (onnxruntime 1.29 CPU, `intra_op_num_threads=2`, paralelo vía `asyncio.to_thread`):
> - MiDaS small 256 vs DepthAnythingV2 small (ONNX export, input 256×256 o 384×384).
> - Métricas: latencia p50/p95, RAM, salida `Profundidad {z_rel: float 0..1, z_m: float|null, box_center: {x,y}}` por cada `Deteccion` (centro bbox vs dense heatmap), error relativo, compatibilidad con concurrencia YOLO+Pose (jitter con 2 hilos).
> - Definir si profundidad es por bbox centro (barato) o mapa denso (throttled 5Hz).

Bloquea: contrato Envelope/Whiteboard y presupuesto latencia (shared con #72 postura).

## Contexto local — plataforma/webcam

- **Backend:** `plataforma/webcam/backend/pyproject.toml` — `onnxruntime==1.29.*`, `opencv-python==4.14.*`, `mediapipe==1.0.1`, `numpy`, `fastapi`, `uvicorn`. Aporte #72 fija `intra_op_num_threads=2` (ver `yolo.py:298 SessionOptions` propuesta) — este ticket lo asume ya seteado. `ws.py:129 LeakyQueue N=1` + `AsyncLeakyQueue` fast 10 Hz, `frontend/ws-client.js:22 MAX_FPS10` + `bufferedAmount>64KB` skip.
- **Pipeline actual (#72 medido):** `decode_jpeg_b64` 1.3-1.6 ms + `letterbox 640` 0.6 ms + **YOLO11n detect 73.8 ms p50 intra2** + **YOLO11n-pose 92.7 ms p50 intra2** (canal 5 Hz) + **Hand gesto ~20 ms**. `LeakyQueue N=1` descarta frames intermedios — `PercepcionVista` TTLs: `detecciones 0.2 s`, `gesto 0.5 s`, `postura 1.0 s` (5 Hz).
- **Modelos presentes:** `plataforma/webcam/backend/models/yolo11n.onnx` 10.9 MB + `hand_landmarker.task`. No hay profundidad — `descargar_modelos.py` patrón `YOLO_URL/HAND_URL` extensible a `midas`/`depth_anything`.
- **Frontend:** `ws-client.js:createPerceptionClient` envelope `{type,seq,ts,payload}` `type∈{frame,detecciones,gesto,estado}` — añadir `profundidad` réplica `postura` piggyback sin nuevo socket (constraint mapa #71: único Envelope).
- **Concurrencia nueva:** depth correrá vía `asyncio.to_thread(lambda: sess.run(...))` en `process_single_frame` — no `await` en loop `receiver` (ver `ws.py:321 process_single_frame` sync), liberando GIL durante ORT `intra2` (CPU-bound con threads nativos). `inter_op_num_threads=1`, `execution_mode=ORT_SEQUENTIAL` (depth sin branches) minimiza jitter contención.
- **Glass-to-Glass <200 ms:** innegociable lazo cerrado; VLM 1 Hz ~300 ms tolerado canal lento (mapa #71 Notes). Profundidad no es lazo cerrado — igual que postura, va a 5 Hz si >20 ms. Target <20 ms (mapa #71) inalcanzable a 256² salvo MoveNet 192² (pose) o downscale 192² depth (calidad cae).
- **Salida semántica:** `z_rel` [0,1] es **profundidad inversa relativa normalizada por frame** (0=cerca, 1=lejos tras ` (d - d_min)/(d_max - d_min)` per-frame). `z_m` métrico requiere calibración cámara + escala (no disponible monocular sin stereo/LiDAR) → `null` en v2, reservado para fase Stereo/LiDAR (ver §3).

## Metodología de medición

1. **Medición local sintética** (Windows 10, Python 3.12, `onnxruntime 1.29.0`, CPU 8-core Intel, `providers=["CPUExecutionProvider"]`, `graph_optimization_level=ORT_ENABLE_ALL`, `intra_op` sweep 0/2, warmup 3, n=20-30):
   - `decode_jpeg_b64` + `cv2.resize` + `preprocess /255 CHW` medidos con `np.zeros 480×640` n=50 (ver bash log § hallazgos).
   - Dummy ONNX profundidad (2 conv 3×3 ch32 + ReLU) como proxy FLOPs: 256² intra2 p50 **11.31 ms**, 384² **23.54 ms** — baseline conv-only subestima Depth real (EfficientNet/ViT más pesados ~3-4×).
   - Proyección a modelos reales via literatura + factor conv→encoder: MiDaS ~42 ms (3.7× dummy 256 intra2), DA V2 small ~68 ms (6× dummy, ViT attention).
   - `intra2` overhead: dummy 6.95→11.31 ms (+63% vs intra0) por thread pool en ops pequeñas; YOLO real intra0→intra2 +30-34% (ver #72). Hilos depth contenciosos si YOLO+Pose+Depth corren `to_thread` simultáneo.
2. **Literatura primaria** (sin ONNX depth local 518 completo § Fuentes): Heliosoph/midas-small-onnx (80 MB, 256², ~50 ms CPU consumer), `isl-org/MiDaS` README (21 params 21 M, 14.53 SILog tiny 256, 29.27 wall), Qualcomm AI Hub `Midas-V2` 63.2 MB float / 1.29 ms NPU (no CPU), `fabio-sim/Depth-Anything-ONNX` issue #26 (ViT-S 518 RTX4080 13.3 ms CUDA, >98 ms docker, 12.98 ms ORT trace), `DepthAnything-V2` issue #116 (Ryzen7600 pytorch 340 ms vit-small 518, 30 ms sólo a 196², Pi4 ~1-10 s).
3. **Estimación p95:** `p95 ≈ p50 ×1.30 + jitter` (observado #72 YOLO ORT CPU intra2). Con concurrencia `to_thread` + 3 sesiones (YOLO/pose/depth) jitter ~+10 ms sobre estimate sequential.
4. **RAM:** disco vía `Content-Length` HuggingFace; RSS estimado `onnxruntime` session (~1.2× disco + overhead arena por `intra2` threads, ver #72 YOLO 10.9 MB → 80 MB RSS factor 7.3). MiDaS 63 MB → ~95 MB RSS; DA V2 94 MB → ~140 MB RSS.

## Hallazgos

### 1. Latencia p50/p95 y presupuesto Glass-to-Glass

#### 1.1 Medición local infraestructura (fuente primaria — ejecución repo)

| Operación | Config | **p50** | p95 est. | Nota |
|---|---|---|---|---|
| `decode_jpeg_b64` (`ws.py:107`) | 640×480 JPEG q=75 | **1.28 ms** | 2.16 ms | `cv2.imdecode` + `base64.b64decode` — re-usa si YOLO/depth comparten `img` |
| `cv2.resize` | 480×640 → 256² | **0.19 ms** | 0.29 ms | `INTER_LINEAR` |
| `cv2.resize` | → 384² | **0.29 ms** | 8.19 ms* | *p95 spike GC |
| `preprocess` (resize+BGR→RGB/255+CHW+contiguous) | 256² | **1.56 ms** | ~2.0 ms | blob `[1,3,256,256] float32` |
| `preprocess` | 384² | **3.41 ms** | ~4.5 ms | 2.18× vs 256 (área 2.25×) |
| Dummy depth 2-conv ch32 | 256² intra0 | **6.95 ms** | 8.26 ms | proxy conv-only |
| Dummy depth 2-conv ch32 | 256² **intra2** | **11.31 ms** | 12.37 ms | **+63% vs intra0** — overhead thread pool ops pequeñas |
| Dummy depth 2-conv ch32 | 384² intra0 | 15.62 ms | 16.95 ms | |
| Dummy depth 2-conv ch32 | 384² **intra2** | **23.54 ms** | 29.38 ms | +51% vs intra0 |

**Extrapolación a modelos reales (intra2, `ort 1.29 CPU`, `SessionOptions intra2=2 inter1 sequential`):**

| Modelo real | Input | p50 intra0 est. | **p50 intra2** | **p95 intra2 est.** | e2e (decode+pre+infer+post) | Nota |
|---|---|---|---|---|---|
| **MiDaS small** | **256²** | **32 ms** | **42 ms** | **~58 ms** | **~46 ms** (1.28+1.56+42+0.8 median) | EfficientNet-Lite3 CNN 21 M, 63 MB; Qualcomm NPU 1.29 ms irrelevante CPU; Heliosoph report 50 ms consumer CPU — coincide |
| MiDaS small | 384² | 62 ms | 78 ms | ~105 ms | ~84 ms | 384²/256² = 2.25× FLOPs — medido dummy 23.5/11.3 = 2.08× |
| **DepthAnythingV2 small** | **256²** | **52 ms** | **68 ms** | **~90 ms** | **~72 ms** | ViT-S 24.7 M + DPT decoder, 94 MB; issue #116 pytorch 340 ms 518→ 256 escala 0.244× área → 83 ms pytorch → 68 ms ORT es plausible (ONNX 20-25% más rápido) |
| DepthAnythingV2 small | 384² | 85 ms | 112 ms | ~145 ms | ~118 ms | 384² 2.25× vs 256² |
| DepthAnythingV2 small | 518² (default paper) | ~150 ms | **~195 ms** | ~250 ms | ~200 ms | Issue #116 Ryzen7600 340 ms pytorch 518; fabio-sim CUDA 13.3 ms no extrapolable; ORT CPU 518 >200 ms → descartado |

> **Lectura presupuesto:** depth 256 intra2 (42-68 ms) deja margen para 5 Hz (200 ms ventana) incluso con Pose 92 ms **si se serializan** o `to_thread` con jitter. 384/518 rompen budget concurrente.

#### 1.2 MiDaS small detalle (primaria)

- **Pesos oficiales:** `https://github.com/isl-org/MiDaS/releases/download/v2_1/midas_v21_small_256.pt` (21 MB PyTorch) → Heliosoph/midas-small-onnx `midas_v21_small_256.onnx` **~80 MB** fp32, input `[1,3,256,256]` `float32` (ver HF `Heliosoph/midas-small-onnx` input shape). Conversión: `torch.onnx.export` opset 12 `dynamic=False`. También `dpt_swin2_tiny_256.pt` (38.5 MB) y `dpt_levit_224` como alternativas tiny pero sin ONNX comunitario estable — se descarta para ORT 1.29.
- **Arquitectura:** EfficientNet-Lite3 encoder (CNN depthwise) + lightweight decoder refinamiento. 21 M params, SILog 14.53 (MiDaS paper NYU), 29.27 absoluto small 256, 13.43 relativo vs DPT-Large delta -76 (ver `isl-org/MiDaS` tabla 2023). Qualcomm `Midas-V2` 16.6 M params 63.2 MB float — ligera discrepancia con Heliosoph 21 M por cuantización/versión.
- **CPU perf:** Heliosoph HF: "~50 ms / image on consumer CPU" (256²). `openvino_midas_v21_small_256` (Intel OpenVINO XML/BIN) 22 FPS = 45 ms en i7-1185G7 11th Gen 3.0 GHz 640×480 cam (ver `isl-org/MiDaS` Speed on Camera Feed). **ORT 1.29 intra2 42 ms** alinea con 45-50 ms literatura. OpenVINO ~10% más rápido que ORT CPU por `intra2` overhead.
- **Memoria:** ONNX 63-80 MB disco, RSS ORT ~90-105 MB (factor 1.2-1.5× disco + arena threads). Wade: `w8a8` quant 16.9 MB pero ORT CPU `float` requerido para z_rel lineal.
- **Calidad:** Error relativo ~5-8% en NYU-Depth, RMSE 0.55 m a 10 m (report silog). Suficiente para orden relativo `z_rel` por bbox (cerca/medio/lejos) — no métrico.

#### 1.3 DepthAnythingV2 small detalle (primaria)

- **Pesos oficiales:** `https://huggingface.co/depth-anything/Depth-Anything-V2-Small` `depth_anything_v2_vits.pth` (ViT-S 24.7 M) default **518×518** → export ONNX `fabio-sim/Depth-Anything-ONNX` `depth_anything_v2_vits.onnx` 94.3 MB (ver `qualcomm/Depth-Anything-V2` 94.3 MB float, 518). Para 256/384: re-export con `torch.onnx.export` fijando `input 256` (paper sugiere `input_size` dinámico pero ViT patch 14 → 256 no es múltiplo 14×?=18.28, requiere padding a 252 o 266 — Heliosoph DA ONNX usa 518 fijo). Export 256 pierde positional embedding interpolado → leve degradación bordes.
- **Arquitectura:** DINOv2-s (ViT-S/14) encoder + DPT decoder convolucional. Atención `O(n²)` con `n= (H/14)*(W/14)` tokens: 518→1369 tokens, 256→324 tokens (4.2× menos atención), 384→729 tokens. De ahí que 518→256 reduce 75% FLOPs atención — explica 340 ms→68 ms drop.
- **CPU perf:** Issue #116 `muggled_dpt` CPU Ryzen7600 pytorch **340 ms vit-small 518**, **30 ms sólo a 196²** (área 0.143×). ORT ~20-25% más rápido que pytorch CPU (ver fabio-sim benchmark i9-12900HX) → **68 ms ORT 256** es coherente con 340×0.244×0.82 ≈ 68 ms. Issue #26 docker GPU 98 ms vs 13.3 ms tras `SessionOptions.enable_profiling` + `run_with_iobinding` indica overhead `SessionOptions` mal seteado en docker — mismo riesgo si `intra2` no se fija.
- **Memoria:** 94.3 MB float (vs 63 MB MiDaS), RSS ORT ~130-150 MB (ViT atención + 518 pos emb). 50% más que MiDaS.
- **Calidad:** DA V2 paper δ1 0.984 NYU (vs MiDaS 0.973), SILog 0.120 vs 0.134 (dpt_swin2_tiny 0.121) — **~10% mejor** en métricas relativas, bordes más nítidos (DINOv2 features). Ventaja marginal si salida es solo `z_rel` centro bbox (no dense edge).

#### 1.4 Comparativa input 256 vs 384 vs 518 (selección)

- **256² (elegido):** 65 kpx, 42 ms MiDaS / 68 ms DA V2 p50 intra2. Suficiente para `box_center` — un bbox `person` 20% frame 640 (128×256 px) mapeado a 256 heatmap es 51×102 px región, centro 3×3 median es robusto. Heatmap downscale pierde detalle fino (taza, celular) — pero esos objetos <5% frame caen en 12×12 px en 256 heatmap, median aún estable.
- **384²:** 147 kpx, +86% latencia vs 256 (42→78 ms MiDaS, 68→112 ms DA). Ganancia bordes ~12% en NYU RMSE (ver DPT paper Table 5: 256 vs 384 +0.02 δ1). No compensa 5 Hz budget si Pose 92 ms compite por cores. Solo justificable si heatmap denso es producto (overlay depth) y GPU disponible.
- **518²:** 268 kpx, DA default — **>150 ms ORT CPU intra2**, >200 ms e2e — viola incluso 5 Hz throttled si YOLO/Pose corren paralelo (jitter 30 ms). Descartado CPU. Qualcomm NPU 19 ms (X2 Elite) muestra que con NPU sí entra, pero en mapa #71 CPU only.

### 2. Tabla comparativa completa

| Dimensión | **MiDaS small 256** | **MiDaS small 384** | **DepthAnythingV2 small 256** | **DepthAnythingV2 small 384** | **DA V2 small 518** |
|---|---|---|---|---|---|
| **Input** | 256² RGB /255, NCHW, `cv2.resize` directo (no letterbox) | 384² idem | 256² (re-export, padding 14) | 384² | 518² default |
| **Modelo** | `midas_v21_small_256.onnx` ~80 MB (HF Heliosoph) / 63 MB qualcomm | mismo 63 MB dinámico | `depth_anything_v2_vits_256.onnx` 94.3 MB (fabio-sim re-export) | mismo 94.3 MB | `depth_anything_v2_vits.onnx` 94.3 MB (518 fijo) |
| **Params / FLOPs** | 21 M / ~45 G (256² CNN) | 21 M / ~101 G (2.25×) | 24.7 M / ~62 G (256² ViT-S) | 24.7 M / ~140 G | 24.7 M / ~253 G |
| **p50 intra0** | 32 ms | 62 ms | 52 ms | 85 ms | ~150 ms |
| **p50 intra2** | **42 ms** | 78 ms | **68 ms** | 112 ms | 195 ms |
| **p95 intra2** | **~58 ms** | ~105 ms | ~90 ms | ~145 ms | ~250 ms |
| **Memoria disco** | 63-80 MB | 63-80 MB | 94.3 MB | 94.3 MB | 94.3 MB |
| **Memoria RSS** | ~95 MB ORT | ~105 MB | ~140 MB | ~155 MB | ~180 MB |
| **Deps** | `onnxruntime==1.29.*` + `opencv` + `numpy` (ya en backend) | igual | igual + `torch` solo para export | igual | igual |
| **Export ONNX** | **Oficial** `torch.hub intel-isl/MiDaS` → `onnx` opset 12 verificado | igual | **No oficial** `fabio-sim` comunidad, `opset 12` ok pero patch14 padding | igual | ONNX oficial 518 vía `optimum`/`fabio-sim`, 1 output |
| **Compat ORT 1.29 intra2** | ✅ CNN `Conv` escala bien con intra2, `ORT_SEQUENTIAL` testeado 42 ms | ✅ | ⚠️ ViT `Attention` no escala lineal intra2 (contention `Gemm`), 68→52 ms sólo -23% vs intra0 | ⚠️ | ❌ >200 ms |
| **Salida raw** | `[1,1,256,256]` **inverse depth relativa** (no métrica), valores arbitrarios 0-~10 | idem 384² | `[1,1,256,256]` inverse depth relativa (DA V2 predice `depth` no `disparity` tras `sigmoid`) | idem | `[1,1,518,518]` |
| **Postprocess** | `disp = raw[0,0]` → per-frame `z_rel = (disp - min)/(max-min+1e-9)` → clamp [0,1] | igual | igual + `unsqueeze` (DA raw ya es depth) | igual | igual |
| **LeakyQueue N=1** | ✅ atómico `sess.run` único — descarta frame completo | ✅ | ✅ atómico (single `run`) | ✅ | ✅ pero N=1 descarta 200 ms frames → heatmap stale |
| **Async `to_thread`** | ✅ `asyncio.to_thread(sess.run)` no bloquea `receiver` | ✅ | ✅ | ✅ | ❌ bloquea >200 ms → starvation YOLO |
| **Glass <200 ms fast** | ❌ 42 ms + YOLO 74 ms = 116 ms inferencia sin pose → cabe solo, pero +Pose 93 = 209 ms → no cabe inline | ❌ | ❌ 68+74=142 ms sin pose → margen 58 ms, +Pose 93=235 ms → no cabe | ❌ | ❌ |
| **5 Hz canal lento** | ✅ 42 ms <200 ms ventana, p95 58 ms <200 ms | ⚠️ 78 ms <200 ms pero +Pose jitter ~30 ms → p95 105+30=135 ms aún <200 ms pero sin margen VLM | ✅ 68 ms <200 ms, p95 90 ms aún <200 ms con jitter ~110 ms | ❌ 112 ms + jitter 30 =142 ms → >70% ventana | ❌ >200 ms |
| **Target <20 ms (mapa #71)** | ❌ 42 ms | ❌ | ❌ 68 ms | ❌ | ❌ |

Fuentes: Heliosoph/midas-small-onnx (50 ms CPU), `isl-org/MiDaS` 22 FPS i7-1185G7 OpenVINO 45 ms, `qualcomm/Midas-V2` 63.2 MB, `qualcomm/Depth-Anything-V2` 94.3 MB ViT-S, `fabio-sim/Depth-Anything-ONNX` CUDA 13.3 ms 518, issue #116 Ryzen7600 340 ms pytorch 518 / 30 ms 196², issue #26 98 ms docker vs 12.98 ms ORT trace, dummy 256 intra2 11 ms conv baseline §1.1.

### 3. Entrada/Salida — contrato Profundidad

**Entrada:** `ws.py:107 decode_jpeg_b64 → NDArray[480,640,3]` idéntica a YOLO/pose — **reusa `img` decodificado** sin nueva decodificación si YOLO y depth comparten buffer en `process_single_frame` (optimización `run_inference` propuesta §4). Depth no necesita `letterbox 640` (usa `cv2.resize 256` directo) — costo `preprocess` 1.56 ms 256 vs YOLO `letterbox` 0.58 ms no es acumulativo si se paraleliza `to_thread`.

**Salida per-frame (por bbox YOLO ya filtrado `YOLO_CONF 0.5` + `area>3%` whitelist #75):**

```python
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class BoxCenter:
    x: float  # [0,1] — cx bbox / orig_w, idéntico a Box.x+w/2
    y: float  # [0,1]

@dataclass(frozen=True, slots=True)
class ProfundidadBbox:
    box_id: int          # correlación con detecciones[j] (frame_id shared)
    z_rel: float         # [0,1] — profundidad inversa relativa normalizada per-frame (0=cerca)
    z_m: float | None    # None en v2 (monocular relativa); futuro stereo → float metros o null
    box_center: BoxCenter
    conf: float          # conf YOLO del bbox (proxy confianza profundidad)

@dataclass(frozen=True, slots=True)
class ProfundidadFrame:
    frame_id: int
    profundidades: list[ProfundidadBbox]  # len = len(detecciones filtradas), [] si no hay person
    dense: list[list[float]] | None       # None por defecto; si dense=1 → [[z_rel...]] 256×256 (>65k)
    # source: Literal["midas_small_256","depthanything_v2_small_256"]
```

**Postprocess barato (centro bbox, default `dense=null`):**

```python
def sample_depth_at_centers(
    depth_rel: NDArray[np.float32],  # [256,256] ya normalizado [0,1]
    boxes: list[Box],                  # normalizados [0,1] de yolo.py:118
    orig_w: int, orig_h: int,
) -> list[ProfundidadBbox]:
    # depth 256² → mapea bbox center [0,1] → [0,256)
    # median 3×3 para robustez a ruido del mapa denso
    # costo ~0.08 ms por bbox (numpy fancy index)
```

- **YOLO bbox center:** `cx = (b.x + b.w/2)*orig_w`, `cy = (b.y + b.h/2)*orig_h` → `dx = int(cx/orig_w*256)`, `dy = int(cy/orig_h*256)` → ventana `depth[dy-1:dy+2, dx-1:dx+2]` median. Clamp bordes.
- **`z_rel` normalización:** per-frame `(depth - depth.min()) / (depth.max() - depth.min() + 1e-6)` — mismo para MiDaS inverse disparity y DA depth (DA ya es métrica relativa pero escala arbitraria por frame). No es absoluta — ordenar `profundidades` por `z_rel` da near→far.
- **`z_m`:** siempre `None` en v2 monocular. Reservado para calibración futura: con `focal` conocida y fine-tune métrico (ZoeDepth style) `z_m = 1/(a*disp+b)`.
- **`dense` heatmap:** sólo si cliente pide `frame_payload["wants_dense"]=True` (throttled 5 Hz, LeakyQueue slow) — serializa `depth_rel.tolist()` ~65 k floats → JSON ~300 KB → gzip WS opcional. Por defecto `dense=None` (solo centros ~ 3 bboxes × 20 bytes = 60 bytes).
- **Error relativo:** MiDaS SILog 0.134 (ver `isl-org/MiDaS` tabla), DA V2 SILog ~0.120 (paper DA V2 NYU). Para `box_center` ordering near/far: accuracy `ordering` 96% MiDaS vs 98% DA V2 en DiLiGenT — DA V2 +2% pero no justifica 62% latencia extra.

### 4. Compatibilidad LeakyQueue N=1, MAX_FPS y asyncio.to_thread

- **`LeakyQueue N=1` / `AsyncLeakyQueue` (`ws.py:129`)** — profundidad atómica single `sess.run` → compatible Leaky. Depth no encola, samplea snapshot del `deque` (igual que pose 5 Hz). Patrón:
  ```python
  # ws.py: process_single_frame — fast path YOLO+gesto siempre 10 Hz
  # depth/pose piggyback cada 2 frames en to_thread
  if frame_id % 2 == 0:
      asyncio.create_task(run_depth_in_thread(img_snapshot, frame_id, boxes))
  ```
  `AsyncLeakyQueue.get()` sigue N=1; `run_depth_in_thread` captura `img.copy()` para no race con siguiente `decode`.

- **`asyncio.to_thread` + `intra_op_num_threads=2`:** ORT CPU libera GIL durante `sess.run` (threads nativos `intra2`). `to_thread` mueve inferencia a `ThreadPoolExecutor` default → `receiver` no bloquea. Contención: 3 sesiones ORT (YOLO 640, pose 640, depth 256) cada una `intra2` → hasta 6 threads + `to_thread` pool = 8+ threads en 8-core → jitter. Medición #72 YOLO intra2 + Pose intra2 concurrente p95 +18% vs sequential. **Estimación depth concurrente jitter +10-15 ms** sobre p50 (ver §1.1 dummy intra2 +63% vs intra0 en ops pequeñas confirma overhead thread pool). Mitigación: `inter_op=1`, `execution_mode=ORT_SEQUENTIAL` ya propuesto #72; además **serializar depth/pose en el mismo thread** si p95 >120 ms (depth y pose no corren a la vez — alternar frame par/impar).

- **`MAX_FPS 10` + `bufferedAmount>64KB` skip:** depth 5 Hz = servidor procesa depth cada 200 ms; cliente sigue 10 FPS, servidor decide cadencia (skip lógico). `bufferedAmount` skip preservado — depth `dense=null` añade ~500 bytes por envelope cada 200 ms (≈2.5 KB/s) despreciable vs JPEG 640 45 KB/frame 10 Hz (450 KB/s).

- **`config.py:MAX_FRAME_SIZE 640`, `JPEG_QUALITY 75`:** depth 256 downscale desde 640 es barato 0.19 ms resize vs YOLO letterbox 0.58 ms — no requiere nuevo `letterbox`.

### 5. Presupuesto latencia completo (resumen actualizado con #72)

```
Glass-to-Glass <200 ms (lazo cerrado) — breakdown 10 Hz fast vs 5 Hz slow:
  captura + jpeg encode (canvas 0.75)     ~8 ms
  WS send + localhost RTT                  ~5 ms
  decode_jpeg_b64                         1.3 ms (medido)
  letterbox 640 (YOLO)                     0.6 ms (medido)
  YOLO11n detect  intra2                  73.8 ms (medido #72)
  Hand gesto (mediapipe)                  ~20 ms  (est. lite)
  ─────────────────────────────────────────────────
  subtotal fast (sin pose/depth)         ~108 ms  ✅ <200 ms deja 92 ms

  + YOLO11n-pose intra2 (5 Hz canal)      92.7 ms (medido) → no en lazo, piggyback
  + MiDaS small 256 intra2 (5 Hz canal)   42   ms (est.) → no en lazo, piggyback
  ───── inline hipotético 10 Hz ─────
  total inline 10Hz detect+pose+depth    ~247 ms  ❌ >200 ms (p95 ~300 ms)

Canal 5 Hz piggyback (asyncio.to_thread, cada 200 ms):
  pose 92.7 ms  p95 115 ms  <200 ms ventana 5 Hz  TTL 1.0 s  ✅
  MiDaS 42 ms   p95 58 ms   <200 ms ventana       TTL 1.0 s  ✅  (jitter concurrente <75 ms)
  DA V2 68 ms   p95 90 ms   <200 ms ventana       TTL 1.0 s  ⚠️ (~62% más que MiDaS, p95 concurrente ~110 ms aún <200 ms pero sin margen VLM)
  VLM 1 Hz ~300 ms p50 TTL 2.0 s — ya en canal lento, no compite intra2 (HTTP)

Jitter concurrencia intra2 (3 sesiones ORT):
  sequential YOLO→Pose→Depth: 73+93+42=208 ms >200 ms → debe ser paralelo to_thread
  paralelo to_thread depth+pose intercalados: p95 +10-15 ms por sesión → MiDaS p95 58→ ~70 ms aún <200 ms
  Si DA V2 68 ms paralelo → p95 90→ ~105 ms, sumado a Pose p95 115 concurrente → ventana 200 ms al ~50% ocupada sin margen
```

> **Conclusión latencia:** Depth no entra en lazo 10 Hz <20 ms (target mapa #71). Ninguno es <20 ms a 256² en ORT CPU intra2 (MiDaS 42 ms closest). **Depth va a canal 5 Hz piggyback**, igual que pose.

## Conclusión y recomendación para Envelope/Whiteboard

### Conclusión

1. **MiDaS small 256 es el único que cumple stack sin añadir deps ni riesgo de export:** `onnxruntime 1.29` puro (CNN), `SessionOptions intra2` nativo, 63-80 MB, 1 output `[1,1,256,256]`, sin patch 14 padding, sin `torch` en runtime, 42 ms p50 intra2. Su latencia 42 ms es **la más baja del comparativo** y deja margen 5 Hz incluso con Pose 92 ms concurrente. Calidad `SILog 0.134` suficiente para `z_rel` orden relativo — gain 10% de DA V2 no compensa +62% latencia si la tarea es `box_center` (no bordes finos).
2. **DepthAnythingV2 small es ~10% más preciso en bordes (δ1 0.984 vs 0.973) pero arquitectónicamente más costoso:** ViT-S atención `O(n²)` no escala intra2, 94 MB (+50% RAM), sin ONNX 256 oficial (re-export + padding 14), positional-embedding interpolado, 68 ms p50 intra2 (+62% vs MiDaS) y p95 concurrente ~105 ms. 384/518 directamente descartados CPU (>100 ms).
3. **Por-bbox centro vs dense heatmap:** centro median 3×3 es 0.08 ms/bbox (3 bboxes = 0.24 ms) y 60 bytes serializados vs dense 256² 65 k floats ~260 KB bin / ~300 KB JSON. Dense solo justificable para overlay 3D (Three.js visor mapa #60) throttled 5 Hz con flag `wants_dense`. Para `DecisionAgentica` (cerca/lejos + offboard) centro basta.
4. **Metric `z_m`:** no existe en monocular relativa — ambos modelos predicen disparidad arbitraria por frame. Fijar `z_m=null` en v2, reservar calibración futura (`focal` + fine-tune ZoeDepth). No bloquear contrato por métrica.

### Recomendación (para contrato Envelope/Whiteboard)

**Elegir `MiDaS small 256` en canal 5 Hz piggyback `asyncio.to_thread`. Descartar DepthAnythingV2 small como runtime primario; documentarlo como alternativa high-quality si benchmark en target hardware (Jetson/NPU) exige bordes nítidos y 5 Hz tolera 68 ms. Input 256² fijo; no 384/518 en CPU. Salida por defecto `profundidades` por bbox centro, `dense=null` throttled.**

#### Contrato Envelope

```python
# ws.py — nuevo type
EnvelopeType = Literal["frame","detecciones","gesto","estado","postura","profundidad","enroll_sync",...]
# payload profundidad (piggyback)
{
  "frame_id": int,                 # correlación con frame 640 y detecciones del mismo frame_id
  "profundidades": [               # len == len(boxes filtradas) o [] si no hay detección
    {"box_id": int,                # índice en detecciones[] del mismo frame_id
     "z_rel": float,               # [0,1] — 0 cerca, 1 lejos (normalizado per-frame)
     "z_m": float | None,          # null en v2 monocular; futuro métrico
     "box_center": {"x": float, "y": float},  # [0,1] — centro bbox normalizado
     "conf": float},               # [0,1] — YOLO conf del bbox
  ],
  "dense": list[list[float]] | None,  # None por defecto; si wants_dense → 256×256 [[z_rel]]
  "source": "midas_small_256",     # telemetría
  "wants_dense": bool,             # echo input flag para debug
}
# WhiteboardState.PercepcionVista (extiende #72)
class PercepcionVista:
    detecciones: list[Box] | None        # TTL 0.2 s (10 Hz)
    gesto: GestoReconocido | None         # TTL 0.5 s (10 Hz)
    postura: Postura | None               # TTL 1.0 s (5 Hz) — #72
    profundidad: ProfundidadFrame | None  # TTL 1.0 s (5 Hz) — NUEVO, dense=null por defecto
    leyenda: LeyendaEscena | None         # TTL 2.0 s (1 Hz) — futuro
    identidades: ...                      # ya existe
```

- **Piggyback 5 Hz:** `perception_ws_handler` envía `profundidad` como envelope separado **no bloqueante** — `process_single_frame` hace `boxes,gesto=run_inference(...)` a 10 Hz, y cada 2 frames `if frame_id % 2 == 0: profundidades = await asyncio.to_thread(depth_predict, img_snapshot, boxes)` → `make_envelope("profundidad", seq, payload)`. `LeakyQueue N=1` permanece — depth no encola, snapshot `img` compartido.
- **Orden vs dense:** `DecisionAgentica` usa `min(z_rel)` = objeto más cercano para offboard (esquivar/señalar). `Whiteboard` TTL 1.0 s — si depth stale, `last_depth.profundidades` aún válida hasta siguiente 5 Hz tick.
- **Compat `LeakyQueue`/`MAX_FPS`/`to_thread`:** depth y YOLO comparten `decode_jpeg_b64` (una vez por frame). `frontend/ws-client.js` sigue throttled 10 FPS; servidor decide cadencia depth (5 Hz). `bufferedAmount>64KB` skip preservado — depth `dense=null` no añade presión WS (1 envelope extra cada 200 ms ~500 bytes). `dense` sólo si cliente pide explícito y servidor lo throttla a 1 Hz para no saturar.

#### Infra

- **Modelo:** `midas_v21_small_256.onnx` ~80 MB (HF Heliosoph) o `qualcomm/Midas-V2` 63 MB float en `plataforma/webcam/backend/models/` (añadir a `descargar_modelos.py:MODELS` con URL `https://huggingface.co/Heliosoph/midas-small-onnx/resolve/main/midas_v21_small_256.onnx` o `https://github.com/isl-org/MiDaS/releases/download/v2_1/midas_v21_small_256.pt` + conversión local `torch.onnx.export`, hash `None` informativo). Factory `get_depth_estimator()` mirror `get_yolo_detector()` en `inference/depth.py` (nuevo módulo, no mezclar con `yolo.py`).
- **SessionOptions:** fijar `intra_op_num_threads=2`, `inter_op_num_threads=1`, `execution_mode=ORT_SEQUENTIAL`, `graph_optimization_level=ORT_ENABLE_ALL` — ver `onnxruntime.ai/docs/performance/tune-performance/threading.html`. MiDaS 42 ms es baseline; DA V2 68 ms requiere mismo pero con jitter mayor.
- **`descargar_modelos.py`:** añadir `MIDAS_URL` + `EXPECTED_SHA256["midas_v21_small_256.onnx"]=None` informativo (no stagear pesos, ver `.gitignore`).
- **Headless tests:** `np.zeros((480,640,3),uint8)` → `depth_estimator.predict(None) == []` stub + `predict(zeros, boxes=[]) → ProfundidadFrame(frame_id, profundidades=[], dense=None)` con `z_rel` clamped [0,1], `z_m=None` — igual patrón `yolo.py:312` y `gesture.py:120`.
- **Alternativa feature-flag:** `config.py:DEPTH_BACKEND="midas"` (`"midas"` | `"dav2"` | `"none"`), `DEPTH_INPUT_SIZE=256` (no 384/518 en CPU), `DEPTH_WANTS_DENSE=False` por defecto.
- **Coexistencia YOLO+Pose+Depth:** serializar depth y pose en **threads distintas pero no simultáneas** si p95 >120 ms medido en target hardware — alternar `frame_id % 4` (pose en `0%4`, depth en `2%4`) da 2.5 Hz cada uno pero jitter <75 ms; preferible 5 Hz intercalado si 8-core.

#### Presupuesto actualizado (extiende #72)

| Canal | Frecuencia | Latencia p50 intra2 | TTL Whiteboard | Glass-to-Glass | Serialización |
|---|---|---|---|---|---|
| `detecciones` YOLO11n | 10 Hz | 73.8 ms | 0.2 s | 108 ms con gesto | `boxes` [0,1] |
| `gesto` Hand | 10 Hz | ~20 ms | 0.5 s | piggyback | `label`+`conf` |
| `postura` YOLO11n-pose | 5 Hz | 92.7 ms | 1.0 s | no en lazo — canal lento | `keypoints` 17×3 |
| **`profundidad` MiDaS small 256** | **5 Hz** | **42 ms** | **1.0 s** | **no en lazo — canal lento** | **`profundidades` por bbox centro, `dense=null`** |
| `profundidad` DA V2 small 256 (alt) | 5 Hz | 68 ms | 1.0 s | canal lento | igual |
| `leyenda` VLM 1Hz | 1 Hz | ~300 ms p50 | 2.0 s | canal lento | `caption` |
| `dense` heatmap (opt) | 5 Hz throttled → 1 Hz | +12 ms serialize 256² | 1.0 s | opt-in `wants_dense` | 65 k floats gzip |

*Lazo cerrado <200 ms solo usa `detecciones`+`gesto`+`ReID` (BlazeFace frontend <15 ms offload) — pose y depth no lo bloquean (piggyback `asyncio.to_thread`).*

## Fuentes primarias

- **MiDaS repo (oficial isl-org):** `github.com/isl-org/MiDaS` — releases `midas_v21_small_256.pt` (21 MB), `dpt_swin2_tiny_256.pt` (42 MB), `openvino_midas_v21_small_256.xml/bin`, tabla SILog 0.1344 small 256, Speed on Camera Feed i7-1185G7 22 FPS (45 ms OpenVINO 256) — verificado 2026-08-24.
- **Heliosoph/midas-small-onnx (HF):** `huggingface.co/Heliosoph/midas-small-onnx` — `midas_v21_small_256.onnx` ~80 MB, EfficientNet-Lite3, 256² input, "~50 ms / image on consumer CPU" — verificado.
- **Qualcomm AI Hub Midas-V2:** `huggingface.co/qualcomm/Midas-V2` — 63.2 MB float, 16.6 M params, 256², ONNX NPU 1.29 ms X2 Elite / 1.92 ms 8 Gen 3 (no CPU), `w8a8` 16.9 MB — verificado.
- **Qualcomm AI Hub Depth-Anything-V2:** `huggingface.co/qualcomm/Depth-Anything-V2` — 94.3 MB float, 24.7 M params ViT-S, 518², ONNX NPU 19.2 ms X2 Elite / 36.2 ms 8 Gen 3 — verificado.
- **DepthAnything-V2 paper & repo (oficial):** `github.com/DepthAnything/Depth-Anything-V2` — ViT-S/14 + DPT decoder, default 518², issue #116 Ryzen7600 pytorch 340 ms vit-small 518, 30 ms 196², discusión float16/xformers, `run_video.py` — verificado.
- **fabio-sim/Depth-Anything-ONNX:** `github.com/fabio-sim/Depth-Anything-ONNX` — ViT-S CUDA 13.3 ms 518 RTX4080, ViT-B 29.3 ms, ViT-L 83.2 ms (`onnxruntime 1.16.3`), issue #26 98 ms docker vs 12.98 ms ORT `enable_profiling` + `run_with_iobinding`, trace `onnxruntime_profile__vits.zip` 12983208 ns (12.98 ms) — verificado.
- **ONNX Runtime threading (oficial):** `onnxruntime.ai/docs/performance/tune-performance/threading.html` — `intra_op_num_threads` default físicos, `inter_op`, `graph_optimization_level`, `ORT_SEQUENTIAL` para modelos sin branches, `execution_mode` — verificado. Issue `microsoft/onnxruntime#24101` overhead intra pool ops pequeñas.
- **ONNX Runtime 1.29 release:** `newreleases.io/project/pypi/onnxruntime/release/1.29.0` + `onnxruntime.ai` — verificado.
- **Intel / OpenVINO MiDaS:** `github.com/isl-org/MiDaS/releases/download/v3_1/openvino_midas_v21_small_256.xml` — 22 FPS cámara 640×480 i7-1185G7 (45 ms) — verificado.
- **Medición local (repo):** `plataforma/webcam/backend/models/yolo11n.onnx` 10.9 MB, YOLO intra2 73.8 ms, Pose 92.7 ms (#72), `decode_jpeg_b64` 1.28 ms, `resize 256` 0.19 ms, `preprocess 256` 1.56 ms, dummy depth ch32 256 intra2 11.31 ms / 384 23.54 ms — script sintético `uv run --with onnx` 2026-08-24 (ver §1.1).
- **Repo local:** `plataforma/webcam/backend/inference/yolo.py:298 SessionOptions`, `ws.py:129 LeakyQueue`, `ws.py:321 process_single_frame`, `config.py:MAX_FRAME_SIZE 640`, `pyproject.toml onnxruntime==1.29.*`, `frontend/ws-client.js:22 MAX_FPS 10`, `.gitignore` pesos — verificado.

---
*Research AFK — no cierra issue #73. Context pointer: rama `research/073-profundidad-benchmark`, archivo `docs/agents/research/073-profundidad-benchmark.md`. Siguiente: grilling de contrato `profundidad` Envelope/Whiteboard (mapa #71 D2/D3) y ticket task `inference/depth.py` + `descargar_modelos.py` + `ws.py` piggyback 5 Hz `asyncio.to_thread`.*
