# Ticket 004 — Grilling: Backend voz — integración Muse Spark streaming

> Label: `wayfinder:grilling` · Parent: `000-map-voz-camara-registro.md` · Estado: cerrado · Resolución: 2026-08-21 · Reclamado por Muse Spark · HITL

## Decisión (grilling)

**Endpoint elegido: `POST /voz` (opción B)** — no multiplexar `WS /ws/percepcion` (opción C). Frontend `voice-chat.js` hace `fetch POST http://localhost:8001/voz {prompt}` → `{text}` JSON. CORS para `http://localhost:5173`.

## Implementación

- `plataforma/webcam/backend/app.py:71` `POST /voz` con `VozRequest`, lazy import `fase-1/gemini_client`, fallback mock si placeholder key (`sk-reemplaza`), `CORSMiddleware` para Vite.
- `frontend/src/main.js:4` + `src/voice-chat.js:99` `onSendToLLM` hace `fetch` a `/voz` con fallback mock local.
- Verificado: `POST /voz {"prompt":"hola"}` → mock `¡Hola! Soy Muse Spark...` con placeholder, y con key real usa `gemini_client.responder` (Muse Spark). `GET /health` OK, `pytest` 64+6 passed, `ruff`/`mypy` clean.

> Estado previo: en progreso · Frontera (desbloqueado) · HITL

## Question

¿Endpoint para voz? Opciones:
- A) Frontend llama directo a Muse Spark via OpenAI SDK (clave en browser — no seguro)
- B) Nuevo `WS /ws/voz` o `POST /voz` en FastAPI que proxya a `fase-1/gemini_client.responder` con `muse-spark-1.2`, streaming SSE para TTS por chunks
- C) Reusar `WS /ws/percepcion` multiplexado con `type: "voz"` en envelope D5

Decidir auth, rate-limit, fallback Gemini (`MODELO_GEMINI_LEGACY`), y si se reutiliza `MissionFSM` para estados de voz.
Requiere `OPENCODE_API_KEY` lista (ticket 006).

Grilling: conversar con humano, luego domain-modeling para términos `Transcript`, `TTS chunk`.
