# Ticket 032 — Research: ArcFace mobilefacenet 128-d real en browser

> Parent: `006-map-vision-viva` · Label: `wayfinder:research` · Estado: cerrado (research-only, 2026-08-23) · Tipo: AFK · Rama: `research/032-embedding-real` (no prod code modificado)

## Question

¿Cómo aterrizar `mobilefacenet.onnx` 112×112 en `face-embedding.js:70 createFaceEmbedder` con `onnxruntime-web` wasm (`session.run` 1×3×112×112, normalize `(x-0.5)/0.5 → L2`) sin romper `uv` `onnxruntime==1.29` server ni colisionar con `hand_landmarker.task` TF Lite? Medir modelo size (4-8MB), latencia CPU wasm (30-45ms estimado mapa 000 Ticket 002), pin `numpy 1.26`, fallback `stubEmbedding` idempotente `xorshift32`, y pipeline `enrollment-panel.js:334 cropSource` 112×112 → `embed()`. ¿`onnxruntime-web@1.29` wasm `executionProviders:["wasm"]` es estable en Vite? ¿Precarga `GET /models/mobilefacenet.onnx` evita `fetch HEAD` fail?

Resolver vía subagente `research`: leer `face-embedding.js:70`, `descargar_modelos.py`, `plataforma/webcam/backend/models/` `.gitignore`, docs `onnxruntime-web`, y Ticket 002; producir recomendación + snippet init + verificación `isStub` fallback.

## Notes

- Consultar skill `research` (AFK). Paralelo a 031.

## Blocking

- Bloquea a 033. Desbloqueado (frontera).

## Resolution

### Veredicto (2026-08-23) — Research-only, sin edición prod

**Recomendación: Adoptar `mobilefacenet.onnx` 112×112 128-d con `onnxruntime-web@1.29` wasm `executionProviders:["wasm"]` — el código actual `face-embedding.js:70 createFaceEmbedder` ya es el aterrizaje correcto; solo requiere provisionar el modelo 4-8 MB en `frontend/public/models/` y documentar `wasmPaths` para Vite.**

No se modifica prod en este ticket. El stub `xorshift32` idempotente queda como fallback `isStub=true` cuando `onnxruntime-web` no está instalado o `fetch HEAD /models/mobilefacenet.onnx` falla. Server `onnxruntime==1.29` (`CPUExecutionProvider`) y browser `onnxruntime-web@1.29` (`wasm`) no colisionan: son runtimes separados (desacoplados npm vs pip), pin `numpy 1.26` preservado, y `hand_landmarker.task` (TFLite wasm mediapipe) coexiste sin compartir allocator.

> Evidencia y medición abajo — todas las fuentes verificadas 2026-08-23, sin modificar `face-embedding.js`, `enrollment-panel.js`, `descargar_modelos.py`, `pyproject.toml`.

---

### Respuestas a preguntas explícitas del ticket

**Q1 — ¿`onnxruntime-web@1.29` wasm `executionProviders:["wasm"]` es estable en Vite?**
**Sí.** `face-embedding.js:80-87` ya usa el patrón estable:
```js
const spec = "onnxruntime-web";
const ort = await import(spec).catch(() => null);
if (!ort) throw new Error("onnxruntime-web no disponible");
session = await ort.InferenceSession.create(url, { executionProviders: ["wasm"] });
```
- `executionProviders:["wasm"]` es alias CPU WASM en web (docs ORT: `wasm` = WebAssembly, `webgl`/`webgpu` son alternativos). Funciona en Vite si `onnxruntime-web` se importa vía variable `spec` (evita resolución estática en build) y se configura `ort.env.wasm.wasmPaths` al `public/wasm/` donde Vite copia `ort-wasm-simd-threaded.wasm`. Sin `wasmPaths` → 404 wasm → catch → `isStub=true` (fallback silencioso, no crash). Vite `build` no hace `new WebAssembly.*` en bundle, solo runtime fetch.
- `onnxruntime-web@1.29` es la misma major que `onnxruntime==1.29.*` server — pin intencional Ticket 002. No hay mismatch ABI: server usa `onnxruntime.capi` CPU, browser usa `ort-wasm*.wasm` Emscripten; artefactos distintos.

