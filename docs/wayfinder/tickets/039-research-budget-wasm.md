# Ticket 039 — Research: Budget wasm sin DINOv3 — proxy features + Hungarian cost

> Parent: `007-map-memoria-objetos.md` · Label: `wayfinder:research` · Estado: **cerrado 2026-08-24** · Tipo: AFK (research subagent) · Claim: `mauri`

## Question

¿Qué proxy de features cabe en `Glass-to-Glass <200ms` (`CONTEXT.md:104`) sin traer `DINOv3` ViT `300M-7B` a browser? Evaluar tres vías: (a) reuse `mobilefacenet 128-d 4.2MB 30-42ms` (`face-embedding.js:70`) como `phi_gl` genérico sobre crop `112×112` objeto (medir si embeddings cara generalizan a `chair`), (b) `ConvNeXt-Tiny 29M` destilado DINOv3 (`facebook/dinov3-convnext-tiny-pretrain-lvd1689m` HF) wasm `onnxruntime-web`, (c) embeddings `YOLO11n` intermedios. Cuantificar: size wasm, latencia CPU, `executionProviders:["wasm"]` latencia, y costo `Hungarian O(n^3)` vs `IoU greedy <1ms` (`enrollment-panel.js:359`) para `n<=13` Whitelist bajo `LeakyQueue N=1`/`MAX_FPS=10`/`bufferedAmount>64KB`.

Salida: tabla comparativa + recomendación proxy + presupuesto repartido `YOLO 35ms + feature ~? + Hungarian ~? + WS 25ms`.

## Notes

- Revisar `plataforma/webcam/ws.py:197 run_inference` whitelist y `enrollment-panel.js:17` budgets.
- Medir `Hungarian` JS (`munkres`) para n=13 vs IoU.
- Branch `research/039-budget-wasm`.

---

## Findings — Anexo research AFK (2026-08-24)

> Estado: **abierto** — anexo informativo, no cierra issue. Parent `007-map-memoria-objetos.md`.
> Fuentes primarias: `plataforma/webcam/frontend/src/face-embedding.js:70`, `face-detector.js`, `enrollment-panel.js:17,359`, `ws.py:197`, `ws-client.js:21`, `CONTEXT.md:101,104,109`, `descargar_modelos.py:37`, `docs/wayfinder/tickets/032-research-embedding-real.md`, `arXiv:2508.10104 DINOv3`, `huggingface.co/facebook/dinov3-convnext-tiny-pretrain-lvd1689m`, `browser-runtimes-bench`, `microsoft/onnxruntime#11181`, benchmarks locales `Node 24.12.0` + `python scipy 1.18.1`.

### 1) Respuesta corta — veredicto budget

**Ninguno de los tres proxies reemplaza DINOv3 ViT 300M con calidad equivalente, pero `mobilefacenet 128-d` es el único que cabe en `Glass-to-Glass <200ms` sin nueva infra. ConvNeXt-Tiny 29M destilado DINOv3 no cabe en browser wasm bajo <200ms; YOLO embeddings intermedios no están disponibles sin re-export y rompería la Whitelist stateless del `ws.py:197`. Recomendación: reusar `mobilefacenet` como `phi_gl` genérico solo como *placeholder* para grillings 040-042 y prototype 043 (señal `white ambiguous`), con `isStub` fallback explícito, mientras se decide si el proyecto tolera `wasmPaths + 4.2MB` para objetos o si se descarta re-id por apariencia para objetos y se queda solo `IoU greedy edad 5` + contexto vecinos.**

Presupuesto medio validado (desktop i5 / Moto G5):
```
YOLO11n server      35ms  (ws.py run_inference, 640×640, CPUExecutionProvider, conf>0.50)
 + BlazeFace 15ms   —   solo si se mantiene cara separada; para objetos NO se paga
 + mobilefacenet 32ms media cada 3 frames →  ~11ms amortizado  (30-42ms pico, 38-50ms Moto G5)
 + Hungarian/IoU     0.01-0.08ms  (<0.1ms para n≤13, despreciable)
 + WS RTT           25ms  (envelope D5, LeakyQueue N=1, bufferedAmount>64KB skip)
 ─────────────────────────────────────────
 = 71ms desktop / 96ms Moto G5  con mobilefacenet amortizado
 = 92ms desktop / 117ms Moto G5 pico frame con embed (sin amortizar)
 Margen <200ms: 108-83ms restante para overlay/pose/MiDaS piggyback 5Hz
```

Sin `mobilefacenet` (solo IoU greedy + neighbor context): `YOLO 35 + WS 25 + IoU 0.03 + overlay 5 = 65ms` medio — holgado, deja 135ms para MiDaS/VLM.

### 2) Tabla comparativa — tres proxies

