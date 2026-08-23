# 018 -- Repos GitHub con LLM gratuito (Research)

Ticket 018 - Parent 003-map-llm-gratuito.md - 2026-08-23

## Resumen

- ollama/ollama 179k MIT - localhost:11434/v1 - qwen2.5:1.5b - fallback local sin internet
- BerriAI/litellm 57k MIT - gateway 100+ LLMs - Router fallbacks
- open-webui/open-webui 150k BSD-3 - multi-provider simultaneo
- danny-avila/LibreChat 42k MIT - custom endpoints
- huggingface/chat-ui 10.9k Apache-2.0 - HF Router https://router.huggingface.co/v1

Patron recomendado: chat-ui + ollama sin litellm. Solo cambio OPENAI_BASE_URL.
Leccion para fase-1/gemini_client.py:60 y app.py:57 ya OpenAI-compatible.

Ver tickets 018 para tabla completa.
