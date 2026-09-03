# R1 — Research: enforcement grounding en free-tier + fallback Groq-HF-Ollama-mock

> Wayfinder #130 mapa · Issue #135 · Rama `research/grounding-free-tier` (throwaway, sin push) · Fecha 2026-09-03
> Alcance: solo investigación. No toca `plataforma/`. Solo este archivo nuevo.

## TL;DR

- **No hay `system` prompt en ningún proveedor.** Todo el grounding es **prefijo `user`**: `plataforma/webcam/backend/app.py:181-193` construye `grounded_prefix` + `prompt_grounded = "{prefix}Usuario dice: {prompt}"` y lo pasa como único `messages=[{"role":"user",...}]` en Groq/HF/OpenAI (`app.py:338,357,395`, `fase-1/gemini_client.py:93-96`) o `contents=prompt` en Gemini (`gemini_client.py:105`). Enforcement = débil (el modelo puede ignorarlo).
- **Cadena real hoy: Groq → HF Router → Gemini legacy → OpenAI fallback → mock.** No hay paso Ollama explícito en `app.py:334-401`; Ollama solo funciona por `OPENAI_BASE_URL=http://localhost:11434/v1` (ver `docs/agents/research/020-ollama-fallback.md`). Gap vs spec Ticket 021 (`Groq→HF→Ollama→mock`).
- **401/429 sin manejo diferenciado.** Solo `except Exception → logger.warning → siguiente proveedor` (`app.py:341-342,366-367,379,400-401`, `vlm.py:100-101,135-136,167-168`). No hay `Retry-After`, ni corta-401, ni mensaje tipado. Gap vs 021 (`401 corta / 429 retry-after 30s`).
- **Mock grounded devuelve el prefix verbatim** (`app.py:433-435,409`), incluyendo `frame_id/age/descs` → se vocaliza por TTS y se muestra en DOM. Formato predecible, útil para tests pero leakea telemetría interna.
- **Leaks frontend confirmados en 3 puntos**: `percepcion-panel` (`main.js:86-93,258`), `overlay.js` (labels + `canvas.title`), `ws-client.js` (passthrough sin filtro + `jpeg_b64` saliente).

## 1. Cómo se construye el system prompt grounding (no es system)

Fuente primaria: `plataforma/webcam/backend/app.py:153-193` (`VozHandler`, `POST /voz`).

```python
# app.py:167-193 (resumen fiel)
from plataforma.webcam.backend.ws import last_atributos, last_frame_id, last_ts
_age = now_ms - last_ts
if last_atributos and _age < 2000:
    _descs = ", ".join([f"{cls} {color} {tamano} {hex} z:{z_rel}{' WORLD:'+prompt_origen if is_world}" for a in last_atributos[:4]])
    grounded_prefix = f"[Percepción viva frame #{last_frame_id} age {_age}ms: {_descs}] Instrucción grounding: responde SOLO sobre lo que ves. Si no ves, di 'No veo objetos ahora'. Prohibido inventar precios/Walmart. "
else:
    grounded_prefix = "[Percepción: No veo objetos ahora (frame stale >2s).] "
prompt_grounded = f"{grounded_prefix}Usuario dice: {prompt}"
```

- Fuente de verdad: globales `ws.py:62,825-827` (`last_atributos`, `last_frame_id`, `last_ts`), actualizados en fast_processor por cada frame inferido.
- Ventanas: grounding-LLM `<2000ms`, anclaje determinista S3 `<500ms` (`app.py:221`). Si `age 500-2000ms` → va a LLM con prefix pero sin atajo local. Si `>2000ms` o vacío → prefix "stale".
- Cap: solo `[:4]` atributos. Campos: `cls/color/tamano/color_hsv_hex/z_rel/is_world/prompt_origen` (`app.py:173-179`).
- Atajo S3 sin LLM (`app.py:194-282`): si `is_color_q` (color/tamaño/qué ves/izquierda/derecha/distancia) y `age<500ms` responde local: color taza/tv, `Veo N objetos...`, espacial izq/der por `centroide.x_c`. No consume cuota.
- YOLO-World dinámico (`app.py:283-312`): si `YOLO_WORLD_DYNAMIC_BY_VOZ` (`config.py:35`) y `extract_prompts_from_transcript(prompt)` no vacío → `get_yolo_world_detector(prompt_list=prompts)` + ack `"Buscando ... (YOLO-World dinámico, frame #...)"` sin LLM para comandos mira/busca/dónde.

