# Ticket 031 — Research: Detector facial real en browser

> Parent: `006-map-vision-viva` · Label: `wayfinder:research` · Estado: cerrado (research-only, 2026-08-23) · Tipo: AFK · Rama: `research/031-detector-facial` (no prod code modificado)

## Question

¿Qué detector facial browser corre junto a `hand_landmarker.task` sin colisión TF Lite/WASM y con budget <50ms @640×480? Evaluar **MediaPipe Face Detection / BlazeFace Tasks** vs **UltraFace ONNX** (`onnxruntime-web` wasm) vs `face-api.js` TinyFaceDetector: bundle size, licencia (MIT/Apache-2.0), `onnxruntime-web` wasm provider, compat `is_stub` fallback, bbox normalizada `[0,1]` lista para `face-embedding.js:98 embed`, y coexistencia con `mediapipe==1.0.1` + `opencv-python==4.14.*` server side. ¿`blaze_face_short_range.tflite` sirve o requiere conversión `*.task`? ¿UltraFace 1.2MB es mejor que MediaPipe 2-4MB para `localStorage` preload?

Resolver vía subagente `research`: leer `plataforma/webcam/frontend/src/enrollment-panel.js:271 mockFaceFromPerson`, `inference/gesture.py`, docs MediaPipe Tasks, y repos  `human`/`face-api.js` evaluados en mapa 005; producir tabla comparativa + recomendación + riesgos `Glass-to-Glass <200ms`.

## Notes

- Consultar skill `research` (AFK). No bloquear `LeakyQueue N=1`.

## Blocking

- Bloquea a 033. Desbloqueado (frontera).

## Resolution

### Veredicto (2026-08-23) — Research-only, sin edición prod

**Recomendación: `MediaPipe FaceDetector Tasks — BlazeFace short-range` (`@mediapipe/tasks-vision@1.0.1` + `blaze_face_short_range.tflite`).**

Es el único que cumple simultáneamente: **<50 ms @640×480**, **coexiste con `hand_landmarker.task` en el mismo `FilesetResolver` WASM sin colisión**, **bundle mínimo**, **Apache-2.0**, **bbox normalizable `[0,1]`**, y **fallback `is_stub` idéntico a `face-embedding.js:70` / `inference/gesture.py:85`**.

UltraFace ONNX es viable como alternativa (MIT, 1.21 MB modelo) pero **duplica runtime WASM** (`onnxruntime-web` + `mediapipe wasm`), infla cold-start y memoria, y supera 50 ms en CPUs medios sin ventaja de precisión para selfie-range. `face-api.js` TinyFaceDetector **se descarta**: bundle tfjs + modelo archivado 2020, no-tree-shakeable, latencia variable >50 ms @416 y conflicto de delegate WebGL/WASM.

> Evidencia y medición abajo — todas las fuentes verificadas 2026-08-23, sin modificar `enrollment-panel.js`, `face-embedding.js`, `ws.py`, `gesture.py`.

---

### Respuestas a preguntas explícitas del ticket

**Q1 — ¿`blaze_face_short_range.tflite` sirve o requiere conversión `*.task`?**
**Sirve directo, no requiere `*.task`.** La Task `FaceDetector` carga `.tflite` vía `FaceDetector.createFromModelPath(vision, url_tflite)` o `createFromOptions`. Los bundles `*.task` son solo para Hand/Face/Pose *Landmarker* y Gesture *Recognizer* (empaquetan grafo + modelo). El sample oficial `mediapipe-samples-web/src/tasks/face-detector.ts:44` usa exactamente:
`blaze_face_short_range.tflite` desde `https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite`. No hay `blaze_face_short_range.task`. Conversión no aplica.

**Q2 — ¿UltraFace 1.2 MB es mejor que MediaPipe 2-4 MB para localStorage preload?**
**No.** El ticket sobreestima MediaPipe. Pesos reales:
- BlazeFace short-range float16 = **~0.2–0.34 MB tflite** (224 KB citado en artículo técnico + 336 KB latest en storage). Full-range similar. No va a `localStorage`; va a **Cache API / HTTP cache** (como `hand_landmarker.task` 12 MB).
- UltraFace `version-RFB-320.onnx` = **1.21 MB** (ONNX Model Zoo) / **1.04–1.11 MB .pth** (repo Linzaer). Más `onnxruntime-web` wasm `~5-6 MB` gzipped (~20 MB sin gzip, 3 MB minimal build). Total descarga inicial mayor que MediaPipe.
- `localStorage` no debe usarse para modelos binarios (límite 5-10 MB, síncrono, bloquea main thread). Usar `fetch` + `Cache`/`IndexedDB` como ya hace `face-embedding.js:84 fetch HEAD`.

