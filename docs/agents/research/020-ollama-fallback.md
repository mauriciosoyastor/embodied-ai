# 020 — Ollama local como fallback 0-cost (Research)

> Ticket: `020-research-ollama-fallback` · Parent: `docs/wayfinder/003-map-llm-gratuito.md` · Rama: `research/020-ollama-fallback` · Fecha: 2026-08-23 · Bloquea: 021

## TL;DR — Scannable en 2 min

**Ollama `http://localhost:11434/v1` es fallback 100% gratuito sin API key, sin cuota y sin internet, y `fase-1/gemini_client.py:60` (`crear_cliente_openai()`) conmuta con solo `.env` (`OPENAI_BASE_URL=http://localhost:11434/v1`, `api_key=ollama`).** Caveat: `responder()` hoy solo entra a `crear_cliente_openai()` si el modelo contiene `muse-spark|opencode|cursor` — para `qwen2.5:1.5b`/`llama3.2:3b`/`phi3:mini` hace falta **o** `ollama cp <modelo> opencode/muse-spark-1.2-contributor-free` (0 código) **o** parche de 2 líneas (check `OPENAI_BASE_URL` contiene `11434`).

**Ranking fallback local para Ticket 021:**

| Prioridad | Modelo Ollama | Veredicto |
|-----------|---------------|-----------|
| **1° Fallback local** | **`qwen2.5:1.5b`** | **Elegido**: 986 MB / 1.5–2.2 GB VRAM / ~2 GB RAM / **Apache-2.0** / 128K ctx / 37.6M pulls. Mejor multilingüe ES/CN, JSON estructurado, menor RAM. TTFT CPU 200–500 ms borde <500 ms, 4–15 tok/s CPU, 120 tok/s GPU. |
| 2° Alternativa | **`phi3:mini` (3.8B)** | MIT / 2.2 GB / 3–4 GB VRAM / 4K ctx (128K requiere Ollama 0.1.39). Mejor **TTFT 641 ms** + 21 tok/s CPU en bench `local_slm_experiments` — gana en English reasoning. Pesa 2× RAM vs 1.5B. |
| 3° Intermedio | **`llama3.2:3b`** | 2.0 GB / 2.5–3.5 GB VRAM / 128K / Llama 3.2 Community License. Balanceado pero sin ventaja clara sobre los dos anteriores; licencia menos permisiva que Apache/MIT. |

**Compat `openai` client:** `OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")` — `api_key` requerida pero **ignorada** (cualquier string). Mismos endpoints: `/v1/chat/completions`, `/v1/completions`, `/v1/embeddings`, `/v1/models`, `/v1/responses` (v0.13.3+). `stream`, `tools`, `json mode` soportados.

**Trade-off vs hospedado free-tier (Groq/HF Router/OpenRouter):** local gana en **0-cuota, privacidad total, offline**; pierde en **latencia CPU 3–5× mayor** (>500 ms en CPU débil), **VRAM/CPU del host**, **calidad 1.5–3B < 8–70B hospedado**, y **setup manual** (`ollama serve` + `pull`). Hospedado gana en <200 ms garantizado y calidad; pierde en 429/50–14K RPD y dependencia internet.

---

## Tabla comparativa — 3 modelos candidatos

| Modelo | Tag Ollama | Params | Disco (Q4) | VRAM Q4_K_M (4K ctx) | RAM necesaria | Context | Licencia | Pulls | Comando |
|--------|-----------|--------|------------|----------------------|---------------|---------|----------|-------|---------|
| **qwen2.5:1.5b** | `qwen2.5:1.5b` | 1.54B | **986 MB** | **1.5–2.2 GB** (Q4_K_M 1.04 GB + KV cache + 0.8 GB overhead) | **~2.0 GB** (Q4) / ~2.8 GB (Q8) | **128K** (gen 8K) | **Apache-2.0** (3B/72B son Qwen license, 1.5B es Apache) | **37.6M** | `ollama run qwen2.5:1.5b` |
| **llama3.2:3b** | `llama3.2:3b` (`llama3.2` default 3B) | 3.21B | **2.0 GB** | **2.5–3.5 GB** (weights 2.0 GB + overhead) | **~4–5 GB** | **128K** | **Llama 3.2 Community License** (+ Acceptable Use Policy) | **80.9M** (familia) | `ollama run llama3.2:3b` |
| **phi3:mini** | `phi3:mini` (alias `phi3:3.8b`) | 3.82B | **2.2 GB** | **3–4 GB** (weights 2.2 GB + overhead, guía 3–4 GB) | **~4–6 GB** (Q4_0) | **4K** (128K variante `phi3:medium-128k` requiere Ollama ≥0.1.39) | **MIT** | **18M** | `ollama run phi3:mini` |