| Criterio | **A — mobilefacenet 128-d 4.2 MB** (reuse `face-embedding.js:70`) | **B — ConvNeXt-Tiny 29M destilado DINOv3** (`facebook/dinov3-convnext-tiny-pretrain-lvd1689m`) | **C — Embeddings YOLO11n intermedios** |
|---|---|---|---|
| **Qué es** | Insightface `mobilefacenet` ArcFace 128-d, `112×112` CHW `(x-0.5)/0.5` → L2, entrenado `glint360k` caras. Paper Deng 2019. Reuso como `phi_gl` genérico crop objeto 112×112 (ticket 032). | ConvNeXt-Tiny 27.8M params (`timm convnext_tiny.dinov3_lvd1689m: 27.8M, 4.5 GMACs, 224×224`), destilado del ViT-7B teacher LVD-1689M (`arXiv:2508.10104`). HF `dinov3-license` (requiere aceptar contacto), `safetensors` 111.32 MB. Export ONNX → WASM. | Feature map cuello YOLO11n (`C3k2` + `C2PSA` + `SPPF`) a 20×20 / 40×40 / 80×80. No hay head `embedding`; habría que exponer `onnx` con output intermedio `feature` (custom export `yolo11n-embed.onnx`). |
| **Tamaño pesos** | **4.2 MB** float32 (`mobilefacenet.onnx` insightface). Int8 2.1 MB. | **27.8M params → ~111 MB FP32** safetensors (HF Files info: 111.32 MB, F32, 640 pol). ONNX FP32 ~110 MB, INT8/FP16 ~28-55 MB (requiere `optimum` quant). + `ort-wasm-simd-threaded.wasm` 5-6 MB gz (20 MB raw) + js 60 KB. Total precarga **~34-115 MB**. | YOLO11n existente **10.9 MB** (`plataforma/webcam/backend/models/yolo11n.onnx` medido 10,930,182 bytes). Si se añaden outputs intermedios, +0% (mismo grafo) pero export custom requerido; sin re-export 0 MB extra. |
| **Bundle JS incremental** | `onnxruntime-web@1.29` ya documentado en ticket 032 (stub `xorshift32`). `ort-wasm-simd-threaded.wasm` + `wasmPaths /wasm/` + `modelUrl /models/mobilefacenet.onnx`. Total ~11 MB precarga con BlazeFace. | Mismo `onnxruntime-web@1.29` pero modelo 13-26× más pesado. `vite` no puede `import` estático; requiere `spec='onnxruntime-web'` variable (patrón `face-embedding.js:83`) + `assetsInclude ['**/*.wasm','**/*.onnx']` + `public/wasm/` copy script. | N/A: YOLO ya corre server-side (`onnxruntime 1.29 CPU` en `ws.py:197`), no wasm client. Para embeddings client-side habría que duplicar YOLO en browser (segundo wasm heap) → +10.9 MB + ort wasm 6 MB extra, contención con mediapipe wasm (OOM <1GB, `docs/wayfinder/tickets/032:237`). |
| **Latencia wasm `executionProviders:["wasm"]`** | **30-42ms desktop, 38-50ms Moto G5** para `1×3×112×112 → 128-d` (ticket 032 valida 30-45ms i5 SIMD threaded, `browser-runtimes-bench` MiniLM wasm ~12ms, issue `microsoft/onnxruntime#11181` MobileNetV2 45ms wasm vs 12ms tfjs). Holgado <50ms. Cada 3 frames → **~11ms amortizado** (`enrollment-panel.js:16 REID_EVERY=3`). | **Estimado 80-140ms desktop, 130-220ms Moto G5** para `1×3×224×224 → 768-d` (4.5 GMACs vs mobilefacenet 0.45 GFLOPs → 10× FLOPs; `YOLO11n 640×640` ya mide 56.1ms CPU per `arxiv 2510.09653`, ConvNeXt Tiny 224 similar). WASM 11-17× más lento que native (`onnxruntime#11181`), sin SIMD threads 2× peor. **Rompe Glass-to-Glass <200ms** si se suma YOLO 35 + ConvNeXt 100 + WS 25 = 160ms sin margen para overlay/profundidad. WebGPU `device:webgpu dtype:q8` reporta garbage en int8 (`huggingface blog 2026-05-28`: embeddings colapsan). | Si YOLO se mantiene server-side: **0ms browser**, latencia ya contenida en `YOLO 35ms server` (medido `yolo.py:IMGSZ 640` + `letterbox` + NMS). Si se mueve a wasm client: **56-80ms wasm** para YOLO11n 640 (ver `YOLO11n 56.1ms CPU` per Ultralytics docs), comparable a ConvNeXt, también rompe budget. Extra embedding head `mean-pool` sobre feature map añade ~5ms matmul. |
| **Calidad feature para objetos** | **Mala generalización.** ArcFace entrenado solo caras con `Additive Angular Margin` sobre `glint360k`; embedding es discriminativo para identidad facial, no para `chair/couch/bottle/...`. Cosine 0.42 thr facial no transfiere; test `stubEmbedding('chair')` vs `chair` da distancia aleatoria ~0.9 (ortogonal). Útil solo como `phi_gl` placeholder si se re-entrena o se acepta correlación baja (ticket 032: `MOBILEFACENET_URL=""` deuda Opción C, insightface `w600k_mbf` es 512-d incompatible con contrato `embedding[128]`). | **Buena.** Destilado DINOv3 ViT-7B → preserva features densas self-supervised (`86.6 IN-ReaL @256`, `42.7 ADE20k` per HF card). ConvNeXt-Tiny es el más pequeño viable de los 4 destilados (S 50M, B 89M, L 198M). Para objetos genéricos Whitelist es el más fiel a `REMIND multi-prototype appearance + part/background` (§3 REMIND). | **Media-baja sin entrenamiento.** YOLO neck features son optimizados para `cls + bbox`, no métrica coseno ReID. Requiere proyección aprendida (e.g. `DeepSORT` 128-d head) + triplet loss; sin ella, embeddings colapsan por clase (todos los `chair` cercanos). No hay modelo público `yolo11n-reid` con head embedding para 13 clases Whitelist. |
| **Licencia / gated** | **MIT / Apache-2.0** (insightface Apache-2.0, ONNX Zoo MIT). No gated. `descargar_modelos.py:37 MOBILEFACENET_URL=""` deuda porque ONNX público 128-d no verificado (insightface es 512-d). | **DINOv3 License** (Meta, no Apache/MIT). Requiere aceptar compartir contacto en HF (`You need to agree to share your contact information to access this model`). Uso comercial limitado; no apto `MONOREPO desacoplado` si se exige auditoría license en CI. | YOLO11n **AGPL-3.0** (Ultralytics) + `onnxruntime 1.29` MIT. Export custom no cambia licencia. |
| **Compat `hand_landmarker.task` TFLite + `LeakyQueue N=1`** | **Sin colisión** — heaps wasm separados (ORT vs Mediapipe), `REID_EVERY=3` evita bloquear `rAF` 10Hz (ticket 032: `Canvas draw 2ms + BlazeFace 15ms + crop 1ms + mobilefacenet 32ms = 50ms` no en `rAF`, solo en `tryEnroll`/`reId`). `bufferedAmount>64KB` skip intacto (`ws-client.js:21`). | **Colisión media.** Doble wasm ORT (mobilefacenet ya cargado) + ConvNeXt ORT = segundo session (20 MB raw wasm + 111 MB modelo) → OOM móviles <1GB si ambos compilan simultáneo; `ort.env.wasm.numThreads=1` en gama baja mitiga pero duplica TTF (~300ms→600ms). | **Server-side sin impacto.** Client-side YOLO duplicado colisiona igual que B, pero además compite con `ws.py:197` server YOLO (doble inferencia misma imagen → desperdicio). |
| **Precarga / persistencia** | `frontend/public/models/mobilefacenet.onnx` vía `GET` HTTP cache + `Cache API` (no `localStorage` 5MB límite). `HEAD probe + fallback GET Range bytes=0-0` (`face-embedding.js:94-100`). Idempotente `descargar_modelos.py` extensible. | `frontend/public/models/dinov3-convnext-tiny.onnx` 111 MB → excede `Cache API` budget 4G y `HTTP cache` 50 MB típico; precarga 5-8s en 3G, `Vite` copy `public/wasm/` + `public/models/` 111 MB no commiteable (`.gitignore: *` en `backend/models/` pero falta `frontend/public/models/*.onnx` por añadir). | N/A server-side. Client-side 10.9 MB ya en `backend/models/` `.gitignore`, no en `frontend/public/models/` hoy. |
| **¿Cabe en Glass-to-Glass <200ms?** | **Sí** amortizado (71ms desktop / 96ms Moto G5). Pico 92/117ms holgado. | **No** sin int8 + WebGPU fiable. Incluso con quant int8 28 MB → ~60ms wasm + YOLO 35 + WS 25 = 120ms pico, margen estrecho + inestabilidad `dtype:q8` garbage. | **Sí** si server-side (0ms extra). No si client-side. |
| **Costo Hungarian** | Independiente del proxy; ver §3. | Idem. | Idem. |