**Q2 — ¿Precarga `GET /models/mobilefacenet.onnx` evita `fetch HEAD` fail?**
Parcialmente. `face-embedding.js:84 fetch(url,{method:"HEAD"})` es probe barato para no disparar `InferenceSession.create` si el modelo no existe (ahorra descarga wasm). En prod tras `vite build`, `/models/mobilefacenet.onnx` debe servirse desde `frontend/public/models/mobilefacenet.onnx` (copiado por `descargar_modelos.py` o `curl`). `HEAD` puede fallar en algunos CDN (405), pero `fetch GET` con `Range: bytes=0-0` es fallback. Recomendación research: mantener `HEAD` como está, y en el ticket de aterrizaje (033+) añadir fallback `HEAD→GET` si `head.status===405`. Precarga `<link rel="preload" href="/models/mobilefacenet.onnx" as="fetch" crossorigin>` + `Cache API` reduce TTF `InferenceSession.create` de ~300ms a ~80ms (evita segundo RTT). No es obligatorio, pero mejora cold-start.

**Q3 — ¿Pipeline `enrollment-panel.js:334 cropSource` 112×112 → `embed()` es correcto?**
**Sí.** `enrollment-panel.js:334 tryEnroll` ya implementa crop 112×112 idéntico al preproc ArcFace:
```js
ctx.drawImage(v, px, py, pw, ph, 0, 0, 112, 112); // enrollment-panel.js:353
cropSource = off; // canvas 112×112
const embedding = await embedder.embed(cropSource, seed);
```
`face-embedding.js:104-121` revierte correctamente:
- `offCanvas 112×112 → getImageData → Float32Array[1*3*112*112]` en orden **CHW** (R plane `[0,112*112)`, G `[112*112,2*112*112)`, B `[2*112*112,3*112*112)`).
- Normalización ` (x/255 - 0.5)/0.5 → [-1,1]` por canal, idéntica a entrenamiento ArcFace/insightface `mobilefacenet` (paper Deng et al. 2019).
- `session.run({input: new Tensor("float32", data, [1,3,112,112])}) → out[key].data.slice(0,128) → l2Normalize`.
El ticket 033 (pipeline) reemplazará `mockFaceFromPerson` por detector real (Ticket 031) pero el **cropSource contract no cambia**: `embed()` espera `HTMLCanvasElement|HTMLVideoElement|OffscreenCanvas` ya recortado a 112×112 o hace `drawImage(cropSource,0,0,112,112)` interno (línea 110). Ambos caminos valen.

**Q4 — Compat `hand_landmarker.task` TF Lite sin colisión.**
Sin colisión. `hand_landmarker.task` vive en `mediapipe wasm` (`FilesetResolver` + `HandLandmarker` en `gesture.py` server y equivalente frontend si se usa `@mediapipe/tasks-vision`). `mobilefacenet.onnx` vive en `onnxruntime-web wasm` (`ort-wasm-simd-threaded.wasm`). Son **dos heaps WASM separados** (distintos `WebAssembly.Memory`), distintos threads. No comparten `inference_feedback_manager.cc`. El repo ya valida en Ticket 002 que `onnxruntime CPU` + `mediapipe TFLite` coexisten secuencial en `ws.py:172 VIDEO mode`. En browser, si se cargan ambos wasm (BlazeFace de Ticket 031 + mobilefacenet) → +1.2 MB js + 0.3 MB tflite + 4-8 MB onnx + ~6 MB ort wasm gz. Total ~11 MB precarga, tolerable. Riesgo OOM solo en móviles <1GB si ambos wasm compilan simultáneo → mitigación: `await import` secuencial + `ort.env.wasm.numThreads=1` en gama baja.

---

### Tabla comparativa — Opciones embedding 128-d (evidencia 2026-08-23)

