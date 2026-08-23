# Ticket 018 — Research: Repos GitHub con LLM gratuito resuelto

> Label: `wayfinder:research` · Parent: `003-map-llm-gratuito.md` · Estado: cerrado · Resolución: 2026-08-23 · Reclamado por subagente research · Frontera · AFK

## Resolución

- Rama `research/018-repos-llm-gratuito` — `docs/agents/research/018-repos-llm-gratuito.md` (14 KB)
- 5 repos ≥1k stars: **ollama/ollama** 179k MIT `localhost:11434/v1`, **open-webui** 150k BSD-3 multi-provider, **BerriAI/litellm** 57k MIT gateway, **danny-avila/LibreChat** 42k MIT custom endpoints, **huggingface/chat-ui** 10.9k Apache-2.0 HF Router `https://router.huggingface.co/v1`
- Patrón recomendado: `chat-ui` + `ollama` — sin LiteLLM, solo cambio `OPENAI_BASE_URL`; lección para `fase-1/gemini_client.py:60` y `app.py:57` ya OpenAI-compatible

## Question

¿Qué repos GitHub (open-source) ya resolvieron LLM 0-coste operativo para voz/orquestador con free-tier hospedado o local (Ollama/LM Studio) y qué patrón usan (OpenAI-compatible proxy, fallback, keys)? Evaluar 3-5 repos relevantes con estrellas/licencia/último commit y extraer stack, `OPENAI_BASE_URL`, modelo y lecciones aplicables a `fase-1/gemini_client.py` y `plataforma/webcam/backend/app.py:57 POST /voz`.
