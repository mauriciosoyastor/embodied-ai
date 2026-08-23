# 019 -- Comparativa free-tier hospedado (Research)

Ticket 019 - Parent 003-map-llm-gratuito.md - 2026-08-23

## Ranking 0-tarjeta + permanente + voz <500ms

| Proveedor | Base URL | Cuota | Tarjeta | Latencia |
|-----------|----------|-------|---------|----------|
| Groq | https://api.groq.com/openai/v1 | 30 RPM / 1K-14.4K RPD / 6-8K TPM | No | Si <500ms LPU |
| HF Router | https://router.huggingface.co/v1 | $0.10/mes few-hundred/h | No | Condicional |
| OpenRouter free | https://openrouter.ai/api/v1 | 20 RPM / 50->1000 RPD | No | Parcial |
| Google Gemini 2.0-flash | generativelanguage.googleapis.com | 15 RPM / 1500 RPD / 1M TPM | No | Borde |
| Together AI | https://api.together.xyz/v1 | Requiere $5 prepago | Si | Si |
| Cerebras | https://api.cerebras.ai/v1 | Trial $5 expira 30d | Si | Si |

Primario: Groq openai/gpt-oss-20b (actual, llama deprecado)
Secundario: HF Router Llama-3.2-3B
Terciario: OpenRouter free
Google no OpenAI-compatible (usa genai.Client)
Together/Cerebras descartados por tarjeta.

Fuentes: console.groq.com/docs/rate-limits, huggingface.co/docs/inference-providers/pricing, openrouter.ai/docs/api_reference/limits