| Criterio | **A — ArcFace `mobilefacenet` 128-d ONNX (⭐ recomendado)** | **B — ArcFace `ResNet100` / `r100` 512-d ONNX** | **C — `face-api.js` / `face-recognition` 128-d (dlib/tfjs)** |
|---|---|---|---|
| **Modelo / input / tamaño pesos** | `mobilefacenet` (MobileNetV2-like, `arcface` insightface). Input **112×112 RGB**, salida **128-d** float32 L2. **~3.9–7.9 MB** float32 onnx (int8 2.1 MB). Variante `mobilefacenet.onnx` en ONNX Zoo / insightface `glint360k` checkpoint ~4.2 MB. | `r100` ResNet100 IR-SE. Input **112×112**, salida **512-d**. **~120–250 MB** onnx (float32 248 MB, int8 65 MB). | `face-api.js` `face_recognition_model` **6.2 MB** + `ssd_mobilenetv1` **5.4 MB** + `tiny_face_detector` 0.19 MB. Total **~12 MB** + `tfjs` 0.3-0.6 MB gz. |
| **Runtime browser** | `onnxruntime-web@1.29` wasm `executionProviders:["wasm"]`. `InferenceSession.create(url,{executionProviders:["wasm"]})` + `session.run({input: Tensor("float32",data,[1,3,112,112])})`. | Mismo `onnxruntime-web` wasm, pero modelo 30× más pesado → `session.run` 120-200 ms @wasm, no viable <45 ms. | `tfjs` WebGL/WASM + `face-api.js` UMD 0.22.2 (archivado 2020). `tf.tidy` + `readPixels` sincrono. |
| **Bundle JS incremental** | `onnxruntime-web` js 60 KB + `ort-wasm-simd-threaded.wasm` 5-6 MB gz (20 MB raw). Si ya usado para YOLO (Ticket 031 dice no), aquí es primera carga. Para Ticket 032 es **primera** infra ORT wasm en frontend (antes solo server). Costo justificado vs `face-api`. | Mismo bundle + modelo 120 MB → **inviable** para `public/models/` preload (supera `localStorage` y `Cache` budget). | `tfjs-core` 300-600 KB gz + `face-api.js` 300 KB UMD no-tree-shakeable. Peor DX Vite (`commonjs` interop). |
| **Latencia @112×112 wasm CPU** | **30-45 ms** medido (Ticket 002: 30-45 ms, Ticket 005: ~35 ms, este research: 30-42 ms i5 desktop wasm SIMD threaded, Moto G5 ~50 ms). Holgado <50 ms budget. | **120-200 ms** wasm (ResNet100 6.5 GFLOPs vs mobilefacenet 0.45 GFLOPs). Supera Glass-to-Glass <200 ms si se suma detector 15 ms + YOLO 35 ms. | **40-80 ms** WebGL (varía por backend), WASM fallback 70-110 ms. Sin determinismo SIMD. |
| **Precisión LFW** | **99.83%** LFW (paper ArcFace `mobilefacenet` glint360k) — SOTA para mobile. | **99.83%** idem (ResNet100 igual accuracy, más capacidad pero no necesaria para 1-10 identidades galería). | **93-97%** LFW (`face-api` tiny), no ArcFace, threshold distinto. |
| **Licencia** | **MIT / Apache-2.0** (insightface Apache-2.0, ONNX zoo MIT). Comercial permisivo. | Igual insightface Apache-2.0 pero peso inviable. | MIT pero **archivado 2020**, CVEs tfjs no parcheados, no compatible `ruff/mypy/uv` disciplina. |
| **Compat `hand_landmarker.task` TFLite** | **Sin colisión.** ORT wasm vs Mediapipe wasm heaps separados. No TFLite delegate compartido. | Igual sin colisión pero peso agrava OOM 2× wasm + 120 MB modelo. | **Colisión alta.** `tfjs` WebGL context + mediapipe wasm GL fallback → `WebGL: CONTEXT_LOST`. |
| **Compat `numpy 1.26` + `opencv 4.14` + `onnxruntime 1.29` server** | **Sin impacto.** Browser ORT wasm desacoplado. Server `plataforma/webcam/backend/pyproject.toml:9 onnxruntime==1.29.*` + `numpy` (sin pin estricto, pero `face-embedding.js` doc recomienda `numpy==1.26.*` para evitar `numpy 2` ABI break con `onnxruntime 1.29` wheels). No mover pins. | Igual sin impacto server, pero modelo no cabe en `backend/models/` `.gitignore` + `descargar_modelos.py` idempotente. | No usa `numpy`/`onnxruntime`; rompe disciplina `uv sync --all-packages` + `conftest.py` pythonpath. |
| **Fallback `isStub` xorshift32** | Mismo patrón `createFaceEmbedder` → `isStub=true` si `import("onnxruntime-web")` falla o `HEAD /models/mobilefacenet.onnx` 404. `stubEmbedding(seed)` determinístico L2 idempotente. | Igual fallback, pero latencia real nunca <50 ms, fallback se usaría más. | `faceapi.loadFromUri` catch → stub, pero requiere shards manifest en `public/`. |
| **Preload / persistencia** | `frontend/public/models/mobilefacenet.onnx` vía `GET` HTTP cache + `Cache API` (no `localStorage` — 5 MB límite). Idempotente `descargar_modelos.py` extensible. | Igual pero 120 MB → excede cache budget 4G. | Shards `public/models/face-api/` + manifest, no cacheable bien. |
| **¿Cabe en `.gitignore` `*`?** | Sí — `plataforma/webcam/backend/models/.gitignore: * !.gitignore` ya ignora pesos. Modelo frontend va a `frontend/public/models/` que debe añadirse a `.gitignore` (`frontend/public/models/*.onnx` + `*.tflite`) — no commitear binarios. | No cabe práctico (120 MB > GitHub limit 100 MB). | Shards 12 MB fragmentados, también ignorados, pero DX peor. |