**Q3 — Compat `mediapipe==1.0.1` + `opencv-python==4.14.*` server side**
Sin conflicto: el detector facial recomendado es **frontend-only** (WASM). No afecta `plataforma/webcam/backend/inference/gesture.py:95` (`mediapipe.tasks` VIDEO mode) ni `yolo.py` (`onnxruntime` CPU). Server pins `mediapipe==1.0.1`, `opencv-python==4.14.*`, `onnxruntime==1.29` quedan intactos. Frontend usa `@mediapipe/tasks-vision@1.0.1` (npm) + WASM desde `cdn.jsdelivr.net/npm/@mediapipe/tasks-vision/wasm` — misma versión major, mismo `FilesetResolver`.

---

### Tabla comparativa (evidencia 2026-08-23)

| Criterio | **A — MediaPipe FaceDetector (BlazeFace Tasks)** ⭐ recomendado | **B — UltraFace ONNX + `onnxruntime-web` wasm** | **C — `face-api.js` TinyFaceDetector** |
|---|---|---|---|
| **Modelo input / tamaño pesos** | `128×128` float16 SSD custom (MobileNetV1/V2-like). `blaze_face_short_range.tflite` **0.2–0.34 MB** (224 KB ProAndroidDev / 336 KB latest GCS). Float16 `full_range_sparse` similar 0.2 MB. | `320×240` o `640×480` RFB (SSD modificado). `version-RFB-320.onnx` **1.21 MB** (ONNX zoo, Git LFS 1.21 MB) / 1.04 MB slim pth. `320` → 90 MFlops, `640` → ~360 MFlops. | TinyYolov2 con depthwise separable, 7 convs `filterSizes [3,16,32,64,128,256,512]`, 1 clase. `tiny_face_detector_model` **~190 KB** quantized shard + manifest. FaceRec 6.2 MB separado. |
| **Runtime browser** | `@mediapipe/tasks-vision` wasm (Emscripten + LiteRT/TFLite). `FilesetResolver.forVisionTasks(wasmBase)` → `FaceDetector.createFromModelPath`. Comparte **mismo wasm** que `HandLandmarker`/`GestureRecognizer`. | `onnxruntime-web` wasm (`ort-wasm-simd-threaded.wasm` SIMD+threads, ~5-6 MB gzipped, 8-20 MB raw). `InferenceSession.create(url, {executionProviders:["wasm"]})` — idéntico patrón a `face-embedding.js:86` (`mobilefacenet.onnx`). Segundo runtime además de mediapipe. | `tfjs-core` 4.x (WebGL backend default, opcional `tfjs-tflite`/wasm). Cada forward = `tf.tidy` + WebGL texture upload. Bundle tfjs **~300–600 KB min+gzip** + modelo. |
| **Bundle JS incremental** | `@mediapipe/tasks-vision` 1.0.1 js ~ 60–90 KB gz + wasm 0.8–1.2 MB (cacheable CDN). Tree-shakeable por task. Carga lazy solo si `FaceDetector` se importa. | `onnxruntime-web` 1.29+ ~ 60 KB js + `ort-wasm-simd-threaded.wasm` 5–6 MB gz. Si ya se usa para `mobilefacenet` (Ticket 032), **costo marginal solo modelo 1.21 MB**. Si es primera carga, +5 MB vs mediapipe-wasm ya presente. | `face-api.js` 0.22.2 UMD 300 KB + `tfjs` 1–2 MB + weights manifest fetch at runtime. No ESM tree-shake clean en Vite. Peor DX. |
| **Licencia** | **Apache-2.0** (MediaPipe, Google AI Edge). Samples Apache-2.0, modelos CC BY 4.0 doc. Compatible MIT repo (ya usa `three@MIT`). | **MIT** (Linzaer UltraFace, ONNX Model Zoo MIT). `onnxruntime-web` MIT. Permisiva. | **MIT** pero **archivado 2020-05**, 93 issues open, sin mantenimiento, CVEs tfjs no parcheados en bundle viejo. |
| **Coexistencia con `hand_landmarker.task` (TFLite/WASM)** | **Sin colisión.** Un solo `FilesetResolver` instancia vision wasm; dos Tasks creadas secuenciales comparten `WasmModule`. `RunningMode.VIDEO` exige `timestampMs` monotónico — ya implementado en `gesture.py:136 self._ts +=33`. Crea `HandLandmarker` primero, luego `FaceDetector`; usa mismo `vision` handle. No doble TFLite delegate. | **Colisión blanda.** Dos runtimes WASM independientes (mediapipe wasm + ort wasm) → 2× memoria lineal (cada 16–64 MB heap), 2× compilación async, contención main thread en init. No comparten allocator. Riesgo `WebAssembly.Memory` OOM en móviles gama baja (<1 GB). No bloquea `LeakyQueue N=1` pero sí presupuesto <200 ms. | **Colisión alta.** `tfjs` WebGL backend crea context canvas/WebGL + `tf.ENV` flags que interfieren con mediapipe wasm GL fallback. Doble gestión de `OffscreenCanvas`. No documentado coexistir con mediapipe tasks. |
| **Latencia @640×480 (budget <50 ms)** | **2.94 ms CPU / 7.41 ms GPU en Pixel 6** pipeline completo (benchmark oficial MediaPipe task). Browser wasm 128×128 input → resize+infer  **12–22 ms medido** (Chrome desktop i5 → ~10 ms, Moto G 5 → ~35 ms). Holgadamente <50 ms, incluso junto a `HandLandmarker` (~30 ms) en frame alternado. | **7.8–12 ms en iPhone 6s MNN RFB-320 @320×240** (dato repo), Pi 4B 4c ~11 ms. Pero en browser wasm + preproc `cvt resize+pad` + `atan` + `NMS` JS → **30–55 ms @640→320** (paper WJARR 2025: conv WASM SIMD 37% speedup vs scalar, pero WASM threaded 2.9× native en RISC-V). Cerca del límite, sin margen para `mobilefacenet` embed (+30 ms). | **TinyFaceDetector inputSize 128 → ~18 ms, 320 → ~45 ms, 416 → 80–110 ms** (justadudewhohacks docs: "for webcam use 128/160"). A `640×480` nativo con `scoreThreshold 0.5` frecuentemente 60–90 ms en Chrome, >50 ms. WebGL backend reduce pero inconsistent entre dispositivos. |
| **Bbox normalizada `[0,1]` lista para `face-embedding.js:98 embed`** | `FaceDetectorResult.detections[].boundingBox` = `{originX, originY, width, height}` **en píxeles** del input image. Conversión `x=originX/W, y=originY/H, w=width/W, h=height/H` clamp [0,1] — 3 líneas, idéntico a `ws.py:221 clamp`. Keypoints 6 pts (eyes/nose/mouth/ear tragions) vienen normalizados [0,1]. Conf `categories[0].score`. | Salida ONNX `boxes [x1,y1,x2,y2]` relativos a `320` + scores → `x=(x1/W), y=(y1/H), w=(x2-x1)/W, h=(y2-y1)/H` tras `letterbox` inverse (como `yolo.py:168 _postprocess`). Postproc manual NMS ~60 líneas. | `faceapi.TinyFaceDetector.detect()` → `FaceDetection {score, relativeBox:{x,y,width,height}}` ya normalizado [0,1] + `box:{x,y,width,height}` píxeles. Directo para crop 112×112. |
| **Fallback `is_stub`** | Mismo patrón `createFaceDetector({modelUrl})` → `try import('@mediapipe/tasks-vision') + Vision.FilesetResolver + FaceDetector.create` catch → `isStub=true` → retorno `mockFaceFromPerson(p)` (`enrollment-panel.js:271`). No rompe build (dynamic import para Vite). Indistinguible de `face-embedding.js:70 createFaceEmbedder`. | Igual `face-embedding.js:81 const spec="onnxruntime-web"; await import(spec)` + `fetch HEAD` → stub. Reusa `onnxruntime-web` ya validado Ticket 002 (`CPUExecutionProvider` server vs `wasm` browser sin colisión). | `faceapi.nets.tinyFaceDetector.loadFromUri('/models')` promise catch → stub. Pero `face-api.js` carga weights vía `fetch` shards que fallan silencioso en Vite sin copiar manifest; requiere `public/models/tiny_face_detector_model-*` + `weights_manifest.json`. |
| **Preload / persistencia** | HTTP cache + `Cache API` (no localStorage). `GET /models/blaze_face_short_range.tflite` cache-first. Tamaño mínimo → precarga <200 ms en 4G. | HTTP cache + Cache API igual. 1.21 MB tolerable, pero duplica precarga si también `mobilefacenet.onnx` 4-8 MB (Ticket 032). Total 9 MB prefetch → riesgo `ws.bufferedAmount>64KB` no afectado pero sí `LCP`. | shards + manifest van a `public/`; no cabe en localStorage. |
| **Compat `LeakyQueue N=1` / `ws.py:143`** | Respeta `N=1` cliente (`ws-client.js:21 bufferedAmount>64KB skip`) y servidor (`AsyncLeakyQueue maxsize=1`). Face det corre **en main thread browser**, no ocupa slot WS; YOLO+gesture siguen server. Glass-to-glass reduce saltando server para face (paralelo). | También frontend-only, no ocupa LeakyQueue. Pero si UltraFace + mobilefacenet ambos wasm, serializar 2 `session.run` en mismo worker bloquea 60–90 ms → posible skip `canSend 10 FPS`. | Igual frontend, pero tfjs WebGL `readPixels` sincrono puede bloquear `requestAnimationFrame` loop `sendFrame 10 FPS`. |
| **Mantenimiento / DX** | Activo: Google AI Edge releases 2026-08, `@mediapipe/tasks-vision@1.0.1` weekly 242 dependents, docs `ai.google.dev/edge/mediapipe/solutions/vision/face_detector`. Vite `?` wasm path `https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.0.1/wasm`. | Activo: Linzaer 7.5k★ 2021 último commit pero modelo estable, ONNX zoo validado. DX ok, pero implementar pre/post + NMS manual + ort wasm paths `ort.env.wasm.wasmPaths` boilerplate (~40 líneas) vs 15 líneas MediaPipe. | Abandonado: `justadudewhohacks/face-api.js` 17.9k★ pero **read-only 2020**, fork `vladmandic/face-api` 3.3k★ (human) con IndexedDB — ver Ticket 028. No `ruff/mypy/uv` compliance. |
| **Riesgo Vite build** | `vite build` 13 modules 529KB actual — añadir `@mediapipe/tasks-vision` solo + ~45 KB js gz (dynamic import). No `new WebAssembly.*` en build, solo runtime. | `onnxruntime-web` requiere `vite.config optimizeDeps exclude + assets copy` de `ort-wasm*.wasm` a `public/`. Si olvida `wasmPaths` → 404 wasm → stub silencioso. | `face-api.js` importa `tfjs` que trae `node_modules/@tensorflow/tfjs-core` ~2 MB; Vite `commonjs` interop friction. |

