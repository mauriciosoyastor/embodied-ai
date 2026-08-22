# Wayfinder Map — Voz + Registro por Cámara

> Label: `wayfinder:map` · Estado: abierto · Tracker: local-markdown (sin GitHub issues configurado)

## Destination

Prototipo funcional mínimo en `plataforma/webcam` donde el usuario **habla por micrófono** (push-to-talk es-AR) → STT browser → **Muse Spark 1.2 free** (`opencode/muse-spark-1.2-contributor-free` vía `openai:opencode/...`) responde → **TTS browser** reproduce → transcript visible en `percepcion-panel`, **y se registra por cámara** vía enrollment facial (YOLO `person` + detector facial → embedding → `localStorage` + confirmación por gesto `thumbs_up`). Cierra cuando el flujo completo corre en `http://localhost:5173` ↔ `http://localhost:8001` sin salir del browser, con tests headless y sin secretos commiteados.

## Notes

- Dominio: Embodied AI platform · `plataforma/webcam` (FastAPI + Vite) + `fase-1` (Pydantic AI orquestador)
- Skills a consultar por sesión: `grilling`, `domain-modeling`, `prototype`, `research`
- Preferencias fijas: push-to-talk (no wake-word), es-AR, híbrido STT browser + Muse Spark + TTS browser, enrollment facial local-first, `Muse Spark 1.2 free` por defecto (ver `fase-1/.env.example`)
- Backend real ya verificado: `yolo11n.onnx` + `hand_landmarker.task` cargan (`is_stub=False`), `GET /health` y `WS /ws/percepcion` operativos

## Decisions so far

- [Modelos reales cargados](../wayfinder/000-map-voz-camara-registro.md) — `descargar_modelos.py` descarga YOLO v8.3.0 + hand_landmarker y `get_*_detector().is_stub=False` (21-08-2026)
- [Muse Spark 1.2 free como default](../../fase-1/gemini_client.py) — `MODELO_DEFECTO=opencode/muse-spark-1.2-contributor-free`, fallback Gemini, `orchestrator.py` → `openai:opencode/...` (21-08-2026)
- [Fix vite proxy ws-client.js](../../plataforma/webcam/frontend/vite.config.js) — proxy `"/ws"` → `"/ws/percepcion"` para no interceptar `/ws-client.js` (21-08-2026)
- [Research STT/TTS browser — Ticket 001](tickets/001-research-stt-tts-browser.md) — Chrome/Edge `webkitSpeechRecognition` es-AR OK en `localhost:5173` secure context, push-to-talk cumple gesto, Firefox fallback texto, TTS voces OS-dependientes (21-08-2026)
- [Research face embedding — Ticket 002](tickets/002-research-face-embedding.md) — `onnxruntime` ArcFace `mobilefacenet` 128-d recomendado (4-8 MB, 30-45 ms) reuse `onnxruntime==1.29`, pin `numpy 1.26`, sin colisión TFLite (21-08-2026)
- [Task API key Cursor free — Ticket 006](tickets/006-task-api-key-cursor.md) — `fase-1/.env` provisionado con `OPENCODE_API_KEY` placeholder, `gemini_client`/`orchestrator` migrados a Muse Spark, `pytest fase-1` 6 passed (21-08-2026, pendiente key real)
- [Prototype UX voz — Ticket 003](tickets/003-prototype-ux-voz.md) — throwaway `prototype-voz.html` 3 variantes, decisión **chat** elegida (burbujas centradas, STT es-AR + TTS) — plegado a `src/voice-chat.js` (21-08-2026)
- [Backend voz — Ticket 004](tickets/004-grilling-backend-voz.md) — `POST /voz` con CORS + proxy a `fase-1/gemini_client` (Muse Spark) + fallback mock, `voice-chat.js` conectado vía `fetch` (21-08-2026)
- [Grilling enrollment — Ticket 005](tickets/005-grilling-enrollment-facial.md) — YOLO `person>0.6 & area>15%` → Face Detection → ArcFace 128-d → `thumbs_up N=5` confirma, single-person block, coseno 0.42, `localStorage:webcam.identities`, `ABORTED` bloquea, input texto + voz (21-08-2026)
- [Privacidad retención — Ticket 007](tickets/007-grilling-privacidad.md) — `localStorage` únicamente (`webcam.identities` + `webcam.consent`), sin IndexedDB/backend, persistente hasta borrado manual ✕/`Borrar todos`, consentimiento checkbox bloqueante, nunca commitear biometría (`.gitignore` `identities.json`) (21-08-2026)

## Not yet specified

- Streaming vs respuesta completa de Muse Spark: ¿TTS por chunks o solo al final?
- Fallback STT server (Whisper) si `webkitSpeechRecognition` no está disponible (Firefox/Safari)