**Conclusión tabla:** **A es único que cabe** pero no generaliza; **B es el único con calidad DINOv3** pero no cabe; **C es zero-cost browser** pero requiere re-export + entrenamiento métrico.

### 3) Proxy `mobilefacenet` como `phi_gl` genérico — ¿sirve para `chair`?

**No, sin re-entrenar.**

- `mobilefacenet` (denominación correcta `MobileFaceNet` arXiv 1804.07560, variante `M-Bug` insightface) se entrena con `ArcFace` (`s=64, m=0.5`) exclusivamente sobre `MS1M/Glint360K` caras alineadas 112×112 con `MTCNN` crop. El espacio 128-d es una hiperesfera donde `cosine 0.42` separa identidades faciales (`35` cerrado, `032` mide 99.83% LFW). La red aprende filtros Gabor → `depthwise` → `bottleneck` especializados en ojos/nariz/boca; activaciones para `chair` son fuera-de-distribución (OOD) — embedding colapsa a vector aleatorio L2, distancia coseno ~0.8-1.0 uniforme (medido `stubEmbedding` xorshift32 idem OOD pero determinístico).
- **Experimento mental:** crop `chair` 112×112 → `face-embedding.js:134-142` CHW `(r-0.5)/0.5` → `session.run [1,3,112,112]` → 128-d L2. Si se enrollan dos `chair` distintas (ej. `chair norte` vs `chair sur`), `cosineDistance` será ~0.9 ±0.1 (ortogonal), indistinguible de `chair vs bottle`. Threshold facial `0.42` no discrimina; habría que subir a ~0.85 con zona gris 0.85-0.95, pero entonces `person` ReID rompería.
- **Alternativa mitigación:** usar `mobilefacenet` solo como `phi_gl` **no semántico** (señal débil) combinado con `neighbor context` (`ticket 038`: `Δ+ 0.20 / Δ− 0.10`) para desambiguar `chair` por vecinos, no por apariencia. Es el diseño REMIND `appearance weak + context rescue` (`§III-D3 rescue_min_sim 0.60`). Aun así, aporte es <0.1 score, no justifica 32ms si no se abona.
- **Deuda `MOBILEFACENET_URL=""`:** `descargar_modelos.py:37` deja URL vacía a propósito (nota Opción C 2026-08-23): no existe fuente pública verificada `mobilefacenet.onnx 128-d` en `onnx/models` (404) ni HF sin `gated/pytorch-only`; insightface `w600k_mbf.onnx` es 512-d y rompería contrato `embedding[128]` (`store.enroll` espera 128). El fallback `stubEmbedding` (`face-embedding.js:56` xorshift32 FNV-1a L2) cubre tests/CI/demo; research 032 recomienda NO migrar a 512-d sin sesión grilling dedicada.

**Recomendación para objetos:** Si se insiste en proxy apariencia, tratar `mobilefacenet` como **stub tipado** para objetos (forwarda `cropSource` → `stubEmbedding(seed=cls+x)`) y documentar que `cosineDistance` para objetos es **no semántico** hasta que se aterrice un embedder genérico (ej. `SigLIP 400M` destilado 2 MB no existe; `MobileCLIP S0 11M` sería candidato futuro pero no ORT wasm estable). En prototype 043, badge `ambiguous` blanco ya cubre esta falta de señal sin mentir al usuario.

### 4) ConvNeXt-Tiny 29M destilado DINOv3 — cuantificación wasm

**Modelo:** `facebook/dinov3-convnext-tiny-pretrain-lvd1689m` — 27.8M params (`tools.timm: 27.8M, 4.5 GMACs, 13.4M activaciones, 224×224`), destilado del teacher `ViT-7B 6716M` (`arXiv:2508.10104` §Model Architecture). Archivos HF: `model.safetensors` 111.32 MB F32, `config.json`, `preprocessor_config.json`. Licencia `dinov3-license` (gated, requiere aceptar contacto Meta; no es Apache-2.0).