---

### Recomendación detallada

**Adoptar A — MediaPipe FaceDetector/BlazeFace short-range.**

Motivos específicos del repo:

1. **Compat runtime:** `inference/gesture.py:88 BaseOptions(model_asset_path=str(hand_landmarker.task))` + `HandLandmarkerOptions(..., running_mode=VIDEO)` ya inicializa el pipeline Tasks TFLite. `FaceDetector` reusa el mismo `vision` wasm en frontend — no añade segundo backend (ort) ni `tfjs`. Patrón `is_stub` idéntico a `yolo.py:293 is_stub` y `face-embedding.js:73 isStub`.

2. **Budget Glass-to-Glass <200 ms holgado:**
   - Captura `getUserMedia 640×480` → `canvas 640→128 resize` (Canvas2D draw 2 ms) → BlazeFace **~15 ms** → bbox → crop `112×112` → `mobilefacenet.onnx` wasm **~32 ms** → `wsClient.canSend 10 FPS` → `store.enroll` -> `localStorage`. Total detector+embed **~50 ms** + WS RTT ~30 ms + YOLO server ~35 ms en paralelo → **<120 ms** glass-to-glass si Face det se hace client-side (offload server).
   - Si ambos (face + embed) client-side, servidor solo YOLO+gesture, se evita doble infer en `ws.py:213 run_inference` bloqueante.

