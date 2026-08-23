# Ticket 019 — Research: Comparativa free-tier hospedado OpenAI-compatible

> Label: `wayfinder:research` · Parent: `003-map-llm-gratuito.md` · Estado: cerrado · Resolución: 2026-08-23 · Frontera · AFK

## Resolución

- Rama `research/019-free-tier-comparativa` — `docs/agents/research/019-free-tier-comparativa.md`
- **Groq** `api.groq.com/openai/v1` 30 RPM / 14.4K RPD (8b) / 1K RPD (70b) 6-8K TPM, sin tarjeta, permanente, <500ms LPU — **primario recomendado**
- **HF Router** `router.huggingface.co/v1` $0.10/mes few-hundred/h, sin tarjeta, mensual renovable — secundario
- **OpenRouter :free** `openrouter.ai/api/v1` 20 RPM / 50→1000 RPD con $10, sin tarjeta, cola free — terciario
- **Google Gemini 2.0-flash** `generativelanguage.googleapis.com` 15 RPM/1500 RPD/1M TPM, sin tarjeta pero no OpenAI-compatible (usa `genai.Client`)
- **Together/Cerebras** requieren tarjeta/$5 y expiran 30d — descartados para 0-cost
- Fuentes primarias `console.groq.com/docs/rate-limits`, `huggingface.co/docs/inference-providers/pricing`, `openrouter.ai/docs/api_reference/limits`, `inference-docs.cerebras.ai/support/rate-limits`

## Question

Comparar Groq, HuggingFace Inference (serverless), OpenRouter free, Together free, Google AI Studio (Gemini 2.0-flash), Cerebras free: cuota (req/día, TPM, RPM), modelos OpenAI-compatible, necesidad de `OPENAI_BASE_URL`, expiración y latencia para voz `<500ms`. ¿Cuál cubre `opencode/muse-spark-1.2-contributor-free` o equivalente sin tarjeta?