## Out of scope

- Auth cloud / OAuth / base de datos centralizada — fuera del prototipo mínimo (solo localStorage)
- Wake-word siempre-escuchando y VAD continuo — se usa push-to-talk para simplicidad
- Video grabación persistente — solo snapshot de enrollment, no stream storage
- Integración ROS/MuJoCo — pertenece a otro mapa wayfinder

## Tickets (frontera)

> Cada ticket es un child de este mapa. Bloqueos nativos en tracker real; aquí se listan con `Bloquea:` y estado `abierto/cerrado`.

### Ticket 001 — Research: Compatibilidad STT/TTS browser es-AR [wayfinder:research] — CERRADO 2026-08-21
**Question:** ¿Qué cobertura real tiene Web Speech API (`webkitSpeechRecognition` + `speechSynthesis`) en Chrome/Edge/Firefox/Safari para `es-AR` con push-to-talk, y qué permisos/HTTPS se requieren en `localhost:5173`?
**Bloquea:** 003, 004
**Estado:** cerrado — ver [001](tickets/001-research-stt-tts-browser.md)

### Ticket 002 — Research: Detector facial + embeddings para enrollment [wayfinder:research] — CERRADO 2026-08-21
**Question:** ¿MediaPipe Face Detection/Tasks vs `face-api.js` vs `onnxruntime` face para extraer embedding 128-d desde recorte YOLO `person`? Evaluar bundle size, licencia, `numpy<2` compat, y si puede correr junto a `hand_landmarker.task` sin colisión TF Lite.
**Bloquea:** 003, 005
**Estado:** cerrado — ver [002](tickets/002-research-face-embedding.md)

### Ticket 003 — Prototype: UX push-to-talk + transcript + TTS [wayfinder:prototype] — CERRADO 2026-08-21
**Question:** ¿Cómo se ve y se siente el flujo voz? Prototipo throwaway en `frontend/src/main.js` + `percepcion-panel`: botón push-to-talk, waveform, transcript usuario/LLM, y botón de replay TTS. Definir estados y feedback de `WS_BUFFERED_LIMIT`.
**Estado:** cerrado — ver [003](tickets/003-prototype-ux-voz.md) — variante **chat** elegida, plegado a `src/voice-chat.js` + `src/enrollment-panel.js`

### Ticket 004 — Grilling: Backend voz — integración Muse Spark streaming [wayfinder:grilling] — CERRADO 2026-08-21
**Question:** ¿Endpoint para voz? Opciones: A) Frontend llama directo a Muse Spark via OpenAI SDK (clave en browser — no), B) Nuevo `WS /ws/voz` o `POST /voz` en FastAPI que proxya a `fase-1/gemini_client.responder` con `muse-spark-1.2`, streaming SSE para TTS por chunks. Decidir auth, rate-limit y fallback Gemini.
**Estado:** cerrado — ver [004](tickets/004-grilling-backend-voz.md) — `POST /voz` implementado

### Ticket 005 — Grilling: Flujo enrollment facial + confirmación por gesto [wayfinder:grilling] — CERRADO 2026-08-21
**Question:** ¿Pasos exactos de registro? YOLO `person` → face bbox → embedding → `thumbs_up` histéresis N=5 confirma → guarda en `localStorage` con nombre. ¿Qué pasa con múltiples caras, oclusión, y re-identificación posterior? ¿UI para nombrar/borrar identidad?
**Estado:** cerrado — ver [005](tickets/005-grilling-enrollment-facial.md) — `face-embedding.js` + `enrollment-panel.js` implementados + wiring voz

### Ticket 006 — Task: Provisionar API key Cursor free y .env [wayfinder:task] — CERRADO 2026-08-21 (AFK)
**Question:** Trabajo manual previo a decisión 004: crear API key Muse Spark free en Cursor/OpenCode, configurar `fase-1/.env` (`OPENCODE_API_KEY` + `OPENAI_BASE_URL` si aplica), verificar `python fase-1/main.py "hola"` responde con Muse Spark. No hay decisión, solo deja credenciales listas.
**Estado:** cerrado — placeholder en `.env`, pendiente key real del usuario

### Ticket 007 — Grilling: Privacidad y retención de embeddings [wayfinder:grilling] — CERRADO 2026-08-21
**Question:** ¿Dónde se persiste el registro facial y por cuánto tiempo? `localStorage` vs `backend/models/identities.json` vs IndexedDB. Consentimiento explícito, aviso de borrado, y si se commitean snapshots. Definir política para prototipo.
**Estado:** cerrado — ver [007](tickets/007-grilling-privacidad.md) — `localStorage` only, consent bloqueante, borrado ✕, nunca commitear