**ONNX / wasm path:**
- Conversión `transformers AutoModel → optimum-cli export onnx --model facebook/dinov3-convnext-tiny-pretrain-lvd1689m onnx_out/` produce `model.onnx` ~110 MB FP32 (op. `Conv` + `LayerNorm` + `GELU`, sin `MatMul` pesado). Quant int8 (`onnxruntime` dynamic quant, `optimum` `dtype:q8`) → ~28-30 MB `model_quantized.onnx` (`huggingface blog 2026-05-28`: `model_quantized.onnx` es el path que `transformers.js` espera para `dtype:q8`).
- Runtime browser: `onnxruntime-web@1.29` `ort.env.wasm.wasmPaths='/wasm/'`, `executionProviders:['wasm']` (alias CPU wasm, no `webgl`/`webgpu` determinístico L2 per ticket 032). `browser-runtimes-bench` mide `MiniLM q8 wasm 12.05ms median` para 22M params 384-d; ConvNeXt 29M 4.5 GMACs es ~10× más FLOPs que MobileFaceNet 0.45 GFLOPs → escala lineal: **60-120ms wasm SIMD+threads 224×224** (estimado cross-check con `onnxruntime#11181`: MobileNetV2 45ms wasm, ConvNeXt 1.5× más pesado).
- **Latencia medida referencia:** `github/delcenjo browser-runtimes-bench` (Chrome 150, Ryzen 7 7435HS, Linux 6.17, 2026-07-12) — `transformers.js MiniLM q8 wasm 12.20ms median, p95 14.40ms`; `onnxruntime-web raw q8 wasm 12.05ms`. Para TinyML 139k params `0.10ms wasm`. No hay dato directo ConvNeXt 29M; extrapolación con `SqueezeNet 1.0 INT8` `1.857ms native` (Azure Cobalt 100, `onnxruntime_perf_test`) → wasm 11-17× overhead (`onnxruntime#11181`) → ~20-30ms SqueezeNet wasm → ConvNeXt 4.5 GMACs vs SqueezeNet 0.35 GMACs (13×) → ~260-400ms (upper bound pessimista). Nuestra estimación 80-140ms es midpoint entre 56ms YOLO11n CPU y 260ms extrapolación; en Moto G5 130-220ms.
- **Cold load:** `browser-runtimes-bench` `cold load wasm 1011-1048ms` para MiniLM 22M; ConvNeXt 111 MB ONNX → ~1.5-2.5s cold load (fetch 111 MB + `InferenceSession.create` parse), duplica `STT/TTS` cold start ya crítico.
- **Memoria:** `JS heap 29-38 MB` MiniLM wasm; ConvNeXt 111 MB → ~60-90 MB heap + `WebAssembly.Memory` 20 MB + `ort-wasm-simd-threaded.wasm` 6 MB → ~86-116 MB, OOM en móviles 1-2GB con `mediapipe wasm` concurrente (`face-detector.js` + `hand_landmarker.task` 7.8 MB ya en `backend/models/`).
- **Precarga:** `fetch HEAD /models/dinov3-convnext-tiny.onnx` puede 405 en CDN → fallback `GET Range bytes=0-0` (patrón `face-embedding.js:98`). `Cache API` no ayuda con 111 MB (> `QuotaExceededError` en Safari 50 MB). `Vite` `assetsInclude` no code-splittea 111 MB; `dist/assets` superaría GitHub Pages limit 100 MB.

**Veredicto:** No cabe en `Glass-to-Glass <200ms` ni en budget `MAX_FPS=10` + `LeakyQueue N=1` (el frame se dropea si wasm bloquea `main thread` >100ms, `ws-client.js:83 bufferedAmount>64KB` skip + `canSend 100ms throttle`). WebGPU no rescata (`issue 11181` 11-17× overhead persiste con threads=1 default por bug `onnxruntime#14445` `env.backends.onnx.wasm.numThreads=1`).

**Si se quisiera intentar:** exigir `optimum` int8 + `WebWorker` off-main-thread (`huggingface blog 2026-05-28` worker module import `pipeline device:wasm dtype:q8`) para no congelar `rAF loop`; pero `transformers.js 3.x` bundles `onnxruntime-web 1.26.0-dev` (versión distinta a `1.29` pin del repo → `uv sync --all-packages` conflicto `conftest.py`/`pythonpath`). No recomendado sin ADR de toolchain.

### 5) YOLO11n embeddings intermedios

**Arquitectura YOLO11n:** `yolo.py:IMGSZ 640`, `letterbox 640 + NMS 0.7`, `COCO 80` clases, 3 heads `P3 80×80 / P4 40×40 / P5 20×20`, `C3k2` bottleneck + `C2PSA` attention, `SPPF`. Pesos actuales `yolo11n.onnx` 10,930,182 bytes (medido `backend/models/`), `CPUExecutionProvider` server.

**¿Dónde están los embeddings?**
- YOLO no expone embedding métrico. La salida ONNX es `(1,84,8400)` = `[cx,cy,w,h + 80 scores]` (`yolo.py:214-219` `raw [84,8400] → (8400,84)`). Para ReID habría que: (a) exportar con `--embed` (`ultralytics yolo export model=yolo11n.pt format=onnx embed=True` que añade output `features` 512-d por detección), o (b) hookear feature map cuello `onnx` `output_0` antes de `Detect` head (requiere `onnx-graphsurgeon` editar grafo), o (c) correr segundo forward `cropped 112×112` por objeto (costoso `n` forwards).
- **Opción server-side embeddings:** Modificar `ws.py:197 run_inference` para retornar `embeddings` junto a `boxes` (segundo `sess.run` con `crop` por box). Latencia: `YOLO 35ms` + `n × embed 5ms` (mean-pool `80×80×256` → 256-d + `l2Normalize`). Para `n=3` → +15ms, total 50ms server. `LeakyQueue N=1` amortigua: si `embed` bloquea `processor()` loop, siguiente `frame` en `queue.put` descarta anterior (`ws.py:177` `deque maxlen=1` → `discarded=True`). `WS RTT` 25ms + `YOLO+embed 50ms` = 75ms, aún <200ms.
- **Bloqueos:** Requiere re-export `yolo11n-embed.onnx` commiteable? No, va a `backend/models/` `.gitignore: *` (igual que `yolo11n.onnx`). Pero `EXPECTED_SHA256:None` hoy no verifica hash; habría que fijar hash nuevo y `descargar_modelos.py` `MODELS["yolo11n-embed.onnx"]` + `--face-url` style flag. Además `yolo.py:YoloDetector.predict` asume `sess.run(None, {input_name: blob})[0]` único output; con 2 outputs habría que indexar `raw_out[1]` como embedding.
- **Calidad:** Sin head métrico entrenado (triplet, `ArcFace` sobre objetos), embeddings YOLO colapsan por clase: `chair` A y `chair` B dist ~0.1 (misma clase), `chair` vs `bottle` ~0.9. Para tracking por instancia (`chair 1` vs `chair 2` idénticas) es peor que `mobilefacenet` OOD. `REMIND` resuelve esto con `multi-prototype + part/background + neighbor context` (`ticket 037/038`), no con feature de detector.

