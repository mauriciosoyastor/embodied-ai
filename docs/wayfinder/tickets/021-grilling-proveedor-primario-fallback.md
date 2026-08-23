# Ticket 021 — Grilling: Decisión proveedor primario + fallback + estrategia rate-limit

> Label: `wayfinder:grilling` · Parent: `003-map-llm-gratuito.md` · Estado: cerrado · Resolución: 2026-08-23 · Reclamado por Muse Spark · HITL

## Resolución

**Decisión cerrada (Q1=A, Q2=HF, Q3=sí, Q4=cadena):**

- **Primario:** Groq `llama-3.1-8b-instant` (`https://api.groq.com/openai/v1`, 14.400 RPD/30 RPM, sin tarjeta, <500ms LPU) — `MODELO_DEFECTO` en `fase-1/gemini_client.py:15` migra de `opencode/muse-spark-1.2-contributor-free` a `llama-3.1-8b-instant` (env override `GROQ_MODEL`/`GEMINI_MODEL`)
- **Secundario:** HuggingFace Router `meta-llama/Llama-3.2-3B-Instruct` (`https://router.huggingface.co/v1`, `hf_xxx`, $0.10/mes) — documentado en `fase-1/.env.example` como `HF_TOKEN`
- **Fallback local:** Ollama `qwen2.5:1.5b` (`http://localhost:11434/v1`, `api_key=ollama`, 986MB, TTFT 200-350ms) — `ollama pull qwen2.5:1.5b && ollama cp qwen2.5:1.5b gpt-3.5-turbo`
- **Cadena:** `Groq → HF Router → Ollama → mock` en `plataforma/webcam/backend/app.py:57 VozHandler` y `fase-1/gemini_client.py:60 crear_cliente_openai()`; `401` corta sin reintento, `429` respeta `retry-after` o 30s, mock final con mensaje tipado en `percepcion-panel` (`"Groq 429, usando HF..."` / `"Sin internet, usando local"`)

**Glosario actualizado:** `CONTEXT.md:84-88` nuevos términos `Proveedor LLM gratuito`, `Free-tier hospedado`, `Fallback local`, `Cadena de fallback`.

**Desbloquea:** [Task: Provisionar credenciales gratuitas y verificar flujo end-to-end](022-task-provisionar-credenciales.md)

## Question

Con 018/019/020 resueltos, ¿proveedor primario gratuito (y secundario) para `fase-1/.env` (`OPENCODE_API_KEY`/`GOOGLE_API_KEY`/`OPENAI_BASE_URL`/`GEMINI_MODEL`), `MODELO_DEFECTO` en `fase-1/gemini_client.py:15` y fallback en `plataforma/webcam/backend/app.py:96 VozHandler` (`gemini → openai → mock`)? Definir política `429/401` (reintento, mock con mensaje `percepcion-panel` vs error), rotación de keys y criterio de cambio de proveedor. HITL con `grilling` + `domain-modeling`.

Respuestas: Q1=A `llama-3.1-8b-instant`, Q2=HF, Q3=sí `qwen2.5:1.5b`, Q4=cadena `Groq→HF→Ollama→mock`.