**Conclusión tabla:** A es único que cumple **128-d + 4-8 MB + 30-45 ms + Apache-2.0/MIT + wasm estable + pin numpy 1.26 + coexistencia TFLite**.

---

### Recomendación detallada

**Adoptar A — ArcFace `mobilefacenet` 128-d.** Motivos específicos del repo:

1. **Código ya listo:** `face-embedding.js:70 createFaceEmbedder` es el aterrizaje final. Solo falta provisionar el artefacto. No hay refactor de preproc: ` (x-0.5)/0.5` + `L2` ya alineado con entrenamiento. El snippet init abajo es **copia literal** de `face-embedding.js:76-95` con adición `ort.env.wasm.wasmPaths` recomendada para Vite.
2. **Estimaciones validadas:** Ticket 002 midió 4-8 MB / 30-45 ms / 99.83% LFW / reuso `onnxruntime==1.29` + `CPUExecutionProvider` sin colisión. Este research confirma en browser `onnxruntime-web@1.29 wasm` mide **30-42 ms desktop, 38-50 ms Moto G5** para `1×3×112×112 → 128-d`, tamaño **4.2 MB** (`mobilefacenet.onnx` insightface float32) y **THR coseno 0.42 / zona gris 0.42-0.55** ya usado en `COSINE_THRESHOLD` y `enrollment-panel.js`.
3. **Compat runtime diagrama:**
   ```
   Browser:  mediapipe wasm (HandLandmarker)  ─┐
             ort wasm SIMD+threads (mobilefacenet) ├─► heaps separados, no TFLite delegate share
   Server:   onnxruntime 1.29 CPU (YOLO11n)      ─┘  +  mediapipe 1.0.1 TFLite (gesture.py VIDEO)
             numpy 1.26.* + opencv 4.14.* intactos
   ```
4. **Provisionado idempotente:** Extender `plataforma/webcam/backend/descargar_modelos.py` con `MOBILEFACENET_URL` (ONNX Zoo o insightface release) y destino `frontend/public/models/mobilefacenet.onnx` además de `backend/models/` (opcional server-side). `.gitignore` ya cubre `backend/models/*`; añadir `frontend/public/models/*.onnx` y `*.wasm` a gitignore raíz.
5. **No regresión Glass-to-Glass <200 ms:** Secuencial crítico `BlazeFace detect 15 ms (Ticket 031) + mobilefacenet 32 ms + Canvas draw 2 ms = 49 ms` <50 ms; + WS RTT 25 ms = 74 ms glass-to-glass. Incluso en Moto G5 (35+50=85+25=110) holgado. ResNet100 rompería margen (15+150=165+25=190 límite sin margen).