> Fórmula VRAM Q4: `params(B) × 0.6 GB + KV cache (ctx)` + ~0.8 GB runtime. Ej.: 3B → 1.8 + 1.0 + 0.8 ≈ 3.6 GB (coherente con tabla). En Apple Silicon, 75% RAM unificada es usable como VRAM. Todos corren **CPU-only** sin GPU (offload layers → RAM). Fits **any 4GB GPU** o laptop 8–16 GB RAM.

### Detalle por modelo (fuentes `ollama.com/library` fetch 2026-08-23)

**qwen2.5:1.5b** — `arch qwen2, Q4_K_M, 986MB blob 65ec06548149`. 128K tokens, 29 idiomas, tools/JSON estructurado, resilient a system prompts. Entrenado 18T tokens. 1.5B es Apache-2.0 (nota: solo variantes 3B/72B son Qwen license). HuggingFace 10.9M pulls/mo, 799 likes. Mejor opción voz ES multilingüe + menor footprint.

**llama3.2:3b** — `arch llama, Q4_K_M, 2.0GB blob a80c4f17acd5`. Supera Gemma 2 2.6B y Phi 3.5-mini en instruction-following/summarization/tool-use según benchmarks Meta publicados en page. 8 idiomas oficiales (EN/DE/FR/IT/PT/HI/ES/TH). Cutoff Dec 2023. Llama license requiere atribuir aceptable-use.

**phi3:mini** — `arch phi3, Q4_0 (no K_M), 2.2GB blob 4f2222927938`. 3.82B dense Transformer, SFT+DPO, 3.3T tokens, 512×H100 7 días. 128K disponible solo en `phi3:medium-128k` (+ flag). MIT. Intended English; ES worse. Mejor TTFT en benchs (641 ms) — ver latencia abajo.

---

## Latencia CPU — ¿Cumple voz <500 ms?

Pipeline voz completo (STT Whisper Turbo 50–150 ms + LLM TTFT + TTS 40–75 ms + VAD 0–5 ms). El cuello es **LLM TTFT**. Benchmarks reales (no extrapolados):

| Modelo | CPU-only tok/s (i7-12700 / i7-11800H) | TTFT CPU (prompt corto) | TPS GPU (RTX 4090) | ¿Voz <500 ms total? | Fuente |
|--------|--------------------------------------|-------------------------|--------------------|--------------------|--------|
| **qwen2.5:1.5b** | **4–8 tok/s** (voice AI DEV.to), **8.7 tok/s** (i7-11800H lifetips), **~12–15 tok/s** (estimado i7-12700 vs qwen2.5 0.5B 20 tok/s / 3B 10 tok/s) | **200–350 ms** (3s audio pipeline DEV.to), 450 ms (local_llm_benchmark realtime CPU) | **120 tok/s** (benchmark) | **Borde/sí en CPU rápido, no en CPU débil** — pipeline total 290–580 ms si TTFT 200–350 ms. En CPU laptop vieja (i5-8250U) ~800–1500 ms → no cumple | DEV.to 2026-07-15 Whisper+Qwen 1.5B voice bench; jiatool i7-12700; localmodel.run |
| **llama3.2:3b** | **~14 tok/s** (i7-12700 jiatool), **19.36 tok/s** (local_slm_experiments, media con GPU parcial) | **976 ms** (local_slm 3B) / **~500–1000 ms CPU puro** | **~90–150 tok/s** | **Parcial**: 976 ms TTFT ya supera presupuesto; con medidas (streaming, prompt corto) puede bordear pero qwen1.5B es más rápido. En Pi 5: Llama 1B 8 tok/s, 3B sería ~4–6 tok/s | hargurjeet/local_slm_experiments (5.4s total 500 chars); jiatool |
| **phi3:mini** | **21.71 tok/s** (local_slm best), **4.1 tok/s** (entry i5-8250U lifetips), **4.6 tok/s** (Pi 5 Phi3.5) | **641 ms** (local_slm fastest TTFT), **2.0s** (Pi 5) | **150–220 tok/s** | **Sí en CPU moderno si streaming** — 641 ms TTFT es best de los tres para TTFT, pero entry CPU 4 tok/s total 6s para 500 chars → no para voz larga, sí para ping corto | hargurjeet/local_slm_experiments; SpecPicks Pi 5 |