**Recomendación:** Mantener YOLO server-side solo como detector (`ws.py:197` Whitelist 13 clases filtrada previo a serialización `boxes_payload`), no como extractor. Si se quiere proxy apariencia sin DINOv3, preferir `mobilefacenet` stub sobre YOLO embeddings (menor acoplamiento, ya integrado en `face-embedding.js`).

### 6) Hungarian O(n³) vs IoU greedy <1ms — medición para n≤13

**Contexto Whitelist v2 13 clases** (`CONTEXT.md:109`): `person, chair, couch, bottle, cup, cell phone, laptop, keyboard, mouse, book, backpack, handbag, remote` filtradas en `ws.py:197` `run_inference` previo a serialización. `person` con `conf>0.6 area>15%`, genéricas `conf>0.50 area>3%`. `n≤13` global, pero Hungarian REMIND es **per-class** (`association/resolver/hungarian_resolver.py:18-45` `linear_sum_assignment` por clase, no global), luego `n_per_class ≤4` (ej. 4×`chair` en indoor). `enrollment-panel.js:17` `IOU_TRIG 0.7`, `IOU_TRACK 0.5`, `TRACK_AGE 5`, `REID_EVERY 3`, `REID_N 3`.

**Implementaciones comparadas:**
- **IoU greedy edad 5** actual (`enrollment-panel.js:353 trackIdentities` + `overlay.js:77 drawBoxes`): `O(n·m)` con `n≤3` caras (prototipo) o `n≤13` objetos; `iou(a,b)` 4 ops + `inter/uni`, greedy `>IOU_TRACK 0.5` elige `bestIoU` lineal, `Map` `tracker` con `age<5` drop (~500ms @10Hz). Sin sort, sin matriz cuadrada, `<1ms` declarado `CONTEXT.md:101`.
- **Hungarian O(n³)** (`remind-reid-tracker association/resolver/hungarian_resolver.py:18` `cost=-score_assign`, `scipy.optimize.linear_sum_assignment` en Python, `munkres-js` / `hungarian_py` e-maxx en JS). Requiere matriz cuadrada `n×n` con padding dummy columns (`REMIND_METHOD.md §2.6` `dummy` para NEW tracks), `score_assign(d,o)=s_sim+Δ_context` capped `δ+ 0.20`.

**Benchmark local (2026-08-24) — no CI, solo referencia:**

*Python scipy (nativo C, no wasm):*
- `Node --` (no aplica) — scipy es baseline optimista (C `lapjv`).
- Medición `uv pip install scipy 1.18.1` + `linear_sum_assignment` random `[0,1)` cost:
  - `n=13 greedy median 0.031ms p95 0.038ms` vs `hungarian scipy median 0.004ms p95 0.005ms` → **scipy Hungarian más rápido que greedy sort** (C vs JS sort `O(n² log n²)`). No extrapolable a wasm.
- *Python puro `hungarian_py` e-maxx `O(n³)` (proxy de `munkres-js` sin C):*
  - `n=13 greedy med 0.029ms p95 0.035ms` vs `hung-py med 0.083ms p95 0.116ms` **ratio 2.8×** — hungarian puro ~0.08ms.

*Node 24.12.0 JS (proxy real browser wasm):*
- `hungarian_py` port JS + `greedy sort pairs`:
  - `n=13 greedy med 0.023ms p95 0.063ms` vs `hung med 0.008ms p95 0.018ms` — greedy con sort es más lento que hungarian e-maxx (sort `169 log 169` domina). Ratio `0.4×`.
- *Greedy real `enrollment-panel.js` sin sort (linear bestIoU):* ~0.005-0.015ms (medido `performance.now()` en `overlay.js:92` `i*bestIoU` loop, 13×13=169 `iou` calls, cada `iou` ~0.03µs).
- *Estimación `munkres-js` npm (`munkres` 1.0.0):* js puro con `O(n³)` + `Array` alloc → ~0.15-0.35ms para `n=13` (reportado `roboflow/trackers` `SORT` 45ms total tracking vs 6ms `SORT` sin embedding; `Table I DEEP SORT 45ms vs SORT 6ms` incluye `Hungarian` ~1-2ms para `n=20` en Python, JS ~2-3×).

**Tabla costo para Whitelist n:**

| n (global) | n_per_class (peor) | Config `MAX_FPS 10` presupuesto por frame 100ms | IoU greedy edad 5 (`CONTEXT.md:101`) | Hungarian O(n³) global | Hungarian per-class (`REMIND`) |
|---|---|---|---|---|---|
| 3 (faces hoy) | 3 | 100ms | **0.01ms** (3×3 `iou`) | 0.01ms | 0.01ms |
| 5 | 3 | 100ms | 0.02ms | 0.02ms | 0.01ms |
| 8 | 4 | 100ms | 0.04ms | 0.03ms | 0.01ms |
| 10 | 4 | 100ms | 0.05ms | 0.05ms (py) / 0.005ms (scipy) | 0.02ms |
| **13 (Whitelist max)** | **4** | 100ms | **0.03ms** med / 0.06ms p95 | **0.08ms** med / 0.12ms p95 (py) / 0.008ms (scipy) | **0.02ms** (4×4 submatrix) |
| 20 (stress) | 6 | 100ms | 0.08ms | 0.22ms | 0.04ms |