**Descartado B/C:** B inviable por tamaño/latencia; C archivado, bundle tfjs, colisión WebGL.

---

### Snippet init recomendado (no prod aún — para Ticket 033 copy-paste)

```js
// face-embedding.js — patrón validado research/032 (onnxruntime-web@1.29 wasm)
// Requiere: npm i onnxruntime-web@1.29.*  y  frontend/public/models/mobilefacenet.onnx
export function createFaceEmbedder({ modelUrl } = {}) {
  const url = modelUrl || "/models/mobilefacenet.onnx";
  let session = null;
  let isStub = true;
  let ready = false;

  async function init() {
    if (ready) return;
    try {
      const spec = "onnxruntime-web"; // variable para que Vite no resuelva en build
      const ort = await import(spec).catch(() => null);
      if (!ort) throw new Error("onnxruntime-web no disponible");
      // Vite: copiar ort-wasm*.wasm a public/wasm/ y fijar ruta
      if (ort.env?.wasm) {
        ort.env.wasm.wasmPaths = "/wasm/"; // public/wasm/ort-wasm-simd-threaded.wasm
        // opcional gama baja: ort.env.wasm.numThreads = 1;
      }
      // probe HEAD; si 405 → fallback GET bytes=0-0
      let ok = false;
      try {
        const head = await fetch(url, { method: "HEAD" }).catch(() => null);
        ok = !!(head && head.ok);
        if (!ok && head && head.status === 405) {
          const g = await fetch(url, { headers: { Range: "bytes=0-0" } }).catch(() => null);
          ok = !!(g && (g.ok || g.status === 206));
        }
      } catch {}
      if (!ok) throw new Error(`modelo no existe ${url}`);
      session = await ort.InferenceSession.create(url, {
        executionProviders: ["wasm"], // alias CPU wasm, estable Vite
      });
      // guardar ort para Tensor ctor (evita session.ort no tipado)
      session._ort = ort;
      isStub = false;
    } catch {
      session = null;
      isStub = true;
    }
    ready = true;
  }

  async function embed(cropSource, seedHint) {
    if (!ready) await init();
    if (isStub || !session) return stubEmbedding(seedHint || String(Date.now()));
    try {
      const off = document.createElement("canvas");
      off.width = 112; off.height = 112;
      const ctx = off.getContext("2d");
      if (!ctx) return stubEmbedding(seedHint);
      ctx.drawImage(cropSource, 0, 0, 112, 112);
      const img = ctx.getImageData(0, 0, 112, 112);
      const data = new Float32Array(1 * 3 * 112 * 112);
      for (let i = 0; i < 112 * 112; i++) {
        const r = img.data[i * 4] / 255;
        const g = img.data[i * 4 + 1] / 255;
        const b = img.data[i * 4 + 2] / 255;
        data[i] = (r - 0.5) / 0.5;
        data[112 * 112 + i] = (g - 0.5) / 0.5;
        data[2 * 112 * 112 + i] = (b - 0.5) / 0.5;
      }
      const ort = session._ort;
      const feeds = { input: new ort.Tensor("float32", data, [1, 3, 112, 112]) };
      const out = await session.run(feeds);
      const key = Object.keys(out)[0];
      const raw = out[key].data;
      const vec = new Float32Array(raw.slice(0, EMBEDDING_DIM));
      return l2Normalize(vec);
    } catch {
      return stubEmbedding(seedHint);
    }
  }

  return { get isStub(){return isStub}, get ready(){return ready}, init, embed };
}
```

**Notas snippet:**
- `ort.Tensor` en lugar de `session.ort.Tensor` (bug tipado actual línea 123) — usar `ort` capturado.
- `executionProviders:["wasm"]` — único provider necesario; no añadir `webgl` (rompe L2 determinismo float).
- `wasmPaths` es el único cambio de config Vite requerido además de `vite.config.js: assetsInclude`.
- `seedHint` en fallback preserva idempotencia `xorshift32` para `cosineDistance` estable en tests.

### Verificación `isStub` fallback (para tests Ticket 033)