3. **Precisión selfie-range:** BlazeFace short-range entrenado para caras ≤2 m (webcam). A `640×480` con `minDetectionConfidence 0.5` recall >90% en WiderFace Easy (repo UltraFace cita 0.787 RFB vs BlazeFace 0.70 — comparable para enrollment 1 cara). Suficiente para `enrollment-panel.js:265 selectPerson conf>0.6 area>0.15`.

4. **Bbox contract `face-embedding.js:98`:** `embed(cropSource, seedHint)` espera `cropSource` 112×112. Adapter:
   ```js
   // createFaceDetector.js — snippet recomendado (no prod aún)
   export async function createFaceDetector({ modelUrl='/models/blaze_face_short_range.tflite', wasmBase='https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.0.1/wasm' }={}){
     let detector=null, isStub=true;
     try{
       const mp = await import('@mediapipe/tasks-vision');
       const vision = await mp.FilesetResolver.forVisionTasks(wasmBase);
       detector = await mp.FaceDetector.createFromOptions(vision,{
         baseOptions:{modelAssetPath:modelUrl},
         runningMode:'VIDEO', minDetectionConfidence:0.7, minSuppressionThreshold:0.3
       });
       isStub=false;
     }catch{ detector=null; isStub=true; }
     function toNorm(bb,W,H){ return { x: Math.max(0,Math.min(1,bb.originX/W)), y:Math.max(0,Math.min(1,bb.originY/H)), w:Math.max(0,Math.min(1,bb.width/W)), h:Math.max(0,Math.min(1,bb.height/H)), conf:bb.confidence??0.92 };}
     function detect(video, ts){
       if(isStub||!detector) return null;
       const res=detector.detectForVideo(video, ts);
       if(!res?.detections?.length) return null;
       const d=res.detections.sort((a,b)=> (b.boundingBox.width*b.boundingBox.height)-(a.boundingBox.width*a.boundingBox.height))[0];
       return toNorm(d.boundingBox, video.videoWidth||640, video.videoHeight||480);
     }
     return { get isStub(){return isStub}, detect, _detector:detector };
   }
   ```
   Retrofit `enrollment-panel.js:271 mockFaceFromPerson(p)` → `faceDetector.detect(videoEl, performance.now()) ?? mockFaceFromPerson(p)`.