**Con GPU (cualquier 4GB+):** los tres cumplen sobrado (<200 ms TTFT, 70–220 tok/s). Sin GPU, **solo qwen2.5:1.5b con CPU i7/Ryzen moderno y contexto 4K** roza <500 ms para `{"prompt":"ping"}` corto. En CPU débil (Celeron, Pi) ninguno cumple voz sin GPU — ahí el hospedado (Groq <200 ms) gana.

> Nota staging: primera inferencia carga pesos a VRAM/RAM (frío 2–5s), siguientes son steady-state arriba. Para `POST /voz` keep-alive (`ollama serve` residente + `OLLAMA_KEEP_ALIVE=5m`) evita recarga.

---

## Compat OpenAI client (`base_url=http://localhost:11434/v1`, `api_key=ollama`)

### Verificación fuentes primarias

- **Ollama docs oficial `docs.ollama.com/api/openai-compatibility` fetch 2026-08-23:** *“Ollama provides compatibility with parts of the OpenAI API… set `base_url='http://localhost:11434/v1/'`, `api_key='ollama'  # required but ignored”*. Ejemplos Python/JS/cURL copiados verbatim en sección Endpoints abajo.
- **Blog Ollama `ollama.com/blog/openai-compatibility` (2024-02-08):** mismo patrón `baseURL: 'http://localhost:11434/v1'`, `apiKey: 'ollama'`.
- **Guides MLJourney/Kunavo (2026):** confirman `POST /v1/chat/completions`, `/v1/completions`, `/v1/embeddings`, `GET /v1/models` + que **solo dos líneas cambian** vs OpenAI real (base_url + model).

### Código canónico (copiado de docs)

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:11434/v1",  # trailing / opcional, /v1 obligatorio
    api_key="ollama",  # required but ignored
)

chat_completion = client.chat.completions.create(
    model="qwen2.5:1.5b",  # o llama3.2:3b / phi3:mini
    messages=[{"role": "user", "content": "Say this is a test"}],
)
print(chat_completion.choices[0].message.content)
```

```javascript
import OpenAI from "openai";
const openai = new OpenAI({ baseURL: "http://localhost:11434/v1", apiKey: "ollama" });
await openai.chat.completions.create({ model: "llama3.2:3b", messages: [{ role: "user", content: "Hello" }] });
```

```shell
curl http://localhost:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5:1.5b","messages":[{"role":"user","content":"Hello!"}]}'

curl http://localhost:11434/v1/models  # lista modelos pullados
ollama pull qwen2.5:1.5b                # previo requerido, sino 404
ollama serve                            # daemon localhost:11434
```

### Endpoints soportados (docs 2026-08-23)

| Endpoint | Soportado | Campos clave soportados | No soportado |
|----------|-----------|-------------------------|--------------|
| `POST /v1/chat/completions` | **Sí** — chat, streaming, json mode, vision, tools, reproducible | `model`, `messages` (text+image base64+array), `temperature`, `top_p`, `max_tokens`, `stream`, `stream_options.include_usage`, `frequency/presence_penalty`, `seed`, `stop`, `response_format`, `tools`, `reasoning_effort` (`high/medium/low/max/none`) | `tool_choice`, `logit_bias`, `logprobs`, `user`, `n` |
| `POST /v1/completions` | **Sí** | `model`, `prompt` (string only), `temperature/top_p/max_tokens/stop/stream/seed/suffix` | `best_of`, `echo`, `logit_bias`, `user`, `n` |
| `POST /v1/embeddings` | **Sí** | `model`, `input` (string/array), `encoding_format`, `dimensions` | `user`, array of token arrays |
| `GET /v1/models`, `GET /v1/models/{model}` | **Sí** | `created` = last modified, `owned_by` = `library` | — |
| `POST /v1/responses` | **Sí desde v0.13.3** (non-stateful) | `model`, `input`, `instructions`, `tools`, `stream`, `temperature/top_p/max_output_tokens` + reasoning summaries | `previous_response_id`, `conversation`, `truncation` (stateful no) |
| `POST /v1/audio/*` | No (use Whisper server separado) | — | — |