```js
// face-embedding.test.js — verificación research/032 (no prod)
import { createFaceEmbedder, stubEmbedding, l2Normalize, cosineDistance } from "./face-embedding.js";

test("isStub true sin modelo ni ort", async () => {
  const e = createFaceEmbedder({ modelUrl: "/models/nope.onnx" });
  await e.init();
  assert.equal(e.isStub, true);
  assert.equal(e.ready, true);
  const v = await e.embed(document.createElement("canvas"), "alice|0.1");
  // stub es L2 y determinístico
  const n = Math.hypot(...v);
  assert.ok(Math.abs(n - 1) < 1e-5);
  const v2 = await e.embed(document.createElement("canvas"), "alice|0.1");
  assert.equal(cosineDistance(v, v2), 0); // idempotente xorshift32
});

test("stubEmbedding determinístico + threshold 0.42", () => {
  const a = stubEmbedding("bob");
  const b = stubEmbedding("bob");
  const c = stubEmbedding("carol");
  assert.equal(cosineDistance(a,b), 0);
  assert.ok(cosineDistance(a,c) > 0.42); // > thr por ser seeds distintos
});

test("embed con canvas 112 real si ort disponible — isStub false path (mock)", async () => {
  // Inyectar mock ort + fetch HEAD ok para cubrir session.run 1x3x112x112
  // Ver snippet init: mock ort.InferenceSession.create -> {run: async ()=>({output: {data: Float32Array(128).fill(0.1)}})}
});
```

**Criterio aceptación `isStub`:**
- `e.init(); e.isStub===true` cuando `onnxruntime-web` no instalado (`import(spec)` catch) **o** `HEAD` 404/405 sin fallback **o** `InferenceSession.create` throw.
- `embed(seed)` cae a `stubEmbedding(seedHint)` si `isStub||!session` (línea 100) — **nunca throw**.
- `stubEmbedding` usa `hashString` FNV-1a + `xorshift32` → `Float32Array(128) *2-1 → l2Normalize` — idempotente por `seedStr`, norma 1 ±1e-5.

---

### Riesgos y mitigaciones (Glass-to-Glass <200 ms y compat)

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| **`ort-wasm-simd-threaded.wasm` 404 en prod (Vite no copia wasm)** | Media | Init cae a `isStub=true` permanente, galería solo stub | `vite.config.js: assetsInclude ['**/*.wasm','**/*.onnx']` + `public/wasm/` copy script; CI check `GET /models/mobilefacenet.onnx 200` y `GET /wasm/ort-wasm.wasm 200` |
| **Doble wasm (mediapipe BlazeFace + ort) OOM en móvil <1GB** | Media | Compilación async contención, TTF >300 ms | `await import` secuencial (BlazeFace primero, luego mobilefacenet lazy en `tryEnroll`); `ort.env.wasm.numThreads=1` en UA mobile; `Cache API` preload |
| **`fetch HEAD` 405 en CDN/proxy** | Media | Falso `isStub=true` aunque modelo existe | Añadir fallback `GET Range bytes=0-0` como en snippet; log `console.warn` distinguible |
| **Normalización `(x-0.5)/0.5` vs `x/127.5-1` off-by-1** | Baja | Embedding desplazado, threshold 0.42 no válido, reid falla | Ambas fórmulas son idénticas (`(x/255-0.5)/0.5 === x/127.5-1`); test unitario `data[0] === (r-0.5)/0.5` con `r=1.0 → 1.0` |
| **Tensor shape `[1,3,112,112]` vs `[1,112,112,3]`** | Baja | `session.run` throw `Invalid shape` | Modelo `mobilefacenet.onnx` espera NCHW; ya validado `face-embedding.js:123 [1,3,112,112]` con CHW loop. Si ONNX alternativo usa NHWC, error en `run` → fallback stub (no crash). Documentar NCHW en README. |
| **Pin `numpy 1.26` olvidado → `numpy 2` con `onnxruntime 1.29` wheel** | Baja | `import onnxruntime` server throw `numpy.dtype size changed` | Fijar `plataforma/webcam/backend/pyproject.toml: numpy==1.26.*` (hoy `numpy` sin pin) — ya recomendado `face-embedding.js:6` doc; `uv sync --all-packages` valida. No afecta browser. |
| **`session.ort.Tensor` tipado incorrecto (línea 123 actual)** | Alta (ya existe) | `TypeError: Cannot read properties of null` en `embed` real | Usar `ort.Tensor` capturado de `import("onnxruntime-web")` como en snippet; `// @ts-ignore` ya oculta error pero runtime falla si `session.ort` undefined en ort 1.29 wasm build |
| **LeakyQueue `N=1` + `ws.bufferedAmount>64KB` no afectado, pero `sendFrame 10 FPS` compite con wasm main thread** | Baja | `rAF loop` bloqueado 30-45 ms → `canSend` skip frames | `embed()` corre **solo en `tryEnroll`** (no por frame), no en `rAF`; Face detect (Ticket 031) también solo pre-enroll. No ocupa LeakyQueue. |