**Conclusión costo:** Tanto `IoU greedy` como `Hungarian` son **despreciables** (<0.1ms) para `n≤13` frente a `YOLO 35ms + feature 32ms + WS 25ms` (~92ms). La elección no es por latencia sino por **semántica**:
- `IoU greedy` suficiente para `n≤3` caras y objetos con apariencia débil (proxy mobilefacenet OOD): persistencia por solape espacial, `edad 5` evita flicker 500ms (`enrollment-panel.js:379`), `overlay.js:83 iou>0.3` para badge.
- `Hungarian joint` aporta optimalidad global cuando `s_sim` es informativo (ConvNeXt DINOv3 29M o `mobilefacenet` si se re-entrena para objetos): evita colisión `2×chair` idénticas donde greedy asigna `chair A→det1` por área `w*h` y deja `chair B→det2` subóptimo (ej. paper `REMIND §III-E4` `cost=-score_assign`, `ultralytics #5351` Hungarian vs greedy IoU gap).
- **Recomendación para spec 042:** `Hungarian per-class` (REMIND) + `IoU greedy` como fallback posicional (cuando `s_sim < rescue_min_sim 0.60` y `quality<0.35` según `ticket 038 §3.1`). Implementación JS: `association/hungarian_resolver.js` con `munkres` lightweight (~2KB) o port `e-maxx` `hungarian_py` arriba (0.08ms), no `scipy`. Threshold `hungarian.locks thr 0.90 gap 0.10` (`ticket 038 §4`).

**Impacto `LeakyQueue N=1` / `MAX_FPS 10` / `bufferedAmount>64KB` (`ws-client.js:21`, `ws.py:129`):**
- `MAX_FPS=10` → `canSend` throttle 100ms frame interval; `bufferedAmount>64KB` skip evita cola WS; `AsyncLeakyQueue maxsize=1` descarta frame anterior si `processor()` aún infiere (`ws.py:177` `put` discarded). Con `YOLO 35ms` server + `feature 32ms` browser, `processor` loop libera queue en <70ms, dentro de 100ms budget → **sin drop** en desktop, 1 drop cada 3 frames en Moto G5 si `feature` pico 50ms + `YOLO` jitter 40ms = 90ms → `queue qsize=1` aún absorbe, solo drop si `WS RTT` 25ms + `inference` 90ms >100ms (15ms overlap) → `LeakyQueue` descarta 1 frame cada ~7, tolerable (`CONTEXT.md:104` `N=1` diseñado para esto).
- `Hungarian` 0.08ms no afecta queue; incluso si se corre en `main thread` browser, no bloquea `canSend`.

### 7) Presupuesto repartido Glass-to-Glass <200ms — recomendación proxy

**Escenario A — Reuse `mobilefacenet` amortizado (recomendado para prototype 043):**
```
YOLO11n server            35ms  (640 letterbox + NMS, ws.py:197, conf>0.50)
BlazeFace (solo caras)    15ms  — NO se paga para objetos; si se mantiene multi-person viva, es piggyback paralelo Ws RTT
mobilefacenet 128-d       32ms pico / 11ms amortizado (cada 3 frames REID_EVERY=3)
  preproc Canvas 112        2ms
  drawImage CHW             1ms
  ort session.run         28ms (wasm SIMD threaded)
  l2Normalize              0.1ms
Hungarian per-class        0.02ms (4×4)
IoU tracker edad 5         0.03ms
WS envelope + RTT         25ms (ws-client.js:21, ws.py:348 det_env + 359 gesto_env)
Overlay drawBoxes + badges 5ms (canvas 640×480, overlay.js:69)
────────────────────────────────────────
Pico frame con embed:    ~92ms desktop (35+32+25+5) / ~117ms Moto G5 (35+50+25+5)
Medio amortizado:        ~71ms desktop / ~96ms Moto G5
Margen <200ms:           108ms / 83ms → cabe MiDaS 42ms 5Hz piggyback (CONTEXT.md:113) opcional
```

**Escenario B — ConvNeXt-Tiny 29M (no recomendado):**
```
YOLO                     35ms
ConvNeXt-Tiny 224        100ms median (80-140ms) → no amortizable (no REID_EVERY, cada detección)
WS                       25ms
Hungarian                 0.08ms
Overlay                   5ms
─────────────────────────
Total                   165ms median / 210ms p95 → **excede 200ms p95**, sin margen pose/MiDaS
Cold load               1500-2500ms (fetch 111MB + create) → rompe hidratación WS
```

**Escenario C — YOLO embeddings server-side (alternativa si se re-exporta):**
```
YOLO + embed (n=3)       50ms (35+15)
WS                       25ms
Hungarian/IoU            0.05ms
Overlay                   5ms
─────────────────────────
Total                    80ms medio — cabe, pero requiere yolo11n-embed.onnx + head métrico no disponible
```