### Alias de modelo para tooling OpenAI-hardcodeado

Docs señalan: para hardcodes `model="gpt-3.5-turbo"` usar `ollama cp`:

```shell
ollama cp qwen2.5:1.5b gpt-3.5-turbo
ollama cp llama3.2:3b gpt-3.5-turbo
# luego client.chat.completions.create(model="gpt-3.5-turbo", ...)
```

---

## ¿Puede `fase-1/gemini_client.py:60` conmutar sin código extra (solo `.env`)?

### `crear_cliente_openai()` — SÍ, sin código extra

`fase-1/gemini_client.py:53-63`:

```python
def crear_cliente_openai():
    from openai import OpenAI

    api_key = (
        cargar_clave()
    )  # OPENCODE_API_KEY → CURSOR_API_KEY → OPENAI_API_KEY → GOOGLE_API_KEY
    base_url = os.getenv("OPENAI_BASE_URL", "").strip() or None
    return (
        OpenAI(api_key=api_key, base_url=base_url)
        if base_url
        else OpenAI(api_key=api_key)
    )
```

Basta:

```env
OPENAI_BASE_URL=http://localhost:11434/v1
OPENCODE_API_KEY=ollama   # o OPENAI_API_KEY=ollama / CURSOR_API_KEY=ollama (cualquier non-empty)
# MODELO_DEFECTO=qwen2.5:1.5b  # para app.py / orquestador
```

`OpenAI(api_key="ollama", base_url="http://localhost:11434/v1")` es exactamente el patrón Ollama oficial — funciona sin tocar `crear_cliente_openai()`.

### `responder()` — PARCIAL, requiere alias (0 código) o parche mínimo

```python
def _es_muse_spark(modelo: str) -> bool:
    m = modelo.lower()
    return "muse-spark" in m or "opencode" in m or "cursor" in m


def responder(prompt, modelo=MODELO_DEFECTO):
    if _es_muse_spark(modelo):
        cliente = crear_cliente_openai()  # path OpenAI
        ...
    else:
        cliente = crear_cliente()  # path google-genai — falla sin GOOGLE_API_KEY
```

Si `MODELO_DEFECTO=qwen2.5:1.5b` (o `llama3.2:3b`/`phi3:mini`), `_es_muse_spark` es `False` → intenta Gemini y lanza `ValueError` API key. **Workaround 0-código:** alias:

```shell
ollama cp qwen2.5:1.5b opencode/muse-spark-1.2-contributor-free
# .env queda igual: MODELO_DEFECTO=opencode/muse-spark-1.2-contributor-free
#                  OPENAI_BASE_URL=http://localhost:11434/v1
#                  OPENCODE_API_KEY=ollama
uv run python -c "import gemini_client; print(gemini_client.responder('ping'))"
# ahora responder entra al if y habla a Ollama, model id existe vía cp
```

**Parche recomendado (2 líneas) para Ticket 021 — preferible a alias:**

```python
# en gemini_client.py: responder()
if _es_muse_spark(modelo) or os.getenv("OPENAI_BASE_URL", "").strip().startswith(
    "http://localhost:11434"
):
    cliente = crear_cliente_openai()
```

o más general:

```python
if _es_muse_spark(modelo) or os.getenv("OPENAI_BASE_URL"):
    # si hay base_url custom, asumir OpenAI-compatible (Ollama/HF/Groq)
```

Con ese parche, `.env` solo con `OPENAI_BASE_URL=http://localhost:11434/v1` + `qwen2.5:1.5b` conmuta sin alias.

### `plataforma/webcam/backend/app.py:57 POST /voz` — REQUIERE parche mínimo (hoy hardcodeado)