Contrato harness: `harness/plan.voz-grounded.json` invariants exigen inyectar `last_atributos (≤500ms) con track_id/color_hsv_hex/z_rel/prompt_origen` y responder `'No veo objetos ahora (frame stale)'` sin alucinación Walmart.

## 2. System vs user prompt por proveedor

| Proveedor | Código | Modelo | `system` | `user` | Notas |
|---|---|---|---|---|---|
| Groq primario | `app.py:335-342` → `gemini_client.responder(prompt_grounded, modelo=GROQ_MODEL‖openai/gpt-oss-20b)` → `gemini_client.py:93-96` | `GROQ_MODEL` o `MODELO_DEFECTO=openai/gpt-oss-20b` (`gemini_client.py:15`) | ❌ ninguno | `prompt_grounded` completo | `crear_cliente_openai()` usa `cargar_clave()` (GROQ primero) + `OPENAI_BASE_URL` tal cual (normalmente `https://api.groq.com/openai/v1`) |
| HF Router secundario | `app.py:345-367` override temporal `OPENAI_BASE_URL=OPENAI_BASE_URL_FALLBACK‖https://router.huggingface.co/v1`, restore en `finally` | hardcode `meta-llama/Llama-3.2-3B-Instruct` (`app.py:357`) | ❌ ninguno | `prompt_grounded` completo | Mutación global `os.environ` — race si concurrencia; no usa `GROQ_MODEL` |
| Gemini legacy | `app.py:369-379` → `gemini_client.responder(prompt_grounded, modelo=GEMINI_MODEL‖gemini-2.0-flash)` → `gemini_client.py:105` | `GEMINI_MODEL` o `MODELO_GEMINI_LEGACY=gemini-2.0-flash` (`gemini_client.py:18`) | ❌ ninguno | `contents=prompt_grounded` (genai, sin rol system) | Path `genai.Client` (`gemini_client.py:63-68`), no OpenAI-compatible |
| OpenAI fallback | `app.py:381-401` `OpenAI(api_key=GROQ‖OPENAI, base_url=OPENAI_BASE_URL‖None).chat.completions.create(model=GROQ_MODEL‖gpt-3.5-turbo, messages=[{"role":"user","content":prompt_grounded}])` | `GROQ_MODEL` o `gpt-3.5-turbo` | ❌ ninguno | `prompt_grounded` completo | Solo entra si `OPENAI_API_KEY` set (ignora `OPENCODE/CURSOR/HF`); si `OPENAI_BASE_URL=localhost:11434` aquí caería Ollama implícito |
| VLM 1Hz (no /voz) | `plataforma/webcam/backend/inference/vlm.py:66-136` + `app.py:450-477 POST /vision/caption` | Groq `meta-llama/llama-4-scout-17b-16e-instruct` → HF `Qwen/Qwen2.5-VL-7B-Instruct` → Gemini | ❌ ninguno | `f"Describe en espanol AR escena con: {objs}"` `max_tokens=64` | Texto solo, `image_b64` ignorado (`vlm.py:62`); `conf` 0.85/0.75/0.70/0.5 + `provider` groq/hf/gemini/mock |
| Mock final | `app.py:403-441` | — | — | `low=prompt_grounded.lower()` pattern-match | Ver §4 |

Dispatch clave `fase-1/gemini_client.py:21-34`: `_es_muse_spark()` hoy es amplio (`muse-spark|opencode|cursor|llama|groq|qwen|deepseek|gpt-oss|gemma` o `OPENAI_BASE_URL` set) → `qwen2.5:1.5b`/`llama3.2:3b` ya entran a path OpenAI sin alias (mejora vs lo documentado en `020-ollama-fallback.md:154-170`). `cargar_clave()` orden `GROQ→HF→OPENCODE→CURSOR→OPENAI→GOOGLE` (`gemini_client.py:42-56`).

Consecuencia enforcement: al ser todo `user`, un modelo instruction-following débil puede ignorar "responde SOLO sobre lo que ves". Endurecer implicaría `role:system` separado (cambio `plataforma/`, fuera de alcance R1).

## 3. 401/429 y cadena Groq → HF → Ollama → mock

Estado real (fuentes primarias):