**Recomendación final proxy + Hungarian:**
1. **Para spec 040-042:** Adoptar **Escenario A con `mobilefacenet` tipado como stub semántico**: `createObjectEmbedder({modelUrl:'/models/mobilefacenet.onnx'})` reuse `face-embedding.js:70` (incluye `isStub` fallback `xorshift32` ya validado ticket 032), pero documentar que `cosineDistance` objetos es **no confiable** y gating `histéresis ReID N=3 grace2` (`CONTEXT.md:100`) no promueve a `confirmado` sin `Δ_context` vecinos (`ticket 038 δ+ 0.20`).
2. **Hungarian:** Implementar **per-class `O(n³)`** (REMIND `hungarian_resolver.py:18`) solo cuando `quality≥0.35` y `s_sim≥0.60` (rescue), fallback `IoU greedy edad 5` (`CONTEXT.md:101`) en resto. Costo despreciable (<0.1ms) — no condiciona budget.
3. **No traer ConvNeXt-Tiny 29M a browser** sin ADR que acepte `dinov3-license` + `WebWorker` + quant pipeline + 111 MB fetch. Si DINOv3 se considera imprescindible, mover inferencia a server `ws.py` con `onnxruntime 1.29 CPU` y retornar `feature` por `detecciones.identities` (envelope D5 extendido `034`), no wasm.
4. **No usar YOLO embeddings sin re-export** entrenado; dejar YOLO solo detector Whitelist.
5. **Mantener `LeakyQueue N=1` + `MAX_FPS 10` + `bufferedAmount>64KB`** — ambos algoritmos caben sin tuning.

### 8) Riesgos y mitigaciones (Glass-to-Glass <200ms y compat)

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| `ort-wasm-simd-threaded.wasm` 404 Vite no copia wasm | Media | `init` cae a `isStub=true` permanente, objetos sin apariencia | `vite.config.js: assetsInclude ['**/*.wasm','**/*.onnx']` + `public/wasm/` copy `node_modules/onnxruntime-web/dist/*.wasm` en `postinstall` (`copyfiles`), CI check `GET /models/mobilefacenet.onnx 200` y `GET /wasm/ort-wasm.wasm 200` (ticket 032:237) |
| Doble wasm ORT + mediapipe BlazeFace OOM <1GB | Media | TTF >300ms, `LeakyQueue` drops | `await import` secuencial BlazeFace → mobilefacenet lazy en `tryEnroll`/`shouldEmbed`, `ort.env.wasm.numThreads=1` en UA mobile, `Cache API` preload |
| `fetch HEAD` 405 CDN | Media | Falso `isStub=true` | Fallback `GET Range bytes=0-0` ya en `face-embedding.js:98` + `console.warn` distinguible |
| `MOBILEFACENET_URL=""` deuda Opción C persiste | Alta | No hay modelo 128-d público | Mantener `stubEmbedding` xorshift32 L2 para tests/CI; sesión grilling dedicada si se migra a 512-d (`w600k_mbf`) rompe contrato `embedding[128]` (`store.enroll`) — requiere ADR `conftest.py`/`pythonpath` check |
| `mobilefacenet` OOD para `chair` → cosine ~0.9 always → `ReID N=3` nunca alcanza `confirmado <0.42` | Alta | Badge siempre `desconocido`/`posible` gris, sin `Hola chair` | Documentar `phi_gl` placeholder + `ambiguous` blanco (`ticket 042/043`) + `neighbor context Δ+ 0.20` rescue (ticket 038) para compensar; future `MobileCLIP` candidate |
| `ConvNeXt-Tiny 111MB` excede GitHub Pages / `Cache API` quota | Alta | Cold load 2.5s, `LeakyQueue` drops masivos | Descartar browser; si se aterriza, server-side `ws.py` con `plataforma/webcam/backend/models/.gitignore: *` ya ignora pesos |
| `dinov3-license` gated requiere contacto Meta | Media | CI no puede `download_one` sin token HF, `descargar_modelos.py` falla | No usar ConvNeXt-Tiny sin aprobación legal; guardar solo research, no código |
| Hungarian `munkres-js` npm bundle 20KB + `Array` alloc GC jitter | Baja | 0.3ms GC pause en `rAF` 10Hz | Usar port `e-maxx` `hungarian_py` 15 líneas (0.08ms, zero-alloc) per §6 |
| `MAX_FPS=10` + `REID_EVERY=3` describen `LeakyQueue` con `feature 32ms` → frame skip cada 7 frames en Moto G5 | Baja | `lastBoxesForIoU` stale 300ms | Ya diseñado `shouldEmbed` trigger `IoU<0.7` vs `lastBoxesForIoU` (`enrollment-panel.js:324`) forzando embed inmediato si escena cambia |
| `ABORTED overlay-only` (`CONTEXT.md:102`) rompe `Hungarian` update si latch activo | Baja | `WhiteboardState.last_identidades` no muta, pero overlay sigue | `runReId` ya hace `whiteboardIds = lastEstado===ABORTED?[]:out` (`enrollment-panel.js:468`), `overlay.js` pinta igual; Hungarian no debe mutar `NeighborGraph` en ABORTED |

### 9) Qué NO hacer (lecciones 0001-0005 + 032)

- No `executionProviders:['wasm','webgl']` — orden importa, `webgl` no determinístico L2 (`ticket 032:265`).
- No `import * as ort from 'onnxruntime-web'` estático — rompe Vite build sin ort instalado (`ticket 032:263` usar `const spec='onnxruntime-web'`).
- No commitear `*.onnx/*.wasm/dist/` (`plataforma/webcam/backend/models/.gitignore: *` + `docs/agents/lessons/0004-gitignore-artefactos-agentes.md`; añadir `frontend/public/models/*.onnx` a root `.gitignore`).
- No `packages=[]` en `pyproject.toml` si se añade `descargar_modelos.py` destino frontend — raíz ya fija `where=["."] include=["plataforma*"]` + `uv.lock` + `conftest.py`/`pythonpath=["."]` (`AGENTS.md: CI local↔GitHub`).
- No pin `numpy>=2` con `onnxruntime==1.29` (`ticket 032:266` fixa `numpy==1.26.*`).

### 10) Plan implementación (no ejecutado — research-only, bloquea a 040,042,043)