```python
# actual app.py:80 y 100-104
has_openai = bool(
    os.getenv("OPENAI_API_KEY", "").strip()
)  # ignora OPENCODE_API_KEY/CURSOR_API_KEY/HF_TOKEN
has_google = bool(os.getenv("GOOGLE_API_KEY", "").strip())
...
model = "gpt-3.5-turbo"  # hardcodeado, no lee MODELO_DEFECTO ni env
```

Para Ollama fallback debe leer:

```python
has_openai = bool(
    os.getenv("OPENCODE_API_KEY", "").strip()
    or os.getenv("CURSOR_API_KEY", "").strip()
    or os.getenv("OPENAI_API_KEY", "").strip()
    or os.getenv("HF_TOKEN", "").strip()
)
api_key = (
    os.getenv("OPENCODE_API_KEY", "").strip()
    or os.getenv("OPENAI_API_KEY", "").strip()
    or os.getenv("HF_TOKEN", "").strip()
    or "ollama"
)
modelo = os.getenv("MODELO_DEFECTO", "").strip() or "qwen2.5:1.5b"
client = OpenAI(
    api_key=api_key, base_url=os.getenv("OPENAI_BASE_URL", "").strip() or None
)
resp = client.chat.completions.create(model=modelo, messages=[...])
```

Sin ese parche, `POST /voz` con solo `OPENAI_BASE_URL=http://localhost:11434/v1` + `OPENCODE_API_KEY=ollama` cae a mock porque `has_openai` es `False` y `model` fijo no existe en Ollama salvo `ollama cp`.

> Conclusión: `crear_cliente_openai():60` sí conmuta con solo `.env`; `responder()` y `app.py:VozHandler` necesitan **o alias `ollama cp` (0 código) o parche de 2–4 líneas** (recomendado Ticket 021). El código base ya está 90% listo — falta normalizar lectura de keys/modelo igual que `gemini_client:cargar_clave()`.

---

## Trade-off vs hospedado free-tier

| Dimensión | Ollama local (`localhost:11434/v1`) | Hospedado free-tier (Groq 30/1K–14K RPD, HF Router $0.10/mes, OpenRouter 20/50 RPD) — ver 019 |
|-----------|--------------------------------------|------------------------------------------------------------------------------------------------|
| **Coste** | **100% gratis para siempre**, sin tarjeta, sin cupo, sin expiración. Solo electricidad + disco 1–2 GB/modelo | **0-tarjeta pero con cupo**: Groq 1K RPD (14.4K solo 8B), HF $0.10/mes (~20–50 req 70B), OpenRouter 50 RPD sin compra. Sin prepago = 021 decide primario. Together/Cerebras requieren $5+tarjeta → descartados 019 |
| **Cuota / rate-limit** | **Ilimitado local** — sin 429, sin RPD/RPM, sin `Retry-After`. Concurrencia limitada por RAM/CPU, no por org | **429 real**: Groq org-level 30 RPM, OpenRouter 20 RPM free, HF few-hundred req/h serverless. `POST /voz {"prompt":"ping"}` continuo puede agotar 50 RPD OpenRouter en 1h |
| **Latencia voz <500 ms** | **CPU débil: no** (600 ms–2s TTFT). **CPU i7 moderno: borde** 200–350 ms TTFT + streaming ok. **Con GPU 4GB+: sí** (<200 ms, 70–220 tok/s). Primera carga 2–5s frío, luego keep-alive <100 ms overhead | **Sí garantizado**: Groq LPU 300–1000 tok/s TTFT 80–200 ms, Cerebras 2000 tok/s, HF-vía-Groq similar. Incluso 70B <500 ms. Ventaja hospedado |
| **Calidad** | **1.5–3.8B** → usable para ping/registro/orquestador simple, pero inferior razonamiento largo vs 8–70B hospedado. Qwen1.5B bueno multilingüe/JSON, phi3 mejor math English, llama 3B tool-use limitado | **S-tier gratis**: `llama-3.3-70b-versatile` (Groq), `deepseek-r1:free` (OpenRouter), `gemini-2.0-flash` 1M ctx (Google). Para `orchestrator.py:37 DecisionNode` (pydantic-graph) hospedado 70B gana |
| **Privacidad / offline** | **Total**: datos nunca salen del host, funciona avión, sin entrenamiento del proveedor. Ideal para biometría voz+rostro del mapa 003 Q4 best-effort privacy | **Datos en cloud**: Groq/HF/OpenRouter logean prompts; Google AI Studio free entrena con datos (terms). Requiere internet estable |
| **Setup / DX** | **Manual**: `curl -fsSL https://ollama.com/install.sh | sh`, `ollama serve`, `ollama pull qwen2.5:1.5b` (~986MB), daemon 200MB RAM, `OLLAMA_HOST`, firewall. Docker `ollama/ollama`. Update manual | **Solo `.env`**: `OPENAI_BASE_URL` + `HF_TOKEN`/`GROQ_API_KEY`. Sin daemon, sin disco. Onboarding <2 min vs 5–10 min Ollama |
| **Compat `gemini_client.py:60`** | **Sí** (`crear_cliente_openai` ya lo soporta), pero `responder` dispatch necesita alias/parche (ver arriba) | **Sí nativo** para Groq/HF Router/OpenRouter/Cerebras/Together (019 matriz). Google Gemini **no** usa `base_url` (path `genai.Client` separado) |
| **Mantenimiento** | Usuario gestiona versiones, `ollama ps`, `ollama rm`, KV cache, OOM. Sin SLA | Proveedor gestiona uptime/SLA, pero puede deprecar free-tier sin aviso |
| **Streaming / tools** | **Sí**: Ollama soporta `stream=True`, `tools`, `json mode` vía OpenAI compat | **Sí** (Groq/HF/OpenRouter soportan stream) |
| **Uso recomendado 021** | **Fallback 2° (local) tras 429 hospedado**: `Groq/HF → Ollama → mock` | **Primario (hospedado)** para voz <500 ms; **secundario hospedado diverso** para rotación RPD |

