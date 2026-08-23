# Ticket 020 — Research: Ollama local como fallback 0-cost

> Label: `wayfinder:research` · Parent: `003-map-llm-gratuito.md` · Estado: cerrado · Resolución: 2026-08-23 · Frontera · AFK

## Resolución

- Rama `research/020-ollama-fallback` — `docs/agents/research/020-ollama-fallback.md` (353 líneas)
- `qwen2.5:1.5b` 986MB/1.5-2.2GB VRAM ~2GB RAM 128K Apache-2.0 — fallback elegido; `llama3.2:3b` 2.0GB/4-5GB, `phi3:mini` 2.2GB/4-6GB 4K
- Latencia CPU `qwen1.5b` 4-15 tok/s TTFT 200-350ms (pipeline 290-580ms borde <500ms i7, >800ms CPU débil), GPU 70-220 tok/s <500ms
- Compat `OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")` endpoints `/v1/chat/completions|embeddings|models` oficiales; `ollama cp <modelo> gpt-3.5-turbo` alias
- `fase-1/gemini_client.py:60` conmuta sin código con `OPENAI_BASE_URL=http://localhost:11434/v1` + `OPENCODE_API_KEY=ollama` (requiere parche 2 líneas para modelos sin `muse-spark|opencode|cursor`); `app.py:80,104` similar

## Question

¿Ollama `localhost:11434/v1` con `qwen2.5:1.5b` / `llama3.2:3b` / `phi3:mini` como fallback 100% gratuito sin API key? Requisitos VRAM/RAM, latencia CPU, compat `openai` client (`base_url=http://localhost:11434/v1`, `api_key=ollama`), y si `fase-1/gemini_client.py:60` puede conmutar sin código extra (solo `.env`).
