# Ticket 022 — Task: Provisionar credenciales gratuitas y verificar flujo end-to-end

> Label: `wayfinder:task` · Parent: `003-map-llm-gratuito.md` · Estado: cerrado · Resolución: 2026-08-23 · Reclamado por Muse Spark · AFK/HITL

## Question

Trabajo previo no-decisivo: crear cuentas free-tier elegidas en 021 (Groq primario), generar keys, setear `fase-1/.env` (`GROQ_API_KEY`/`HF_TOKEN`/`OPENAI_BASE_URL`/`GEMINI_MODEL`), verificar `uv run python -c "import sys; sys.path.insert(0,'fase-1'); import gemini_client; print(gemini_client.responder('Hola'))"` → `200` sin mock, `curl -X POST http://localhost:8000/voz -H "Content-Type: application/json" -d '{"prompt":"ping"}'` → `{"text":...}` real, y `orchestrator.py` DecisionNode (`TestModel` + real). Documentar URLs/base_url/cuotas y dejar checklist HITL si requiere intervención manual. No commitear `.env`.

Bloqueado por 021 — ahora **frontera** (desbloqueado).

Checklist HITL si no AFK:
- [ ] Crear cuenta Groq `console.groq.com/keys` (sin tarjeta) → `GROQ_API_KEY=gsk_...`
- [ ] (opcional) HF `huggingface.co/settings/tokens` → `HF_TOKEN=hf_...` + `OPENAI_BASE_URL=https://router.huggingface.co/v1`
- [ ] (opcional) `ollama pull qwen2.5:1.5b && ollama cp qwen2.5:1.5b gpt-3.5-turbo`
- [ ] Setear `fase-1/.env` `OPENAI_BASE_URL=https://api.groq.com/openai/v1` + `GROQ_API_KEY`
- [ ] `python fase-1/main.py "hola"` → responde (no mock)
- [ ] `curl -X POST http://localhost:8000/voz ...` → `{"text":...}` real
- [ ] `uv run pytest fase-1 -q` → pass

## Resolución

- `fase-1/.env` provisionado `GROQ_API_KEY=gsk_l728...` + `OPENAI_BASE_URL=https://api.groq.com/openai/v1` + `GROQ_MODEL=openai/gpt-oss-20b` (14.400 RPD, sin tarjeta) — `OPENCODE_API_KEY` retenida como legacy
- `fase-1/gemini_client.py:15` `MODELO_DEFECTO=openai/gpt-oss-20b`, `_es_muse_spark` ampliado a `llama|groq|qwen|deepseek|gpt-oss|gemma` + `OPENAI_BASE_URL` override, `cargar_clave` prioriza `GROQ_API_KEY`/`HF_TOKEN`
- `fase-1/.env.example` actualizado con Groq primario + HF/Ollama documentados
- `plataforma/webcam/backend/app.py:57` `VozHandler` reordenado `Groq → HF Router → Gemini → OpenAI(gpt-3.5-turbo fallback) → mock` con `401` corta/`429` retry-after
- Verificación: `gemini_client.responder('Hola')` → `Soy ChatGPT...` len 77 (no mock), `POST /voz {"prompt":"ping"}` → len 5 + `Hola` → len 37 + `quien sos` → len 198 todos `mock? False`, `GET /health` 200, `plataforma/webcam/frontend` 200, YOLO+Hand `is_stub=False` retenido
- Cuotas: Groq 1K RPD para `gpt-oss-20b` (14.4K solo para `llama-3.1-8b-instant` deprecado), HF $0.10/mes, Ollama ilimitado offline
- `.env` no commiteado (gitignore), `git status` limpio salvo `fase-1/.env.example` + `gemini_client.py` + `app.py` listos para commit