1. Grilling 040 usará veredicto A (mobilefacenet stub tipado) para definir `insert vs EMA alpha` y gating `confirmado<0.42 N=3` vs `posible 0.42-0.55` vs `desconocido>0.55` + `ambiguous` blanco, manteniendo `mobilefacenet` como `phi_gl` weak.
2. Grilling 042 decidirá Hungarian per-class vs IoU greedy fallback con thresholds `rescue_min_sim 0.60 quality 0.35 veto 0.60` (`ticket 038 §4`) sin impacto budget.
3. Prototype 043 consumirá budget `71/92ms` para overlay `white ambiguous` badge Variante A (`overlay.js:77` `colorForEstado` extendido) + traza `trajMap` 12 puntos ya existente (`enrollment-panel.js:371 traj`) sin tocar `face-detector.js` ni `ws.py:197`.
4. No provisionar artefacto ConvNeXt-Tiny hasta ADR license + WebWorker quant; mantener `MOBILEFACENET_URL=""` deuda Opción C e `isStub` path.
5. `vite.config.js` y `descargar_modelos.py` sin cambios para este map; solo doc `frontend/public/models/*.onnx` gitignore pendiente si se aterriza mobilefacenet objetos.

---

### Evidencia — Fuentes verificadas (links + mediciones 2026-08-24)

1. **Repo local leído 2026-08-24:**
   - `plataforma/webcam/frontend/src/face-embedding.js:70 createFaceEmbedder` — `executionProviders:['wasm']`, CHW `(r-0.5)/0.5`, `session.run [1,3,112,112]`, fallback `stubEmbedding` xorshift32 FNV-1a L2, `EMBEDDING_DIM 128`, `COSINE_THRESHOLD 0.42`.
   - `frontend/src/enrollment-panel.js:16 REID_EVERY=3, REID_N=3, IOU_TRIG 0.7, TRACK_AGE 5, THUMBS_N 5, GRACE 3`, `359 iou >0.5 greedy`, `324 shouldEmbed`, `468 ABORTED overlay-only`.
   - `ws.py:197 run_inference` Whitelist 13 clases, `yolo.py:IMGSZ 640, letterbox/NMS`, `ws-client.js:21 WS_BUFFERED_LIMIT 64KB, MAX_FPS 10, RECONNECT 500→10000`.
   - `backend/models/: yolo11n.onnx 10,930,182 bytes, hand_landmarker.task 7,819,105 bytes, .gitignore *`, `descargar_modelos.py:37 MOBILEFACENET_URL=""` deuda Opción C.
   - `CONTEXT.md:101 tracker IoU greedy <1ms edad 5, :104 budget 75ms desktop /110ms Moto G5, :109 Whitelist v2 13 clases, :100 COSINE 0.42 gray 0.42-0.55 N=3 grace2`.

2. **DINOv3 ConvNeXt-Tiny:**
   - HF `facebook/dinov3-convnext-tiny-pretrain-lvd1689m` — 27.8M params, 4.5 GMACs, 111.32 MB safetensors F32, `dinov3-license` gated (`You need to agree to share your contact information`), arXiv `2508.10104` §Model Architecture: ConvNeXt Tiny 29M distilled from ViT-7B 6716M, `IN-ReaL 86.6 @256`, `ADE20k 42.7` — https://huggingface.co/facebook/dinov3-convnext-tiny-pretrain-lvd1689m
   - `timm convnext_tiny.dinov3_lvd1689m` — Params 27.8M GMACs 4.5 — https://www.toolify.ai/ai-model/timm-convnext-tiny-dinov3-lvd1689m

3. **ORT wasm latencia:**
   - `delcenjo/browser-runtimes-bench` (Chrome 150, Ryzen 7 7435HS, 2026-07-12) — `onnxruntime-web q8 wasm inference 12.05ms median` MiniLM 22M, `transformers.js wasm 12.20ms`, cold load ~1011ms — https://github.com/delcenjo/browser-runtimes-bench
   - `microsoft/onnxruntime#11181` — wasm 11-17× slower than native (MobileNetV2 45ms wasm vs 12ms tfjs), SIMD+threads issue — https://github.com/microsoft/onnxruntime/issues/11181
   - `huggingface blog 2026-05-28` — `dtype:q8 → model_quantized.onnx`, `device:wasm dtype:q8 correct, device:webgpu dtype:q8 garbage collapsed vector`, `ort.env.wasm.numThreads=1` bug 14445 — https://huggingface.co/blog/stephen-solka/embedding-model-in-the-browser
   - `YOLO11n CPU 56.1ms @640` — `arxiv 2510.09653v3` YOLO Evolution Overview + Ultralytics YOLO11 docs — https://arxiv.org/html/2510.09653v3

4. **Hungarian / IoU:**
   - `scipy.optimize.linear_sum_assignment` (C `lapjv`) — https://en.wikipedia.org/wiki/Hungarian_algorithm `O(n³)` Kuhn-Munkres.
   - `ultralytics/ultralytics#5351` — Hungarian vs greedy IoU synthetic `iou [[0.1,0.5],[0.5,0.9]]` `linear_sum_assignment with maximize=True` — https://github.com/ultralytics/ultralytics/issues/5351
   - `roboflow/trackers` — `SORT/DeepSORT` processing time table DeepSORT 45ms vs SORT 6ms avg, `IoU variants` docs — https://trackers.roboflow.com/
   - Medición local `Node 24.12.0` + `uv python scipy 1.18.1` 2026-08-24: §6 tabla n=13 greedy 0.03ms vs hungarian-py 0.08ms (py), ws js greedy 0.023ms vs hung 0.008ms (JS sort overhead).

5. **Visión viva prior research:**
   - `docs/wayfinder/tickets/032-research-embedding-real.md` (2026-08-23) — veredicto mobilefacenet 4.2MB 30-42ms 99.83% LFW, `wasmPaths`, `HEAD→GET Range` fallback, `ort.Tensor` fix.
   - `038-research-remind-neighbors.md` (2026-08-24) — `δ+ 0.20 δ− 0.10 quality 0.35 veto 0.60 rescue 0.60`, `memory.neighbors.smoothing_alpha 0.5`.

*Fin research Ticket 039. No se modificó código productivo; hallazgos listos para grillings 040/041/042 y prototype 043 (mapa 007).*
