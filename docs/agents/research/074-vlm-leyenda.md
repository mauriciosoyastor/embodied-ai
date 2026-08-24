# 074 — Research: VLM 1Hz LeyendaEscena (Groq vision primario vs HF Router/Gemini fallback)

> **Rama:** `research/074-vlm-leyenda` · **Ticket:** [#74](https://github.com/mauriciosoyastor/embodied-ai/issues/74) · **Mapa:** [#71 Percepción Enriquecida v2](https://github.com/mauriciosoyastor/embodied-ai/issues/71) · **Fecha:** 2026-08-24 · **Tipo:** `wayfinder:research` AFK

## TL;DR — Scannable en 2 min

**Groq `meta-llama/llama-4-scout-17b-16e-instruct` (reemplazo oficial de `llama-3.2-11b-vision-preview` decommissioned 2025-04-14) es primario 1Hz por latencia p50 ~350-600 ms, free-tier 30 RPM / 1K RPD / 30K TPM, $0.11/$0.34 por 1M y `OPENAI_BASE_URL=https://api.groq.com/openai/v1` nativo. Secundario HF Router (`Qwen2.5-VL-3B-Instruct` o `Llama-3.2-11B/3B-Vision` vía `https://router.huggingface.co/v1` con `HF_TOKEN`, $0.10 crédito free) y terciario Gemini `gemini-2.0-flash`/`gemini-2.5-flash` vía `google-genai` si `GOOGLE_API_KEY` (15 RPM / 1500 RPD free, $0.10/$0.40 por 1M). 429 con `retry-after` header, leaky-skip 1/30 (=1Hz sobre 10 FPS) con `frame_id % 30 == 0` y TTL Whiteboard 2.0s. Cadena recomendada `Groq → HF → Gemini → mock` con `OPENAI_BASE_URL` override por request.**

| Proveedor / Modelo | **Endpoint `OPENAI_BASE_URL`** | **Input 640px jpeg_b64** | **p50 / p95 (640px, 1Hz leaky-skip)** | **RPM / RPD / TPM** free | **Costo pay-go** | **429 handling** | **Recomendación** |
|---|---|---|---|---|---|---|---|
| **Groq `meta-llama/llama-4-scout-17b-16e-instruct` (MoE 17B act, 109B total, 5 imágenes, 128K ctx)** — reemplazo `llama-3.2-11b-vision-preview` (deprecated 2025-04-14) | `https://api.groq.com/openai/v1` (`GROQ_API_KEY`, `GROQ_MODEL`) | `image_url: data:image/jpeg;base64,<b64>` OpenAI-compatible | **p50 ~380-550 ms** (LPU 594 tok/s) / **p95 ~900 ms-1.5 s** (cold + retry) | **30 / 1K / 30K** (TPD 500K) org-level | **$0.11 in / $0.34 out** por 1M (blended $0.168, 3:1) | `429` + `retry-after: 2` + `x-ratelimit-*` headers; backoff 1s→2s→4s; respeta header | **Primario 1Hz** — más rápido, libre, OpenAI-compatible sin deps extra |
| **Groq `llama-3.2-11b-vision-preview` (legacy)** | mismo Groq endpoint | igual | n/a — **decommissioned** | n/a | n/a | n/a → `model_decommissioned` 400 | **Descartado** — `code: model_decommissioned` desde 2025-04-14, reemplazo Scout obligatorio |
| **HF Router `Qwen/Qwen2.5-VL-3B-Instruct` (3B, 64K, 4-16k vis tokens)** | `https://router.huggingface.co/v1` (`HF_TOKEN`, `OPENAI_BASE_URL_FALLBACK`) | igual OpenAI-compatible (`content: [{type:text},{type:image_url}]`) | **p50 ~600-1100 ms** / **p95 ~1.8-3 s** (Hyperbolic/Novita routing, cold start) | **~30 RPM / ~1K RPD** (vía créditos $0.10/mes free, luego pay-go por provider) | **~$0.25 in / $0.75 out** (OpenRouter proxy; HF pass-through sin markup, provider ~ $0.25/$1.0) | `429` RateLimit + `500 Internal Error` vision intermitente (issue #3688) — retry + fallback Gemini | **Secundario si Groq 429/500** — requiere `HF_TOKEN`, latencia mayor |
| **HF Router `meta-llama/Llama-3.2-11B-Vision-Instruct` / `3B-Vision`** | igual `router.huggingface.co/v1` | igual | p50 ~800 ms-1.2 s / p95 ~2-3.5 s | igual créditos HF | ~$0.20-$0.60/1M (por provider Novita/Together) | igual 429/500 | Alternativa 11B si Qwen 3B no alcanza calidad español |
| **Gemini `gemini-2.0-flash` (o `2.5-flash`)** — **no OpenAI-compatible, usa `google-genai`** | `generativelanguage.googleapis.com` (`GOOGLE_API_KEY`, `GEMINI_MODEL`) | `genai.Client.models.generate_content` (prompt + inline `image` bytes) | **p50 ~300-500 ms** / **p95 ~800 ms-1.2 s** (Google) | **15 RPM / 1500 RPD / 1M TPM** free (paid $0.10 in / $0.40 out, cache $0.025) | **Free $0** (free-tier) luego **$0.10 in / $0.40 out** | `429 ResourceExhausted` + `retry-after`; free-tier 15 RPM estrecho | **Terciario si `GOOGLE_API_KEY`** — no OpenAI base_url, código distinto |
| **Mock fallback** | n/a | n/a | <1 ms | ilimitado | $0 | n/a | **Final** en `percepcion-panel` si 401/429 corta — `caption: "Escena no disponible"` |

**Contrato `Envelope` propuesto:** `scene_caption { frame_id: int, caption: str (es-AR 1 frase ≤20 palabras), objects: string[] (COCO whitelist), conf: float 0-1, source: "groq"|"hf"|"gemini"|"mock" }` — **TTL Whiteboard `PercepcionVista.leyenda` 2.0 s** (1Hz, 2× período), canal separado del piggyback `postura`/`profundidad` 5Hz, sin nuevo socket.

---

## Pregunta (Issue #74)

> Comparativa **VLM 1Hz para LeyendaEscena** (`scene_caption`) con cadena fallback existente (`plataforma/webcam/backend/app.py:67` Groq→HF→Gemini→mock, `fase-1/gemini_client.py`).
> Evaluar: Groq `llama-3.2-11b-vision-preview` (primario) vs HF Router `Qwen2-VL 2B` / `Llama-3.2-3B-vision` vs Gemini vision si `GOOGLE_API_KEY`. Métricas: latencia p50/p95 con jpeg_b64 640px (leaky-skip 1/30), RPD/RPM, cuota free-tier, costo, `OPENAI_BASE_URL` override por request, prompt `Describe escena en 1 frase es-AR`, manejo 429 retry-after. Envelope: `type: scene_caption {frame_id, caption: str, objects: [str], conf}` 1Hz separado del piggyback pose/depth; fallback mock en `percepcion-panel` si 401 corta.

Bloquea: contrato `WhiteboardState.PercepcionVista.leyenda` y presupuesto Glass-to-Glass (VLM 1Hz ~300 ms tolerado canal lento, no lazo cerrado).

## Contexto local — plataforma/webcam

- **Cadena vigente (fuente primaria local):** `plataforma/webcam/backend/app.py:67` `VozHandler` implementa **Groq primario (Ticket 021) → HF Router secundario → Gemini legacy → OpenAI fallback → mock**. `fase-1/gemini_client.py:15` `MODELO_DEFECTO="openai/gpt-oss-20b"`, `MODELO_GEMINI_LEGACY="gemini-2.0-flash"` (`l.18`), `_es_muse_spark` (`l.21`) detecta `llama|qwen|groq|gpt-oss` y usa `OPENAI_BASE_URL` si está seteado, despacha por `crear_cliente_openai()` (`l.70`) con `OpenAI(api_key, base_url)` (`l.78`). `cargar_clave` (`l.37`) prioriza `GROQ_API_KEY > HF_TOKEN > OPENCODE/CURSOR/OPENAI_API_KEY > GOOGLE_API_KEY`. Este ticket **extiende** esa cadena a **visión** (image_url) sin romper voz texto.
- **`OPENAI_BASE_URL` override por request:** `app.py:108-125` HF fallback guarda `orig_base = os.getenv("OPENAI_BASE_URL")`, setea `os.environ["OPENAI_BASE_URL"]=hf_base` (`https://router.huggingface.co/v1`), llama `gemini_client.responder(..., modelo="meta-llama/Llama-3.2-3B-Instruct")`, y restaura en `finally`. Patrón reutilizable para VLM: override temporal por intento sin mutar global entre requests concurrentes (riesgo race — mejor pasar `base_url` explícito al cliente OpenAI, §4).
- **WebSocket existente:** `plataforma/webcam/backend/ws.py:40` `EnvelopeType` hoy `{frame,detecciones,gesto,estado,enroll_sync,...}`, `ws.py:129` `LeakyQueue N=1` + `AsyncLeakyQueue`, `ws.py:321` `process_single_frame` sync, `ws.py:379` `receiver`/`processor` con `asyncio.create_task`. `frontend/ws-client.js:22` `MAX_FPS 10` + `bufferedAmount>64KB` skip, `frontend/src/main.js` hidratación `Whiteboard` (por `ws.py` TTLs: `detecciones 0.2 s`, `gesto 0.5 s`, `postura 1.0 s` — leyenda 2.0 s nueva).
- **VLM no es lazo cerrado:** mapa #71 Notes — `Glass-to-Glass <200 ms innegociable para lazo cerrado`, `VLM 1Hz ~300 ms p50 tolerado en canal lento`. VLM no compite con `intra_op_num_threads=2` ONNX (HTTP externo, libera GIL en `asyncio.to_thread` + `httpx`).
- **Imagen fuente:** `ws-client.js:140` `canvasOrVideoToJpegB64` 640px `quality 0.75` (~45 KB JPEG). VLM reutiliza el mismo `jpeg_b64` del `frame` (no recodifica). 640px ≈ 1290 tokens Gemini (ver pricing), ~600-1100 tokens Groq image (según patch).
- **Mock existente:** `app.py:163-191` fallback texto por patrones `hola/registr/quien`; para VLM mock equivalente en `percepcion-panel` si 401/429 corta (no backend).
- **Leaky-skip 1/30 1Hz:** VLM 1Hz = 1 de cada 30 frames a 10 FPS (`frame_id % 30 == 0`), o `frame_id % 10 == 0` si frontend ya limita a 10 FPS y backend quiere 1 FPS. Con `LeakyQueue N=1` el VLM no encola frames — `asyncio.create_task` fire-and-forget cada 1s, descarta si anterior pendiente (ver §5).

## Metodología

1. **Fuentes primarias locales:** lectura directa `app.py:67-191`, `fase-1/gemini_client.py:1-106`, `ws.py:40-437`, `ws-client.js`, `pyproject.toml` (`onnxruntime==1.29.*` no aplica a VLM pero fija `intra2` budget).
2. **Fuentes primarias externas:** `console.groq.com/docs/deprecations` (tabla 2025-04-14 decommission `llama-3.2-11b-vision-preview` → `llama-4-scout`), `console.groq.com/docs/rate-limits` (RPM/RPD/TPM/TPD por modelo, headers `retry-after`, `x-ratelimit-*`), `console.groq.com/docs/model/meta-llama/llama-4-scout-17b-16e-instruct` (MoE 17B/109B, early fusion, ≤5 imágenes, 128K ctx), pricing Groq `$0.11/$0.34` (groq.com/pricing + apicents, modelpricewatch), HF Router `router.huggingface.co/v1` OpenAI-compatible (docs `inference-providers`, `pricing` $0.10/mes free, pass-through sin markup), Gemini pricing `ai.google.dev/gemini-api/docs/pricing` (`2.0 Flash` $0.10/$0.40, free 15/1500/1M), issue `huggingface_hub#3688` 500 vision intermitente.
3. **Latencia estimada:** sin medición live en repo (VLM externo), se usan benchmarks publicados: Groq LPU 594 tok/s Scout, echomind PR #33 `~400 ms e2e` Scout, OpenRouter Nebius 7.15 s vs Parasail 1.25 s para Qwen2.5-VL-72B (HF Router similar), Gemini 300-500 ms (Google).
4. **Cuota:** tabla oficial Groq rate-limits 2026 (Scout 30/1K/30K/500K org-level, free), HF $0.10 free luego credits, Gemini free 15/1500/1M.

## Hallazgos

### 1. Tabla comparativa completa (VLM 640px jpeg_b64 1Hz)

| Dimensión | **Groq `llama-4-scout-17b-16e-instruct`** (primario) | **Groq `llama-3.2-11b-vision-preview` (legacy)** | **HF Router `Qwen2.5-VL-3B` (secundario)** | **HF Router `Llama-3.2-11B/3B-Vision`** | **Gemini `gemini-2.0-flash` (terciario)** |
|---|---|---|---|---|---|
| **Modelo** | `meta-llama/llama-4-scout-17b-16e-instruct` — MoE 17B activos / 109B total, 16 experts, early fusion nativo multimodal, cutoff 2024-08 | `llama-3.2-11b-vision-preview` — 11B dense, Llama 3.2 vision | `Qwen/Qwen2.5-VL-3B-Instruct` — 3B, 64K ctx, window attention, MRoPE, 4-16k vis tokens (min/max_pixels) | `meta-llama/Llama-3.2-11B-Vision-Instruct` (11B) / `3B-Vision` | `gemini-2.0-flash` (2.0 Flash, 128K) — `gemini-2.5-flash` sucesor |
| **Estado** | **Activo** (reemplazo oficial 2025-04-14); **ojo: deprecado 2026-07-17** → migrar a `openai/gpt-oss-120b` o `qwen/qwen3.6-27b` si Groq lo apaga | **Decommissioned 2025-04-14** — `model_decommissioned` 400, ver `console.groq.com/docs/deprecations` | Activo — requiere `HF_TOKEN` + Inference Providers routing | Activo | Activo; `2.0 Flash` free-tier, paid mismo modelo |
| **Endpoint** | `https://api.groq.com/openai/v1` | mismo | `https://router.huggingface.co/v1` (`:fastest`, `:cheapest`, `:provider` suffix) | igual | `generativelanguage.googleapis.com` vía `google-genai` |
| **Auth** | `GROQ_API_KEY` (env `GROQ_MODEL` override) | igual | `HF_TOKEN` (fine-grained `Inference Providers`) | igual | `GOOGLE_API_KEY` (`GEMINI_MODEL`) |
| **OpenAI-compatible** | ✅ `OpenAI(api_key, base_url)` + `chat.completions.create(model, messages=[{role:user, content:[{type:text},{type:image_url}]}])` | ✅ | ✅ `OpenAI(base_url="https://router.huggingface.co/v1", api_key=HF_TOKEN)` — `huggingface.co/docs/inference-providers/guides/responses-api` | ✅ | ❌ `genai.Client(api_key).models.generate_content(model, contents)` — no OpenAI |
| **Input 640px** | `image_url: {"url": "data:image/jpeg;base64,<b64>"}` | igual | igual | igual | `types.Part.from_bytes(data=b64_bytes, mime_type="image/jpeg")` o `inlineData` |
| **Prompt es-AR** | `system: "Sos asistente visual es-AR. Describí la escena en 1 frase (≤20 palabras)."` + `user: [{text:"Describe escena en 1 frase es-AR", image_url}]` | igual | igual | igual | `systemInstruction` + `contents=[prompt, image]` |
| **Salida** | `choices[0].message.content` → `caption` str, `objects` extraído de caption o `response_format: json_object` opcional | igual | igual | igual | `response.text` |
| **Latencia p50 640px b64** | **~380-550 ms** (Groq LPU 594 tok/s, 128K ctx; PR echomind 400 ms e2e; `~1.28 ms decode` local no aplica) | n/a | **~600-1100 ms** (HF routing + provider Hyperbolic/Novita; cold ~1.5 s) | **~800-1200 ms** (11B más pesado) | **~300-500 ms** (Google) |
| **p95 640px** | **~900 ms-1.5 s** (con retry-after 2s) | n/a | **~1.8-3 s** (500 intermitente + retry) | ~2-3.5 s | **~800 ms-1.2 s** |
| **Jitter canal 1Hz** | <50 ms si 1 req/s (30 RPM = 1 cada 2s, 1Hz cabe) | n/a | ~100-200 ms (provider routing) | similar | ~50 ms |
| **RPM free** | **30** (org-level) | n/a | ~30 (HF routing, por provider) | igual | **15** |
| **RPD free** | **1K** | n/a | **~1K** (vía $0.10 crédito, luego pay-go) | igual | **1500** |
| **TPM free** | **30K** (TPD 500K) — highest TPM free Groq | n/a | depende provider | igual | **1M** |
| **Cuota binding 1Hz** | 1Hz = 86.4K req/día si 24h continuo → **RPD 1K limita a ~16 min/día continuo**; con throttling usuario real (~8h, 1Hz = 28.8K/día) igual excede — **leaky-skip + TTL 2s + solo cuando usuario presente** necesario (§5) | n/a | $0.10 ≈ 100-400 req 3B (HF pay-go $0.25/1M) | igual | 15 RPM = 1 cada 4s → 1Hz excede free, requiere 15 RPM throttling |
| **Costo pay-go** | **$0.11 in / $0.34 out** por 1M (blended $0.168) — 1 req 640px (~1.3K in +50 out) ≈ **$0.00016** | n/a | **~$0.25 in / $0.75 out** (OpenRouter Nebius) o HF pass-through similar | ~$0.20-$0.60 | **$0.10 in / $0.40 out** (Gemini 2.0 Flash) — cache $0.025; `gemini-2.0-flash-exp` vision ~$0.00019/imagen |
| **Deps** | `openai>=1.0` + `python-dotenv` (ya en `fase-1`) | igual | igual + `HF_TOKEN` | igual | `google-genai` (ya en `fase-1/gemini_client.py` legacy) |
| **Compat `OPENAI_BASE_URL` override** | ✅ `os.getenv("OPENAI_BASE_URL")` o `OPENAI_BASE_URL_FALLBACK` por request (ver §3) | igual | ✅ `OPENAI_BASE_URL_FALLBACK=https://router.huggingface.co/v1` | igual | ❌ no aplica — `genai` separado |
| **429 handling** | `429` + `retry-after: 2` + `x-ratelimit-remaining-requests`, `x-ratelimit-reset-requests` — backoff honor header | `400 model_decommissioned` (no retry) | `429` + `500 Internal Error` vision (issue #3688) — retry 1× luego fallback Gemini/mock | igual | `429 ResourceExhausted` + `retry-after` |
| **Visión multi-imagen** | ≤5 imágenes por request (Scout) | igual | 1 imagen (Qwen 3B) | 1 imagen | múltiples |
| **Idioma es-AR** | Bueno (Llama 4 multilingüe), prompt steerable con system | — | Bueno (Qwen multilingüe) | Bueno | Excelente es-AR |
| **Riesgo** | **Scout deprecado 2026-07-17** → Groq recomienda `openai/gpt-oss-120b` (no vision) o `qwen/qwen3.6-27b` — vision puede migrar a `llama-4-maverick-17b-128e-instruct` ($0.50/$0.77) | Ya muerto | 500 vision intermitente si single provider (Hyperbolic) — usar fallback | igual | 15 RPM free muy bajo para 1Hz |

Fuentes: `console.groq.com/docs/deprecations` (2025-04-14 y 2026-07-17), `console.groq.com/docs/rate-limits`, `console.groq.com/docs/model/meta-llama/llama-4-scout-17b-16e-instruct` (MoE 17B/109B, early fusion), `groq.com/pricing` / `apicents` / `modelpricewatch` ($0.11/$0.34), `huggingface.co/docs/inference-providers` (router `https://router.huggingface.co/v1`, `:fastest`, `pricing` $0.10/mes, issue #3688 500 vision), `ai.google.dev/gemini-api/docs/pricing` (2.0 Flash $0.10/$0.40, free 15/1500/1M), `fase-1/gemini_client.py:21-80`, `plataforma/webcam/backend/app.py:67-191`.

### 2. Decommission `llama-3.2-11b-vision-preview` → `llama-4-scout-17b-16e-instruct`

- **Fecha:** `2025-04-14` — tabla `Multiple Model Deprecations` en `console.groq.com/docs/deprecations`: `llama-3.2-11b-vision-preview` y `llama-3.2-90b-vision-preview` → `meta-llama/llama-4-scout-17b-16e-instruct`. Error vivo verificado por issues `ha-llmvision#407` / `#311` y `SillyTavern#4507`: `{"error":{"message":"The model `llama-3.2-11b-vision-preview` has been decommissioned...","type":"invalid_request_error","code":"model_decommissioned"}}` 400.
- **Reemplazo:** Scout es MoE 17B activos (109B total) + early fusion multimodal nativo, 5 imágenes, 594 tok/s, $0.11/$0.34. **No es drop-in text-only** — `llama-3.1-8b-instant` es reemplazo para `llama-3.2-1b/3b-preview` text, pero vision requiere Scout/Maverick. `litellm#18062` actualiza `supports_vision: true` para Scout/Maverick.
- **Segunda deprecación:** `2026-07-17` Groq agenda shutdown de `llama-4-scout-17b-16e-instruct` (y `qwen/qwen3-32b`) hacia `openai/gpt-oss-120b` / `qwen/qwen3.6-27b` (no vision puro). Si Groq ejecuta, **vision debe migrar a `llama-4-maverick-17b-128e-instruct`** ($0.50/$0.77, 15 RPM free) o quedarse en HF Router Qwen. Documentar como riesgo y feature-flag `GROQ_VISION_MODEL` override (ver §4, patrón `echomind#33`).
- **Acción:** `GROQ_MODEL` por defecto debe ser `meta-llama/llama-4-scout-17b-16e-instruct` (no `llama-3.2-11b-vision-preview`). Si env no seteado, `gemini_client.MODELO_DEFECTO` hoy es `openai/gpt-oss-20b` (texto) — para VLM usar `GROQ_VISION_MODEL` separado o `GROQ_MODEL` con fallback a Scout.

### 3. `OPENAI_BASE_URL` override por request y cadena fallback

**Cadena existente `app.py:67` (voz):**

```python
# 1) Groq primario
if has_groq:
    modelo = os.getenv("GROQ_MODEL","").strip() or gemini_client.MODELO_DEFECTO
    text = gemini_client.responder(prompt, modelo=modelo)  # usa OPENAI_BASE_URL=https://api.groq.com/openai/v1
# 2) HF Router secundario (si 429/500)
if has_hf:
    hf_base = os.getenv("OPENAI_BASE_URL_FALLBACK","").strip() or "https://router.huggingface.co/v1"
    orig_base = os.getenv("OPENAI_BASE_URL","")
    os.environ["OPENAI_BASE_URL"] = hf_base
    try:
        text = gemini_client.responder(prompt, modelo="meta-llama/Llama-3.2-3B-Instruct")
    finally:
        restore orig_base
# 3) Gemini legacy
if has_google:
    modelo = os.getenv("GEMINI_MODEL","").strip() or gemini_client.MODELO_GEMINI_LEGACY
    text = gemini_client.responder(prompt, modelo=modelo)  # ruta genai
# 4) mock
```

**Para VLM replicar con `image_url` y sin race global:**

- **No mutar `os.environ` en concurrente** — `asyncio` puede intercalar requests. Patrón seguro: pasar `base_url` explícito al `OpenAI` client por intento, no vía env global. `gemini_client.crear_cliente_openai()` ya lee `OPENAI_BASE_URL` (`l.77`), pero para VLM crear helper `crear_cliente_vlm(base_url, api_key)` que instancie `OpenAI(api_key=..., base_url=...)` por llamada.
- **Config recomendada (env):**
  - `GROQ_API_KEY` (requerido primario), `GROQ_VISION_MODEL=meta-llama/llama-4-scout-17b-16e-instruct` (default), `OPENAI_BASE_URL=https://api.groq.com/openai/v1`
  - `HF_TOKEN` (secundario), `OPENAI_BASE_URL_FALLBACK=https://router.huggingface.co/v1`, `HF_VISION_MODEL=Qwen/Qwen2.5-VL-3B-Instruct` (o `meta-llama/Llama-3.2-11B-Vision-Instruct:hyperbolic` si se fija provider)
  - `GOOGLE_API_KEY` + `GEMINI_MODEL=gemini-2.0-flash` (terciario)
  - `VLM_ENABLED=true` feature-flag para `percepcion-panel` (si `401`/sin keys → mock)
- **Flujo VLM 1Hz:**
  1. `frame_id % 30 == 0` y `VLM_ENABLED` y `not pending_vlm` → `jpeg_b64_640 = frame_payload["jpeg_b64"]`
  2. `try: caption = await asyncio.to_thread(vlm_groq, jpeg_b64)` (Groq OpenAI client, timeout 3s)
  3. `except RateLimitError (429): retry_after = int(resp.headers.get("retry-after",2)); await sleep(retry_after); raise` → cae a HF
  4. `except (AuthError 401, RateLimit 429, Server 500): caption = await asyncio.to_thread(vlm_hf, jpeg_b64)` (HF Router, `HF_TOKEN`, mismo `image_url` schema, timeout 4s)
  5. `except: caption = await asyncio.to_thread(vlm_gemini, jpeg_b64)` (genai, timeout 3s)
  6. `except: caption = mock_caption(objects_from_yolo)` (ver §4)
  7. `Whiteboard.leyenda = LeyendaEscena(frame_id, caption, objects, conf, source, ts)` + `make_envelope("scene_caption", seq, payload)` broadcast
- **Headers rate-limit:** Groq retorna `x-ratelimit-limit-requests`, `x-ratelimit-remaining-requests`, `x-ratelimit-reset-requests` (ver `console.groq.com/docs/rate-limits` tabla headers). Loggear `remaining` para telemetría y no reintentar si `remaining==0` y `reset` >60s — directo a fallback.

### 4. Prompt es-AR, `objects` y Envelope `scene_caption`

**Prompt es-AR (1 frase, ≤20 palabras):**

```
system: "Sos asistente visual es-AR. Describí la escena en 1 frase (≤20 palabras), tono neutro, sin prefijos. Si ves personas, mencioná cantidad y acción principal."
user: [
  {"type":"text","text":"Describe escena en 1 frase es-AR. Responde solo la frase, sin comillas."},
  {"type":"image_url","image_url":{"url":"data:image/jpeg;base64,<b64>"}}
]
```

- **Por qué system + user:** Scout es *steerable* con system prompts (ver `console.groq.com/docs/model/llama-4-scout` *Use system prompts to improve steerability*). Sin system, Llama 4 tiende a prefijos *"La imagen muestra..."* — system lo suprime.
- **HF Qwen/Gemini:** mismo prompt, Qwen VL es multilingüe pero favorece inglés — forzar `es-AR` en system reduce drift.

**Salida `scene_caption`:**

```python
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LeyendaEscena:
    frame_id: int
    caption: str  # es-AR, 1 frase ≤20 palabras, ej "Una persona con remera azul levanta la mano en un escritorio."
    objects: list[
        str
    ]  # whitelist COCO curada + YOLO detecciones, ej ["person","chair","cup"]
    conf: float  # 0..1 — proxy conf VLM (Groq no da logprobs → 0.85 defecto, mock 0.0)
    source: str  # "groq"|"hf"|"gemini"|"mock"
    ts: int  # now_ms()
```

- **`objects`:** dos fuentes: (a) parse caption (`"person, chair"`), (b) `YOLO boxes` del mismo `frame_id` (`box.cls` whitelist). Preferir YOLO (ground truth) y usar caption solo para validar. `objects` no es `boxes` — es lista semántica para overlay texto.
- **`conf`:** Groq/HF no retornan conf vision — fijar `0.85` si éxito, `0.0` mock, o `1.0` si `finish_reason=="stop"` y caption no vacío. Gemini sí da `safety` pero no conf numérica — mapear a `0.85`.
- **Mock fallback:** si `401` o sin keys, `percepcion-panel` muestra `"Escena no disponible — configurá GROQ_API_KEY"` y `Whiteboard.leyenda` queda `caption="Escena no disponible (mock)"`, `objects=[]`, `conf=0.0`, `source="mock"`. No error WS.

**Contrato Envelope/Whiteboard (extiende `ws.py:40` + #72/#73):**

```python
# ws.py
EnvelopeType = Literal[
    "frame",
    "detecciones",
    "gesto",
    "estado",
    "postura",
    "profundidad",
    "scene_caption",
    "enroll_sync",
    ...,
]
# payload scene_caption (1Hz, separado de piggyback 5Hz)
{
    "frame_id": int,  # correlación con frame 640 y detecciones del mismo frame_id
    "caption": str,  # es-AR, 1 frase ≤20 palabras
    "objects": list[str],  # whitelist COCO + YOLO, [] si no hay
    "conf": float,  # 0..1
    "source": str,  # "groq"|"hf"|"gemini"|"mock"
    "ts": int,  # now_ms()
}


# WhiteboardState.PercepcionVista (extiende #72 pro + #73 prof)
class PercepcionVista:
    detecciones: list[Box] | None  # TTL 0.2 s (10 Hz)
    gesto: GestoReconocido | None  # TTL 0.5 s (10 Hz)
    postura: Postura | None  # TTL 1.0 s (5 Hz) — #72
    profundidad: ProfundidadFrame | None  # TTL 1.0 s (5 Hz) — #73
    leyenda: LeyendaEscena | None  # TTL 2.0 s (1 Hz) — NUEVO, 2× período
    identidades: ...  # ya existe
```

- **Por qué TTL 2.0s:** 1Hz período = 1s, TTL 2s = 2× período tolera 1 miss sin stale (igual `gesto 0.5s` es 5× período 0.1s, `postura 1.0s` 2× período 0.5s). Si VLM p95 1.5s, TTL 2s aún fresca; si 429, fallback mock renueva TTL.
- **Separado de piggyback:** `postura` y `profundidad` van 5Hz (`frame_id % 2 == 0`, `intra2` ORT), VLM 1Hz (`frame_id % 30 == 0`) en `asyncio.create_task` independiente con `httpx` timeout, no bloquea `process_single_frame` sync. `ws.py:379` `receiver`/`processor` ya es `asyncio.to_thread` compatible.

### 5. Leaky-skip 1/30 1Hz, presupuesto Glass-to-Glass y `bufferedAmount`

- **Leaky-skip:** `frontend/ws-client.js:22` `MAX_FPS 10` ya throttled; backend hace `if frame_id % 30 != 0: return` para VLM (1Hz = 1/30 a 30 FPS cámara, o 1/10 a 10 FPS throttled → `frame_id % 10 == 0` si cámara 30 FPS real, documentar ambos). Con `LeakyQueue N=1` el VLM no encola — `pending_vlm: bool` flag + `asyncio.create_task(vlm_once)` fire-and-forget, descarta si `pending_vlm` True (igual que `ws.py:129` leaky).
- **`ws.bufferedAmount>64KB` skip:** VLM `scene_caption` payload ~200 bytes (caption 100 chars + objects), no presiona WS. JPEG 640 b64 45 KB/frame 10Hz = 450 KB/s dominante. VLM no añade JPEG extra — reutiliza `jpeg_b64` del frame ya enviado (cliente no re-envía imagen para VLM, servidor la tiene).
- **Presupuesto Glass-to-Glass:**
  ```
  Lazo cerrado <200 ms (innegociable):
    captura + jpeg 0.75               ~8 ms
    WS send + RTT                     ~5 ms
    decode_jpeg_b64                   1.3 ms
    YOLO11n detect intra2             73.8 ms
    Hand gesto                        ~20 ms
    ─────────────────────────────────────
    total lazo                        ~108 ms  ✅

  Canal 5Hz piggyback (to_thread, no bloquea):
    YOLO11n-pose 92.7 ms  TTL 1.0s
    MiDaS small 256 42 ms TTL 1.0s

  Canal 1Hz VLM (HTTP externo, no ORT):
    Groq Scout 380-550 ms p50  TTL 2.0s  ✅ (canal lento tolerante)
    HF Qwen 600-1100 ms p50    TTL 2.0s  ✅
    Gemini 300-500 ms p50      TTL 2.0s  ✅
    p95 900 ms-1.5s aún < TTL 2.0s, pero bloquearía lazo si inline → debe ser async
  ```
  VLM nunca inline en `process_single_frame` — `asyncio.create_task` + `asyncio.to_thread` con `httpx.AsyncClient` evita GIL y no compite `intra2`.

- **Cuota 1Hz binding:** 1Hz continuo = 86.4K req/día > RPD 1K Groq/HF y >15 RPM Gemini (15/min = 1 cada 4s). **Solución:** VLM solo cuando usuario presente (`frontend` envía frames solo si `ws-client canSend()` y `video` activo), y backend VLM solo si `len(boxes)>0` o `presence` flag. Con uso real 8h/día intermitente (~2h efectivo 1Hz = 7.2K req) aún excede RPD — pero free-tier RPD es por org, no por usuario, y demo no es 24h. Documentar que **1K RPD ≈ 16 min continuo 1Hz** — suficiente para demo/sesión, no producción 24h. Para producción, pagar $0.11/1M (7.2K req/día ≈ $1.15/día) o throttlear a 0.2Hz (`frame_id % 150`).

- **429 handling detallado:**
  - Groq: `429 Too Many Requests` + `retry-after: 2` (segundos) + `x-ratelimit-remaining-requests: 0` + `x-ratelimit-reset-requests: 59.5s` + `x-ratelimit-limit-tokens`. **Respetar `retry-after`** y backoff exponencial `1s→2s→4s` cap 10s, luego fallback HF sin reintentar Groq hasta `reset`.
  - HF Router: `429` + `500 Internal Error` vision intermitente (Hyperbolic single provider) — **no reintentar HF más de 1×**, fallback Gemini.
  - Gemini: `429 ResourceExhausted` (15 RPM) — throttlear a 0.25Hz si Gemini activo.
  - **Mock:** si `401 Unauthorized` (key ausente/inválida) en Groq/HF/Gemini, no retry — directo a mock y log `logger.warning("VLM 401 %s", source)`. `percepcion-panel` muestra mock.

## Conclusión y recomendación para Envelope/Whiteboard

### Conclusión

1. **`llama-3.2-11b-vision-preview` está muerto desde 2025-04-14** — cualquier código que lo referencie retorna `model_decommissioned` 400. **Scout es reemplazo obligatorio** pero a su vez deprecado 2026-07-17; planificar `GROQ_VISION_MODEL` override.
2. **Groq Scout gana para 1Hz:** 380-550 ms p50 (LPU), 30 RPM/30K TPM/1K RPD, $0.11/$0.34, OpenAI-compatible sin deps nuevas, 5 imágenes, system steerable es-AR. HF Qwen 3B es 600-1100 ms + 500 intermitente + $0.10 crédito limitado; Gemini es rápido pero 15 RPM free y no OpenAI (deps `google-genai` distintas). Costo 1Hz continuo excede free RPD en los 3, pero demo intermitente cabe.
3. **HF Router solo como fallback Groq 429/500:** Qwen2.5-VL-3B es 3B ligero pero sin provider garantizado (Hyperbolic single) — igual que Llama-3.2-11B Vision (11B) más pesado. No primario.
4. **Gemini terciario solo si `GOOGLE_API_KEY`:** no OpenAI (`genai.Client`), 15 RPM free limita 1Hz, pero útil si Groq+HF sin keys.
5. **Leaky-skip 1/30 = 1Hz** con `frame_id % 30` (o `%10` a 10 FPS) + `pending_vlm` flag + `TTL 2.0s` es suficiente; no nuevo socket, no jitter `intra2`.

### Recomendación (para contrato Envelope/Whiteboard)

**Elegir `Groq llama-4-scout-17b-16e-instruct` primario 1Hz, HF Router `Qwen2.5-VL-3B` (o `Llama-3.2-11B-Vision`) secundario, Gemini terciario, mock final. `OPENAI_BASE_URL` override por request con `OpenAI(base_url=...)` explícito (no `os.environ` global). Prompt es-AR 1 frase ≤20 palabras con system. Envelope `scene_caption {frame_id,caption,objects,conf,source,ts}` en canal 1Hz separado, TTL Whiteboard `leyenda` 2.0s.**

#### Contrato Envelope

```python
# ws.py — nuevo type
EnvelopeType = Literal[
    "frame",
    "detecciones",
    "gesto",
    "estado",
    "postura",
    "profundidad",
    "scene_caption",
    "enroll_sync",
    ...,
]
# payload scene_caption (1Hz, separado de piggyback 5Hz)
{
    "frame_id": int,
    "caption": str,  # es-AR 1 frase ≤20 palabras
    "objects": list[str],  # whitelist COCO curada + YOLO boxes, [] si no hay
    "conf": float,  # 0..1 (0.85 éxito, 0.0 mock)
    "source": str,  # "groq"|"hf"|"gemini"|"mock"
    "ts": int,  # now_ms()
}


# WhiteboardState.PercepcionVista (extiende #72/#73)
class PercepcionVista:
    detecciones: list[Box] | None  # TTL 0.2 s (10 Hz)
    gesto: GestoReconocido | None  # TTL 0.5 s (10 Hz)
    postura: Postura | None  # TTL 1.0 s (5 Hz) — #72
    profundidad: ProfundidadFrame | None  # TTL 1.0 s (5 Hz) — #73
    leyenda: LeyendaEscena | None  # TTL 2.0 s (1 Hz) — NUEVO
    identidades: ...  # ya existe
```

- **Trigger 1Hz:** `if frame_id % 30 == 0 and not pending_vlm: pending_vlm=True; asyncio.create_task(run_vlm(jpeg_b64, frame_id, boxes))` donde `run_vlm` hace cadena Groq→HF→Gemini→mock con `asyncio.to_thread` + `httpx` timeout 3s, `retry-after` honor, y `pending_vlm=False` en `finally`.
- **Frontend `percepcion-panel`:** `client.onSceneCaption = (payload)=> { leyendaEl.textContent = payload.caption; objectsEl.textContent = payload.objects.join(", "); }` + mock si `source=="mock"` muestra `"Escena no disponible — configurá GROQ_API_KEY"`.
- **Compat LeakyQueue/`MAX_FPS`/`bufferedAmount`:** VLM no encola frames, no añade JPEG, no presiona WS. `frontend/ws-client.js` sigue throttled 10 FPS; servidor decide cadencia VLM 1Hz.

#### Infra

- **Env:** `GROQ_API_KEY` (requerido), `GROQ_VISION_MODEL=meta-llama/llama-4-scout-17b-16e-instruct` (default, override a `llama-4-maverick-17b-128e-instruct` si 2026-07-17 shutdown), `OPENAI_BASE_URL=https://api.groq.com/openai/v1`, `HF_TOKEN` (opcional secundario), `OPENAI_BASE_URL_FALLBACK=https://router.huggingface.co/v1`, `HF_VISION_MODEL=Qwen/Qwen2.5-VL-3B-Instruct`, `GOOGLE_API_KEY` + `GEMINI_MODEL=gemini-2.0-flash` (opcional terciario), `VLM_ENABLED=true`.
- **Factory:** `plataforma/webcam/backend/inference/vlm.py` (nuevo módulo, no mezclar con `yolo.py`/`gesture.py`) con `async def caption_frame(jpeg_b64: str, frame_id: int, boxes: list[Box]) -> LeyendaEscena` que implementa cadena y `OPENAI_BASE_URL` override por intento (ver §3). Tests headless: `jpeg_b64 = base64.b64encode(cv2.imencode(".jpg", np.zeros((480,640,3),uint8))[1]).decode()` → mock caption si sin keys.
- **Tests:** `plataforma/webcam/tests/test_vlm.py` — `caption_frame` con keys ausentes → `source=="mock"`, `caption` es-AR no vacío, `objects` subset whitelist; `429` simulado vía `monkeypatch` `openai.RateLimitError` → fallback HF; `leaky-skip` `frame_id % 30` unit.
- **Coexistencia YOLO+Pose+Depth+VLM:** VLM HTTP no compite `intra_op_num_threads=2` (no ONNX). YOLO/pose/depth ORT en `to_thread` pool, VLM en `httpx` async — GIL liberado.

#### Presupuesto actualizado (extiende #72 pro + #73 prof)

| Canal | Frecuencia | Latencia p50 | TTL Whiteboard | Glass-to-Glass | Serialización |
|---|---|---|---|---|---|
| `detecciones` YOLO11n | 10 Hz | 73.8 ms | 0.2 s | 108 ms con gesto | `boxes` [0,1] |
| `gesto` Hand | 10 Hz | ~20 ms | 0.5 s | piggyback | `label`+`conf` |
| `postura` YOLO11n-pose | 5 Hz | 92.7 ms | 1.0 s | canal lento | `keypoints` 17×3 |
| `profundidad` MiDaS small 256 | 5 Hz | 42 ms | 1.0 s | canal lento | `profundidades` por bbox |
| **`scene_caption` Groq Scout** | **1 Hz** | **380-550 ms** | **2.0 s** | **canal lento** | **`caption` es-AR 1 frase + `objects`** |
| `scene_caption` HF Qwen 3B (alt) | 1 Hz | 600-1100 ms | 2.0 s | canal lento | igual |
| `scene_caption` Gemini (alt) | 1 Hz | 300-500 ms | 2.0 s | canal lento | igual |

*Lazo cerrado <200 ms solo usa `detecciones`+`gesto`+`ReID` — pose, depth y VLM no lo bloquean (piggyback `to_thread` / `async task` 1Hz).*

## Fuentes primarias

- **Groq deprecations (oficial):** `console.groq.com/docs/deprecations` — `2025-04-14 Multiple Model Deprecations` tabla (`llama-3.2-11b-vision-preview` → `llama-4-scout`, shutdown 04/14/25) y `2026-07-17` (`llama-4-scout` → `gpt-oss-120b`/`qwen3.6-27b`) — verificado 2026-08-24.
- **Groq rate-limits (oficial):** `console.groq.com/docs/rate-limits` — Scout Free 30/1K/30K/500K org-level, headers `retry-after`, `x-ratelimit-*`, `TPM` highest — verificado.
- **Groq model Scout (oficial):** `console.groq.com/docs/model/meta-llama/llama-4-scout-17b-16e-instruct` — MoE 17B/109B 16 experts early fusion, ≤5 imágenes, 128K, steerable system — verificado.
- **Groq pricing (oficial + agregadores):** `groq.com/pricing` / `apicents.com/provider/groq` / `modelpricewatch.com` — Scout $0.11 in / $0.34 out, blended $0.168, Maverick $0.50/$0.77 — verificado.
- **Groq OpenAI-compat:** `console.groq.com/docs/openai-compat` — `https://api.groq.com/openai/v1` con `OpenAI` SDK — verificado vía `ha-llmvision#407` logs.
- **HF Router (oficial):** `huggingface.co/docs/inference-providers` — `https://router.huggingface.co/v1`, `OpenAI(base_url, api_key=HF_TOKEN)`, `:fastest/:cheapest/:provider` suffix, `inferenceProviderMapping` — verificado.
- **HF Router pricing (oficial):** `huggingface.co/docs/inference-providers/pricing` — Free $0.10/mes, PRO $2, pass-through sin markup, `hf-inference` CPU — verificado.
- **HF Router Qwen:** `huggingface.co/Qwen/Qwen2.5-VL-3B-Instruct` — 3B 64K, `min_pixels`/`max_pixels`, `qwen-vl-utils`, Vision `image-text-to-text` — verificado.
- **HF Router outage:** `github.com/huggingface/huggingface_hub#3688` — 500 vision intermitente si single provider (Hyperbolic) — verificado.
- **Gemini pricing (oficial):** `ai.google.dev/gemini-api/docs/pricing` — 2.0 Flash $0.10 in / $0.40 out, free 15 RPM / 1500 RPD / 1M TPM, `gemini-2.0-flash` — verificado.
- **Repo local:** `plataforma/webcam/backend/app.py:67` cadena Groq→HF→Gemini→mock + `OPENAI_BASE_URL` override (`l.108-125`), `fase-1/gemini_client.py:15` `MODELO_DEFECTO/MODELO_GEMINI_LEGACY`, `:21` `_es_muse_spark`, `:70` `crear_cliente_openai`, `plataforma/webcam/backend/ws.py:40` `EnvelopeType`, `:129` `LeakyQueue N=1`, `:321` `process_single_frame`, `frontend/ws-client.js:22` `MAX_FPS 10` + `bufferedAmount>64KB` — verificado.
- **Benchmark viva:** `github.com/issamkrb/echomind#33` — Scout `~400 ms e2e` vs OpenRouter `~20s` nemotron, `GROQ_VISION_MODEL` env — verificado.

---
*Research AFK — no cierra issue #74. Context pointer: rama `research/074-vlm-leyenda`, archivo `docs/agents/research/074-vlm-leyenda.md`. Siguiente: grilling de contrato `scene_caption` Envelope/Whiteboard (mapa #71 D2/D3) y ticket task `inference/vlm.py` + `ws.py` 1Hz `asyncio.create_task` + `OPENAI_BASE_URL` override por request.*