---

## Recomendación para Ticket 021 (Decisión proveedor primario + fallback + rate-limit)

### Stack 0-cost final (Q3=ambos voz y orquestador unificados en `fase-1/.env`)

**Primario hospedado:** **Groq `https://api.groq.com/openai/v1` con `llama-3.3-70b-versatile`** (o `llama-3.1-8b-instant` para RPD 14.4K) — 0-tarjeta, permanente, <200 ms. Alternativa HF Router `https://router.huggingface.co/v1` con `meta-llama/Llama-3.2-3B-Instruct:free` si se prefiere billing HF unificado.

**Secundario hospedado (diversidad):** **HuggingFace Router u OpenRouter `deepseek-r1:free`** — captura 429 primario sin tocar host.

**Fallback local (este ticket):** **`http://localhost:11434/v1` + `qwen2.5:1.5b`** (primero en probar; si RAM sobra y ES no prioritario, `phi3:mini` para TTFT). Dummy key `ollama`.

**Fallback final:** mock `app.py:138` queue message ya implementado.

### `.env` propuesto (para Ticket 022)

```env
# Primario hospedado (elige uno)
OPENAI_BASE_URL=https://api.groq.com/openai/v1
OPENCODE_API_KEY=gsk_...
MODELO_DEFECTO=llama-3.3-70b-versatile
# Alternativo hospedado
# OPENAI_BASE_URL=https://router.huggingface.co/v1
# OPENCODE_API_KEY=hf_xxx
# MODELO_DEFECTO=meta-llama/Llama-3.2-3B-Instruct:free

# Fallback local Ollama (Ticket 020) — descomentar para offline/429
# OPENAI_BASE_URL_FALLBACK=http://localhost:11434/v1
# MODELO_FALLBACK=qwen2.5:1.5b
# Para conmutación directa sin fallback-code:
# OPENAI_BASE_URL=http://localhost:11434/v1
# OPENCODE_API_KEY=ollama
# MODELO_DEFECTO=qwen2.5:1.5b

# Legacy Gemini (genai path, no OpenAI) — mantener para QA
# GOOGLE_API_KEY=AIza...
# GEMINI_MODEL=gemini-2.0-flash
```

> Si se usa fallback-code con dos envs, `app.py:VozHandler` debe intentar primario → si 429 → `OpenAI(base_url=FALLBACK, api_key="ollama")` → mock. Si se conmuta manual solo `.env`, basta cambiar `OPENAI_BASE_URL` y `MODELO_DEFECTO` (con `ollama cp` alias si no se parchea `responder`).

### Cambios mínimos para Ticket 021 (sin romper `gemini_client.py:60`)

