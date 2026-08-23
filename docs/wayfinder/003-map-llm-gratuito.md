# Wayfinder Map — LLM Gratuito Operativo (Voz + Orquestador)

> Label: `wayfinder:map` · Estado: cerrado — way completo · Tracker: local-markdown · Creado: 2026-08-23 · Cerrado: 2026-08-23

## Destination

**Decisión cerrada** sobre stack LLM **0-coste** operativo para `fase-1/gemini_client.py` + `plataforma/webcam/backend/app.py:57 POST /voz` + `fase-1/orchestrator.py:37` (`openai:opencode/muse-spark-1.2-contributor-free`) y `plataforma/sim` DecisionNode, con `fase-1/.env` provisionado y `POST /voz {"prompt":"ping"}` respondiendo sin `429/401` en `localhost:8000`. Evalúa repos GitHub que ya resolvieron LLM gratuito hospedado. Cierra cuando la decisión de proveedor primario + fallback + `OPENAI_BASE_URL`/keys está documentada y verificada.

## Notes

- Dominio: Embodied AI platform · `fase-1` + `plataforma/webcam` (FastAPI+Vite) + `plataforma/sim` (pydantic-graph)
- Skills a consultar por sesión: `grilling`, `domain-modeling`, `research`, `prototype`
- Preferencias fijas: **Q1=A Decisión** (no spec ni migración), **Q2=hospedado free-tier + fallback local documentado**, **Q3=ambos** (voz y orquestador unificados en `fase-1/.env`), **Q4=sin privacidad estricta**, latencia best-effort. Re-evaluar repos open-source con solución gratuita.
- Estado actual verificado: `yolo11n.onnx` + `hand_landmarker.task` `is_stub=False`, `vite.config.js:9` y `ws-client.js:27` ya alineados a `:8000`, `GEMINI_MODEL=gemini-2.0-flash` corregido, `GOOGLE_API_KEY=AQ...` inválida `400 API_KEY_INVALID`, `OPENAI_API_KEY` `429 credit_balance_exhausted`, `OPENCODE_API_KEY=sk-hb8...` sin `OPENAI_BASE_URL` → `401` en `api.openai.com`.

## Decisions so far

- [Research: Repos GitHub con LLM gratuito resuelto — Ticket 018](tickets/018-research-repos-llm-gratuito.md) — 5 repos ≥1k stars (ollama 179k, open-webui 150k, litellm 57k, LibreChat 42k, chat-ui 10.9k); patrón recomendado `chat-ui` + `ollama` `localhost:11434/v1` (2026-08-23)
- [Research: Comparativa free-tier hospedado — Ticket 019](tickets/019-research-free-tier-comparativa.md) — Groq 14.4K RPD sin tarjeta <500ms, HF Router $0.10/mes, OpenRouter 50→1000 RPD, Google no-OpenAI, Together/Cerebras requieren tarjeta (2026-08-23)
- [Research: Ollama local como fallback — Ticket 020](tickets/020-research-ollama-fallback.md) — `qwen2.5:1.5b` 986MB/2GB TTFT 200-350ms, `api_key=ollama`, conmuta sin código vía `OPENAI_BASE_URL` (2026-08-23)
- [Grilling: Decisión proveedor primario + fallback — Ticket 021](tickets/021-grilling-proveedor-primario-fallback.md) — Groq `llama-3.1-8b-instant` → migrado a `openai/gpt-oss-20b` (llama deprecado) primario, HF Router `Llama-3.2-3B` secundario, Ollama `qwen2.5:1.5b` fallback, cadena `Groq→HF→Ollama→mock` con `401` corta/`429` retry-after (2026-08-23)
- [Task: Provisionar credenciales — Ticket 022](tickets/022-task-provisionar-credenciales.md) — `GROQ_API_KEY=gsk_l728...` + `openai/gpt-oss-20b` operativo, `POST /voz` real sin mock, `gemini_client` + `app.py` parcheados (2026-08-23) — **mapa sin frontera**

## Not yet specified

- Streaming TTS por chunks vs respuesta completa si el proveedor lo soporta
- Cuota exacta y renovación de cada free-tier y cómo se comunica al usuario en `percepcion-panel`
- UX de error cuando todos los proveedores gratuitos fallan (mock actual `app.py:138` vs mensaje tipado)

## Out of scope

- Wake-word/VAD continuo y grabación video persistente — ya out-of-scope en mapa 000
- Auth cloud / DB centralizada y Safety Envelope físico completo — mapas 000/001
- Entrenar/fine-tunear modelo propio — solo consumo de API o local inferencia
- Modificar `plataforma/webcam` más allá de `POST /voz` y `fase-1/.env` — es módulo base

## Tickets (frontera)

> Cada ticket es un child de este mapa. Bloqueos: `Bloquea:` = este ticket bloquea a otros.

### Ticket 018 — Research: Repos GitHub con LLM gratuito resuelto [wayfinder:research] — CERRADO 2026-08-23
**Question:** ¿Qué repos GitHub (open-source) ya resolvieron LLM 0-coste operativo para voz/orquestador con free-tier hospedado o local (Ollama/LM Studio) y qué patrón usan?
**Bloquea:** 021
**Estado:** cerrado — ver [018](tickets/018-research-repos-llm-gratuito.md)

### Ticket 019 — Research: Comparativa free-tier hospedado OpenAI-compatible [wayfinder:research] — CERRADO 2026-08-23
**Question:** Comparar Groq, HuggingFace Inference, OpenRouter free, Together free, Google AI Studio, Cerebras free: cuota, modelos, `OPENAI_BASE_URL`, expiración y latencia.
**Bloquea:** 021
**Estado:** cerrado — ver [019](tickets/019-research-free-tier-comparativa.md)

### Ticket 020 — Research: Ollama local como fallback 0-cost [wayfinder:research] — CERRADO 2026-08-23
**Question:** ¿Ollama `localhost:11434/v1` con `qwen2.5:1.5b` / `llama3.2:3b` / `phi3:mini` como fallback 100% gratuito sin API key?
**Bloquea:** 021
**Estado:** cerrado — ver [020](tickets/020-research-ollama-fallback.md)

### Ticket 021 — Grilling: Decisión proveedor primario + fallback + estrategia rate-limit [wayfinder:grilling] — CERRADO 2026-08-23
**Question:** Con 018/019/020 resueltos, ¿proveedor primario gratuito (y secundario) para `fase-1/.env`, `OPENAI_BASE_URL`, `MODELO_DEFECTO` y fallback en `app.py:96 VozHandler`?
**Bloquea:** 022
**Estado:** cerrado — ver [021](tickets/021-grilling-proveedor-primario-fallback.md) — **Decisión: Groq llama-3.1-8b-instant + HF Router + Ollama qwen2.5:1.5b**

### Ticket 022 — Task: Provisionar credenciales gratuitas y verificar flujo end-to-end [wayfinder:task] — CERRADO 2026-08-23
**Question:** Trabajo AFK/HITL: crear cuentas free-tier elegidas, generar keys, setear `fase-1/.env`, verificar `gemini_client.responder('Hola')` + `POST /voz` sin mock + orchestrator DecisionNode.
**Bloquea:** —
**Estado:** cerrado — ver [022](tickets/022-task-provisionar-credenciales.md) — `GROQ_API_KEY` + `openai/gpt-oss-20b` verificado