- `app.py:329-332`: gates `has_groq/has_google/has_openai/has_hf` por presencia de env, sin validar formato.
- Cada intento `try/except Exception → logger.warning("Groq/HF/Gemini/OpenAI ... fallo")` y cae al siguiente. **No inspecciona `status_code`, ni `Retry-After`, ni distingue 401 vs 429 vs 500** (`app.py:341,367,379,401`).
- `vlm.py:100,135,167`: mismo patrón (`except Exception: pass`).
- `gemini_client.py`: sin retry ni backoff; deja subir la excepción.
- **Ollama ausente como paso nominal** en `app.py`. Grep `ollama|11434` en `plataforma/` = 0 hits (solo docs `019/020` y specs 021/022). Reuso posible hoy: setear `OPENAI_BASE_URL=http://localhost:11434/v1` + `OPENAI_API_KEY=ollama` entra al paso 4 (OpenAI fallback), o `GROQ_API_KEY=ollama` + `GROQ_BASE_URL` equivalente en VLM. Pero pisa al primario — no es fallback secuencial.
- Spec esperada (no implementada): `docs/wayfinder/tickets/021-grilling-proveedor-primario-fallback.md:12` — `Groq→HF→Ollama→mock`, `401` corta sin reintento, `429` respeta `retry-after` o 30s, mock tipado en `percepcion-panel` (`"Groq 429, usando HF..."` / `"Sin internet, usando local"`). `022-task-provisionar-credenciales.md:25` repite `401 corta/429 retry-after`. **Ambos gaps abiertos.**

Cuotas contexto (`docs/agents/research/019-free-tier-comparativa.md:7-22`): Groq 30 RPM/1K-14.4K RPD, HF Router $0.10/mes few-hundred/h, OpenRouter 20 RPM/50-1000 RPD, Gemini 15 RPM/1500 RPD. Sin 429 explícito, una ráfaga `POST /voz ping` quema el primario y cae en cascada silenciosa hasta mock.

## 4. Formato mock grounded

Fuente: `app.py:403-441`.

```python
low = prompt_grounded.lower()
if "hola" in low:
    if grounded_prefix and "person" in grounded_prefix.lower():
        return {"text": f"¡Hola! Veo {grounded_prefix.split('Percepción viva')[1][:120] ...} (mock grounded)."}
    return {"text": "¡Hola! Soy Muse Spark 1.2 free vía OpenAI (fallback). ¿Como te registro por camara? ..."}
if "registr" in low: return {"text": "Perfecto, para registrarte mirá a la camara y hacé pulgar arriba. (fallback OpenAI)"}
if "quien" in low: return {"text": "Soy Muse Spark 1.2, orquestador cognitivo de Embodied AI. (fallback OpenAI)"}
if grounded_prefix:
    return {"text": f'{grounded_prefix} Recibí: "{prompt}" (mock grounded — sin LLM).'}
return {"text": f'Recibio: "{prompt}" (fallback OpenAI — Gemini y OpenAI no disponibles...).'}
```

- Mock con percepción devuelve **prefix + eco del prompt original** verbatim. Ejemplo real: `[Percepción viva frame #123 age 120ms: cup rojo mediano ...] Instrucción grounding: ... Recibí: "qué ves?" (mock grounded — sin LLM).`
- Incluye `frame_id`, `age_ms`, lista `cls color tamano hex z` — telemetría interna expuesta al usuario (ver §5).
- Frontend tiene su propio mock espejo (`frontend/src/voice-chat.js:131-135`) cuando `fetch /voz` falla: `"Recibí: ... (mock) Cuando el backend /voz esté listo..."`.

## 5. Dónde puede leakear al frontend

### A. percepcion-panel (`frontend/src/main.js:54-102,214-291`)

- `#p-atributos-json` (`main.js:258`): `JSON.stringify(filtered.slice(0,3), null, 2)` con objetos `AtributoVista` crudos (`track_id/cls/color/tamano/z_rel/centroide/track history`). Visible en panel + screenshot + grabación.
- `#p-atributos-list` chips (`main.js:246-254`): `#id cls color tamano z0.42` + `#p-ttl` con `age` (`main.js:251-256`).
- `#p-leyenda` (`main.js:81-85,271-291`): `caption + objects + provider` (`· mock` vs `· groq/hf`). Distingue proveedor pero también revela caídas.
- Transcript voz (`voice-chat.js:88-102,160-164`): burbujas `🧑/🤖` muestran `j.text` del backend verbatim (incluido prefix grounded) + `speak(reply)` lo **vocaliza por TTS** (`voice-chat.js:108-122`). El prefix diseñado para LLM termina leído en voz alta.
- `fetch("http://localhost:8000/voz", ...)` (`main.js:145-149`) sin auth, acepta `j.text ‖ j.reply`.