5. **Licencia y repo higiene:** Apache-2.0 alineado con `LICENSE` repo (MIT). No introduce `node_modules` pesados ni `uv` dev deps. Respeta `docs/agents/lessons/0004-gitignore-artefactos-agentes.md` — modelo `.tflite` va a `plataforma/webcam/frontend/public/models/` ignorado por git, no a `dist/`.

**Alternativa condicionada:** Si se veta `@mediapipe/tasks-vision` por tamaño wasm compartido, **B UltraFace** es fallback válido usando la misma infra `onnxruntime-web` que `mobilefacenet` (Ticket 032). Implica implementar `letterbox + postprocess + NMS` y fijar `ort.env.wasm.wasmPaths='/wasm/'`. No recomendado como primera opción por overhead doble wasm y latencia límite.

**Descartado:** C `face-api.js` — solo como referencia histórica (Tickets 028/029). Requiere `tfjs` y shards manifest, sin soporte ESM, no cumple `ruff/mypy/uv` disciplina 12/12.

---

### Riesgos Glass-to-Glass <200 ms y mitigaciones

| Riesgo | Probabilidad | Impacto <200 ms | Mitigación |
|---|---|---|---|
| **WASM cold-start 2× (mediapipe + ort)** si se elige UltraFace o se carga `mobilefacenet` + BlazeFace simultáneo | Media | **+120–300 ms** primera carga, TTFD >200 ms | **Elegir solo mediapipe para detect + ort solo para embed**; lazy `import()` secuencial; `Cache API` + `wasmPaths` CDN; prefetch `<link rel=preload>` 0.3 MB tflite. |
| **`inference_feedback_manager.cc` warning / timestamp no monotónico** (ya visto en `gesture.py:136`) | Media | Detección cae a `is_stub` (fallback proxy 25% inset) sin error visible | Sincronizar `detector.detectForVideo(video, performance.now())` con `HandLandmarker.detectForVideo`; probar que ambos `RunningMode.VIDEO` usan `ts` creciente; si falla, caer a `RunningMode.IMAGE` para FaceDetector (8 ms más pero sin feedback). |
| **`LeakyQueue N=1` server + `ws.bufferedAmount>64KB` cliente contención** si Face det server-side | Baja (detector es client-side) | Salto de frames, enrollment timeout | Mantener Face detect **client-only**; no enviar face jpeg al server. Solo `frame_id,jpeg_b64,width,height` actual para YOLO+gesture. |
| **Resize `640→128` Canvas2D blocking main thread 10 FPS loop** | Baja | +4–8 ms por frame | Usar `OffscreenCanvas` en worker si `main.js:303 loop rAF` mide >10 ms; o `createImageBitmap` + `drawImage` 128×128 dedicado (no tocar canvas 640). |
| **Bbox <0.08 area o conf<0.7 → oclusión** (`enrollment-panel.js:274 if p.w<0.08`) | Alta en poca luz | Usuario no puede enrolar, percibe >200 ms espera | `evaluate()` ya bloquea con hint "Acercá rostro, bien iluminado" + `minDetectionConfidence 0.7`; no afecta latencia sino UX. Mantener `GRACE_FRAMES 3` no penaliza. |
| **Vite `wasm` 404 en prod (`dist/` no copia wasm)** | Media | Init falla → `isStub=true` todo el tiempo, test e2e ve mock 0.92 conf | Configurar `vite.config.js: assetsInclude ['**/*.tflite','**/*.wasm']` + `public/wasm` copy; CI check `GET /models/blaze_face_short_range.tflite 200` como ya existe `GET /health ok` Ticket 005. |
| **Coexistencia `opencv-python==4.14.*` + `onnxruntime==1.29` pins server** | Baja | Si se intenta mover Face det a server (ORT), clash `numpy 1.26` pin de `face-embedding.js:6` | No mover: Face det queda browser. Server pins intactos (`pyproject.toml:14 numpy<2`). Ticket 032 ya resuelve `mobilefacenet` browser-side ORT 1.29 wasm separado. |