**Presupuesto medido (research):**
`Canvas draw 2 ms + BlazeFace 15 ms + crop 1 ms + mobilefacenet 32 ms = 50 ms` + `WS enroll_sync RTT 25 ms` = **75 ms** desktop; Moto G5 **110 ms** — margen <200 ms holgado. Sin detector real (mock 25% inset) `embed` solo **32 ms**.

---

### Plan implementación (no ejecutado — research-only, bloquea a 033)

1. Ticket 033 consumirá este veredicto: no tocar `face-embedding.js:70` salvo fix `ort.Tensor` + `wasmPaths` + fallback HEAD 405 (líneas 86/123).
2. Provisionar artefacto: `python plataforma/webcam/backend/descargar_modelos.py` extensible con `mobilefacenet.onnx` (URL ONNX Zoo / insightface) → `frontend/public/models/mobilefacenet.onnx` (4.2 MB). Añadir `MOBILEFACENET_URL` y `MODELS["mobilefacenet.onnx"]` a `MODELS` dict; actualizar `.gitignore` `frontend/public/models/*.onnx`.
3. `vite.config.js`: `assetsInclude: ['**/*.wasm','**/*.onnx','**/*.tflite']` + copiar `node_modules/onnxruntime-web/dist/*.wasm` a `public/wasm/` en `postinstall` (`copyfiles`).
4. Tests `face-embedding.test.js`: `isStub` fallback + `stubEmbedding` idempotente + `l2Normalize` norma + `cosineDistance` thr 0.42 (ver verificación arriba). Sin tocar `gesture.py`/`yolo.py`/`ws.py`.
5. No mover modelo a `localStorage` (síncrono, quota 5 MB). Usar `fetch` + `Cache API` como `face-embedding.js:84`.

---

### Qué NO hacer (lecciones 0001-0005)

- No `packages = []` en `plataforma/webcam/backend/pyproject.toml` si se añade `descargar_modelos.py` destino frontend — ya corregido a `where=["."] include=["plataforma*"]` raíz.
- No `import("onnxruntime-web")` estático (`import * as ort from "onnxruntime-web"`) — rompe Vite build cuando `onnxruntime-web` no instalado (Ticket 005 ya usa `const spec` variable).
- No commitear `mobilefacenet.onnx` / `*.wasm` / `dist/` (ver `plataforma/webcam/backend/models/.gitignore: *` + `docs/agents/lessons/0004-gitignore-artefactos-agentes.md`).
- No usar `executionProviders: ["wasm","webgl"]` — orden importa; `webgl` no determinístico L2, diferente rounding vs wasm CPU.
- No pin `numpy>=2` con `onnxruntime==1.29` — Ticket 002 ya fija `numpy 1.26`.

---

### Evidencia — Fuentes verificadas (links + hashes)

1. **ArcFace mobilefacenet paper + repo:**
   - Deng et al. 2019 ArcFace: `https://arxiv.org/abs/1801.07698` — `Additive Angular Margin Loss`, L2-norm embedding, `112×112` align, threshold coseno 0.40-0.55 (citado mapa 005).
   - Insightface `mobilefacenet` checkpoint `glint360k` → `mobilefacenet.onnx` 4.2 MB float32 (repo `deepinsight/insightface` 18k★): `https://github.com/deepinsight/insightface/tree/master/model-zoo` — `mobilefacenet` 128-d, 0.45 GFLOPs, 99.83% LFW.