### B. overlay.js (`frontend/src/overlay.js`, `frontend/overlay.js` raíz legacy)

- Labels World (`overlay.js:258-265`): `🌐 {cls} {conf}% {color} {hex} · {prompt_origen}` + `canvas.title = "World: {prompt} · {color} {hex} · is_world"`. `prompt_origen` viene de la voz del usuario (vía `YOLO_WORLD_DYNAMIC_BY_VOZ`) → eco de input por voz en canvas visible.
- Identidades (`overlay.js:266-271`): `Hola {nombre} ✓`, `posible {nombre}?`, `? {nombre} blanco`, `⋯ {nombre} prov` con `cosine` — expone estado de enrollment + score biométrico.
- Depth badges (`overlay.js:181-195`): `z 0.42` por bbox; `canvas.title` telemetría `yolo Xms · mano Yms` (`overlay.js:378-382`); `countEl` (`overlay.js:300-303`).
- Handlers `handleDetecciones/handleSceneCaption/handleGesto/handleEstado` (`overlay.js:386-422`) no filtran; `handleSceneCaption` es no-op canvas pero `main.js:263-291` sí pinta caption en DOM.

### C. ws-client.js (`frontend/src/ws-client.js`, `frontend/ws-client.js` legacy)

- Passthrough total: `onmessage` parsea `envelope {type,seq,ts,payload}` y reenvía a `onDetecciones/onGesto/onEstado/onSceneCaption/onEnrollAck/onPurgeAck` sin sanitizar (`ws-client.js:57-71`). Contrato D5 `frame/detecciones/gesto/estado` + v2 `scene_caption`.
- Saliente: `sendFrame()` envía `jpeg_b64 + width/height + frame_id/seq/ts` (`ws-client.js:103-124`); throttling `canSend()` 10 FPS + `bufferedAmount>64KB` skip (`ws-client.js:88-94`). Sin redacción PII — frame crudo sale del browser.
- `selectTransport()` (`ws-client.js:177-201`) probe `HEAD https://<JETSON-IP>:8554/webrtc/signal` — revela topología LAN en consola/red.

Riesgo neto: bajo para demo local, medio si se expone: PII (rostro/embeddings vía enrollment), telemetría interna (frame_id/age/z_rel/scores) y prompts de voz ecoados en UI/TTS. Mitigaciones típicas (fuera de alcance R1, solo se enuncian): no devolver `grounded_prefix` verbatim en mock (devolver resumen), `role:system` separado, filtrar `prompt_origen/cosine/age` antes de pintar, no vocalizar prefix.

## 6. Archivos tocados por esta research (solo este)

- `docs/agents/research/R1-grounding-free-tier.md` (este archivo, rama `research/grounding-free-tier`, sin push).

## 7. Fuentes primarias verificadas

- `plataforma/webcam/backend/app.py:153-441` (POST /voz, grounding, cadena, mock)
- `fase-1/gemini_client.py:1-106` (dispatch, claves, OpenAI-compat)
- `plataforma/webcam/backend/inference/vlm.py:1-185` (VLM Groq→HF→Gemini→mock)
- `plataforma/webcam/backend/ws.py:62,823-827,904-954,1079-1083` (last_atributos/frame_id/ts)
- `plataforma/webcam/backend/config.py:1-93` (YOLO_WORLD_DYNAMIC_BY_VOZ, thresholds)
- `plataforma/webcam/frontend/src/main.js:54-102,135-158,214-291` (percepcion-panel)
- `plataforma/webcam/frontend/src/overlay.js` + `frontend/overlay.js` (labels World/identidades/depth)
- `plataforma/webcam/frontend/src/ws-client.js` + `frontend/ws-client.js` (envelope, throttling)
- `plataforma/webcam/frontend/src/voice-chat.js:124-136` (mock espejo, TTS)
- `harness/plan.voz-grounded.json` (invariants grounding)
- `docs/agents/research/019-free-tier-comparativa.md`, `020-ollama-fallback.md` (cuotas, Ollama `localhost:11434/v1` + `ollama cp` alias)
- `docs/wayfinder/003-map-llm-gratuito.md`, `tickets/021-grilling-proveedor-primario-fallback.md`, `tickets/022-task-provisionar-credenciales.md` (spec cadena + 401/429)