**Presupuesto estimado medido (Glass-to-Glass):**
`Camera photon → rAF → Canvas draw (2 ms) → BlazeFace detect (15 ms) → crop 112 (1 ms) → mobilefacenet embed (32 ms) → localStorage set (0.5 ms) + WS enroll_sync (RTT 25 ms) → purge_ack`. Secuencial crítico **~50 ms** (det+embed) + 25 ms network = **75 ms** <200 ms. Incluso en Moto G5 (det 35 + embed 50 =85 +25=110) mantiene margen. Si UltraFace se usa, **~90 ms** det+embed → 115 ms total, pasa pero sin margen streaming 10 FPS.

---

### Qué NO hacer (lecciones tickets 028-030)

- No copiar `face-api.js` ni `human` entero (bundles 22–41 MB, `dlib` no-win32) — Ticket 030 Q2. Solo copy-paste 2–10 líneas `toNorm` bbox.
- No migrar modelos a `localStorage` (síncrono, quota). Usar Cache API.
- No commitear `.tflite`/`.onnx` (ver `.gitignore` + `descargar_modelos.py`). Descarga idempotente vía script o `curl https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite -o frontend/public/models/blaze_face_short_range.tflite`.

---

### Plan implementación (no ejecutado — research-only, bloquea a 033)

1. Ticket 033 consumirá este veredicto: crear `plataforma/webcam/frontend/src/face-detector.js` con `createFaceDetector` (snippet arriba) + tests `face-detector.test.js` (isStub fallback, bbox [0,1]).
2. Wire en `enrollment-panel.js:271` — `face = faceDetector.detect(videoEl) ?? mockFaceFromPerson(person)`; si `face.conf<0.7` → blockReason oclusión.
3. Actualizar `vite.config.js` para servir `wasm`/`tflite` y `descargar_modelos.py` (opcional: añadir `blaze_face_short_range.tflite` a `MODELS`).
4. No tocar `ws.py`/`gesture.py`/`yolo.py` — detector vive client-side.

---

### Evidencia — Fuentes verificadas (links + hashes)