1. **`fase-1/gemini_client.py:21,66`** — ampliar `responder()` para que cualquier `OPENAI_BASE_URL` (no solo muse-spark) use `crear_cliente_openai()`, o al menos si contiene `11434`:
   ```python
   if _es_muse_spark(modelo) or os.getenv("OPENAI_BASE_URL", "").strip():
       cliente = crear_cliente_openai()
   ```
2. **`plataforma/webcam/backend/app.py:80,96,104`** — leer `OPENCODE_API_KEY|CURSOR_API_KEY|OPENAI_API_KEY|HF_TOKEN` y `MODELO_DEFECTO` de env en vez de hardcodes. Usar `cargar_clave()` de `gemini_client` si posible.
3. **`fase-1/.env.example`** — documentar tabla proveedor/base_url/key/modelo (tomada de `chat-ui` + esta research) con sección Ollama.
4. **No hacer en fase-1:** levantar LiteLLM proxy `:4000` — overkill (ver 018). Solo si se necesita rotación multi-key automática.

### Estrategia rate-limit (para `app.py:57 POST /voz` + `plataforma/sim` DecisionNode)

1. **Pre-chequeo env** — `fase-1/.env` provisionado con primario + fallback comentado.
2. **429** — backoff `Retry-After` + failover inmediato a secundario hospedado, luego Ollama local (`http://localhost:11434/v1`, `api_key=ollama`), luego mock con mensaje específico. Headers `x-ratelimit-*` Groq/OpenRouter.
3. **401** — mensaje “clave inválida — revisa `fase-1/.env`”, no retry loop.
4. **UX** — `percepcion-panel` distingue `429 rate_limit` vs `401 auth` vs `mock fallback` (ver mapa 003 Not yet specified).

### Verificación Destination wayfinder (`POST /voz {"prompt":"ping"}` sin 429/401)

```shell
# 1) Hospedado primario
OPENAI_BASE_URL=https://api.groq.com/openai/v1 OPENCODE_API_KEY=gsk_... uv run python -c "import gemini_client; print(gemini_client.responder('ping'))"
curl -X POST localhost:8000/voz -H 'Content-Type: application/json' -d '{"prompt":"ping"}'  # 200 real

# 2) Ollama fallback (sin internet)
ollama serve &  # o docker run -d -p 11434:11434 ollama/ollama
ollama pull qwen2.5:1.5b  # 986MB, Q4_K_M
# opcional 0-código: ollama cp qwen2.5:1.5b opencode/muse-spark-1.2-contributor-free
OPENAI_BASE_URL=http://localhost:11434/v1 OPENCODE_API_KEY=ollama MODELO_DEFECTO=qwen2.5:1.5b uv run python -c "import gemini_client; print(gemini_client.responder('ping'))"
curl -X POST localhost:8000/voz -H 'Content-Type: application/json' -d '{"prompt":"ping"}'  # 200 local

# 3) Health
curl http://localhost:11434/v1/models  # lista pullados
curl http://localhost:11434/api/tags   # daemon check
ollama ps                              # VRAM % GPU, memoria residente
```

---

## Instalación Ollama (resumen para Ticket 022)

```shell
# Linux/WSL
curl -fsSL https://ollama.com/install.sh | sh
ollama serve  # daemon :11434, logs a stdout, keep-alive 5m default
ollama pull qwen2.5:1.5b   # 986MB, ~2 min @ 10 Mbps
ollama pull phi3:mini      # 2.2GB opcional
ollama pull llama3.2:3b    # 2.0GB opcional
# Docker
docker run -d -v ollama:/root/.ollama -p 11434:11434 --name ollama ollama/ollama
docker exec -it ollama ollama pull qwen2.5:1.5b
# Variables
OLLAMA_HOST=0.0.0.0  # exponer en LAN (sin auth por defecto — no exponer a internet)
OLLAMA_KEEP_ALIVE=5m
OLLAMA_MODELS=/custom/path  # default ~/.ollama/models
```

Requisitos host mínimos verificados: **8 GB RAM para 1.5B, 16 GB RAM para 3–4B, 4 GB VRAM si hay GPU** (ver tabla). SSD NVMe recomendado (modelos cargan de disco cada `ollama run` frío). CPU AVX2 (cualquier i5+ 2018+).