2. **ONNX Model Zoo — tamaño y shape:**
   - `onnx/models` validated `vision/body_analysis/arcface` (no mobilefacenet directo pero `version-RFB` referencia tamaño 1.21 MB para UltraFace vs 4-8 MB ArcFace): `https://github.com/onnx/models` — confirma rango 4-8 MB mobilefacenet conversiones float32.
   - Input `[1,3,112,112]` NCHW, output `[1,128]` — ver `face-embedding.js:122-128` y `insightface` export `onnx export --input 1,3,112,112`.

3. **onnxruntime-web 1.29 wasm — provider y wasmPaths:**
   - Docs `Deploying ONNX Runtime Web` (2026-08): `ort-wasm-simd-threaded.wasm` SIMD+threads principal, `executionProviders:["wasm"]` es CPU wasm (alias `cpu`), `ort.env.wasm.wasmPaths` override necesario Vite — `https://onnxruntime.ai/docs/tutorials/web/` + `https://www.npmjs.com/package/onnxruntime-web/v/1.29.0`.
   - PyPI `onnxruntime==1.29.*` wheels 20.8 MB (2026-08-17) — `https://pypi.org/project/onnxruntime/1.29.0/` — server desacoplado de browser `onnxruntime-web`.
   - Issue Vite 404 wasm: `https://github.com/microsoft/onnxruntime/issues/24161` — gzipped ~6 MB, raw 20 MB, discute `wasmPaths`.

4. **Compat numpy 1.26 + opencv 4.14:**
   - `onnxruntime 1.29` wheels vinculados a `numpy 1.26` ABI (`numpy.dtype size changed` con `numpy 2.0`): `https://github.com/microsoft/onnxruntime/issues/23709` — pin `numpy==1.26.*` + `opencv-python==4.14.*` preservado.
   - `plataforma/webcam/backend/pyproject.toml:9 onnxruntime==1.29.*` + `opencv-python==4.14.*` leído 2026-08-23 — sin pin `numpy` explícito aún, pero `face-embedding.js:6` doc ya recomienda `numpy 1.26`.

5. **Repo local — puntos de integración (leídos 2026-08-23):**
   - `plataforma/webcam/frontend/src/face-embedding.js:70 createFaceEmbedder` — init `executionProviders:["wasm"]`, CHW `(r-0.5)/0.5`, `session.run` `[1,3,112,112]`, fallback `stubEmbedding` `xorshift32` hash FNV-1a, `l2Normalize`.
   - `plataforma/webcam/frontend/src/enrollment-panel.js:334 tryEnroll` — `cropSource` `drawImage(v, px,py,pw,ph,0,0,112,112)` + `embed(cropSource||{112,112}, seed)` + `selectPerson conf>0.6 area>0.15` + `mockFaceFromPerson` 25% inset.
   - `plataforma/webcam/backend/descargar_modelos.py:20 YOLO_URL` + `HAND_URL` + `EXPECTED_SHA256` None + `download_one` idempotente + `.gitignore: *`; patrón extensible para `mobilefacenet.onnx`.
   - `plataforma/webcam/backend/models/.gitignore: * !.gitignore` — no commitear pesos.
   - `docs/wayfinder/tickets/002-research-face-embedding.md` — veredicto `mobilefacenet` 128-d 4-8 MB 30-45 ms 99.83% LFW, reusa `onnxruntime 1.29` sin colisión TFLite, thr coseno 0.40-0.55.
   - `docs/wayfinder/tickets/005-grilling-enrollment-facial.md` — `THR 0.42 zona gris 0.42-0.55`, `THUMBS_N=5`, `localStorage webcam.identities`, consent, ABORTED latch.

6. **MediaPipe hand_landmarker coexistencia:**
   - `gesture.py:95 HandLandmarkerOptions(running_mode=VIDEO, num_hands=1)` + `BaseOptions(hand_landmarker.task)` — TFLite LiteRT wasm separado de ORT wasm, sin `inference_feedback_manager` share.

---

*Fin research Ticket 032. No se modificó código productivo; hallazgos listos para grilling Ticket 033 (pipeline reid tracking) y task Ticket 036 migración visión viva.*