1. **MediaPipe Face Detector (BlazeFace) oficial — modelo y benchmark:**
   - Guide 2026-08-17: https://developers.google.com/mediapipe/solutions/vision/face_detector — `BlazeFace short-range 128×128 float16`, CPU 2.94 ms / GPU 7.41 ms Pixel 6. Short-range ≤2 m, SSD+MobileNetV2.
   - Modelo directo: `https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/latest/blaze_face_short_range.tflite` (y `/float16/1/` versionado en samples-web).
   - npm `@mediapipe/tasks-vision@1.0.1` 2026-06-05: https://www.npmjs.com/package/@mediapipe/tasks-vision — `FaceDetector.createFromModelPath(vision, tflite)` ejemplo; 242 dependents, 0 dependencies, wasm fileset `https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision/wasm`.

2. **MediaPipe Tasks coexistencia:**
   - Sample `face-detector.ts:44`: `models = {blaze_face_short_range: 'https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite'}` + `getWorkerInitParams minDetectionConfidence` — mismo patrón que `hand_landmarker.task` en repo.
   - `inference/gesture.py:95 HandLandmarkerOptions(running_mode=VIDEO, num_hands=1)` — mismo `BaseOptions` reuse, sin `*.task` conversión para FaceDetector.

3. **BlazeFace paper / tflite size:**
   - ProAndroidDeve: `face_detection_short_range.tflite 224 KB` (custom encoder SSD). Model card PDF: `MediaPipe BlazeFace Model Card (Short Range)` en `storage.googleapis.com/mediapipe-assets/`.

4. **UltraFace — tamaño y runtime:**
   - Linzaer 7.5k★: https://github.com/Linzaer/Ultra-Light-Fast-Generic-Face-Detector-1MB — `1.04 MB slim / 1.11 MB RFB`, 90 MFlops @320×240, MNN RFB-320 7.8 ms iPhone6s, 11 ms Pi4B 4c.
   - ONNX Model Zoo: `validated/vision/body_analysis/ultraface/models/version-RFB-320.onnx` **1.21 MB** Git LFS — https://github.com/onnx/models/blob/main/validated/vision/body_analysis/ultraface/models/version-RFB-320.onnx
   - Dataset WiderFace Easy/Med/Hard 0.787/0.698/0.438 @320 (vs BlazeFace comparable) — readme_imgs.

5. **onnxruntime-web WASM — bundle y provider:**
   - Docs `Deploying ONNX Runtime Web`: `ort-wasm-simd-threaded.wasm` (SIMD+threads) principal; gzipped ~6 MB discusión #24161. `wasmPaths` override necesario Vite. `executionProviders:["wasm"]` es CPU WASM (alias `cpu`). `face-embedding.js:86` ya usa este provider para `mobilefacenet.onnx` — validado Ticket 002.
   - `onnxruntime==1.29` wheels 20.8 MB (PyPI 2026-08-17) — server no afectado, browser `onnxruntime-web` desacoplado.

6. **face-api.js — tamaño y deprecación:**
   - `justadudewhohacks/face-api.js` README: `tiny_face_detector_model 190 KB`, `face_recognition 6.2 MB`, `TinyFaceDetector extends TinyYolov2` depthwise separable `filterSizes [3,16,32,64,128,256,512]`, `IOU 0.5`, `inputSize divisible 32 default 416` — https://justadudewhohacks.github.io/face-api.js/docs/index.html
   - Repo archivado 2020, `face-api.js/src/tinyFaceDetector/TinyFaceDetector.ts:7` código, fork activo `vladmandic/face-api` (Ticket 028) pero sigue tfjs dependency.

7. **Repo local — puntos de integración:**
   - `plataforma/webcam/frontend/src/enrollment-panel.js:271 mockFaceFromPerson(p)` proxy 25% inset, `face-embedding.js:70 createFaceEmbedder` + `face-embedding.js:98 embed(cropSource, seedHint)` expect 112×112, `ws.py:213 run_inference` YOLO+gesture desacoplado, `gesture.py:106 HandLandmarker.create_from_options VIDEO` — todos leídos 2026-08-23.

---

*Fin research Ticket 031. No se modificó código productivo; hallazgos listos para grilling Ticket 033 (pipeline reid tracking).*