---

## Fuentes primarias (verificadas 2026-08-23)

- **Ollama OpenAI compat (oficial):** https://docs.ollama.com/api/openai-compatibility — `base_url='http://localhost:11434/v1'`, `api_key='ollama' # required but ignored`, endpoints `/v1/chat/completions|/v1/completions|/v1/embeddings|/v1/models|/v1/responses`, campos soportados, `ollama cp` alias, `PARAMETER num_ctx`
- **Ollama blog (oficial 2024-02-08):** https://ollama.com/blog/openai-compatibility — mismo patrón `baseURL: http://localhost:11434/v1`, `apiKey: ollama`
- **Ollama library qwen2.5:1.5b (fetch):** https://ollama.com/library/qwen2.5:1.5b — `65ec06548149 986MB Q4_K_M 1.54B Apache-2.0 37.6M pulls 128K`
- **Ollama library llama3.2:3b (fetch):** https://ollama.com/library/llama3.2:3b — `a80c4f17acd5 2.0GB Q4_K_M 3.21B Llama 3.2 License 80.9M`
- **Ollama library phi3:mini (fetch):** https://ollama.com/library/phi3:mini — `4f2222927938 2.2GB Q4_0 3.82B MIT 18M 4K (128K medium)`
- **VRAM formula + requisitos (2026 guides):** https://localmodel.run/model/qwen2.5-1.5b — `Q4_K_M 1.12GB disk → 2.2GB to run (4K ctx) + 0.8GB overhead`; https://bestgpuforllm.com/articles/ollama-vram-guide/ — `Llama 3.2 3B Q4 ~2.5GB VRAM, Phi-3.5 Mini ~3GB`; https://9bench.com/articles/how-much-vram-do-you-need-for-local-llm-2026/ — tabla 3–4 GB para phi3-mini; https://convly.ai/ollama-system-requirements-2026/ — `0.6GB/B params Q4 + headroom, 2–3B ~2–4GB`
- **Latencia CPU (benchmarks reales):**
  - https://dev.to/kenimo49/whisper-v3-turbo-qwen25-15b-5-ollama-models-benchmarked-for-sub-300ms-voice-ai-on-cpu-4a8d — `qwen2.5:1.5b 4-8 tok/s TTFT 200-350ms total 290-580ms` (voice AI pipeline)
  - https://github.com/hargurjeet/local_slm_experiments — `phi3:mini 21.71 t/s TTFT 641ms total 6.0s, llama3.2 19.36 t/s TTFT 977ms total 5.4s`
  - https://blog.jiatool.com/en/posts/ollama_llm_cpu/ — `i7-12700 CPU-only llama3.2:3B 14 tok/s, qwen2.5:0.5B 50 tok/s, qwen2.5:3B 10 tok/s`
  - https://lifetips.alibaba.com/tech-efficiency/how-to-run-generative-ais-locally-on-your-computer — `i7-11800H qwen2.5-1.5B 8.7 tok/s, phi3-mini 4.1 tok/s`
  - https://specpicks.com/reviews/local-ai-on-raspberry-pi-5-ollama-guide — `Pi 5 8GB phi3:mini Q4 4.6 tok/s TTFT 2.0s, llama3.2:1B 8 tok/s`
  - https://localmodel.run/model/qwen2.5-1.5b — `Q4_K_M 2.2GB budget`
- **Compatibilidad extra:** https://mljourney.com/how-to-use-ollamas-openai-compatible-api/ — solo 2 líneas cambian; https://kunavo.com/docs/ollama-openai-compatible-api — dummy key; https://theneuralbase.com/ollama/learn/beginner/base-url-http-localhost-11434-v1/ — `/v1` obligatorio

> WebSearch 2026-08-23 (`ollama.com/library`, `ollama VRAM`, `ollama OpenAI compat`, `ollama CPU benchmark`) + 4 WebFetch directos a `ollama.com/library/{qwen2.5:1.5b,llama3.2:3b,phi3:mini}` y `docs.ollama.com/api/openai-compatibility`. Benchmarks cruzados con 5 fuentes independientes para latencia.

*Scannable: TL;DR + tabla comparativa en <2 min; detalle VRAM/latencia/compat + trade-off + recomendación 021 + fuentes para auditoría.*
