# Ticket 003 — Prototype: UX push-to-talk + transcript + TTS

> Label: `wayfinder:prototype` · Parent: `000-map-voz-camara-registro.md` · Estado: cerrado · Resolución: 2026-08-21 · Reclamado por Muse Spark · HITL

## Resolución

**Prototipo throwaway en `plataforma/webcam/frontend/prototype-voz.html` (3 variantes: minimal/chat/overlay) validado en `http://localhost:5173/prototype-voz.html`. Decisión: variante **chat** elegida por usuario (burbujas tipo WhatsApp centrada, waveform integrada, transcript 6 últimas, replay TTS). Mock Muse Spark con STT `webkitSpeechRecognition` es-AR + TTS `speechSynthesis` es-AR, estados IDLE→LISTENING→THINKING→SPEAKING visibles. Prototipo capturado como fuente primaria (rama throwaway `prototype/voz-ux`).**

## Implementación producción (grilling completado 2026-08-21)

- **Plegado a** `frontend/src/voice-chat.js:9` `createVoiceChat` — variante chat en `percepcion-panel` bajo `ws-client`: `wave` integrada, `transcript` 8 últimas burbujas, `pointerdown/up` con `setPointerCapture`, `interim` separado, fallback `input` + `🧪 Test mock`.
- **Estados producción:** `idle → listening (pointerdown, wave + "Soltá para enviar") → thinking (fetch POST /voz) → speaking (speechSynthesis es-AR) → idle`, con `speaking` cancelado al iniciar `listening`. Errores STT (`not-allowed`, `no-speech`, `audio-capture`) con hints y fallback mock Firefox.
- **UX transcript:** panel lateral `percepcion-panel` (no overlay sobre `cam-wrap` para no tapar YOLO boxes); variantes `variants/` mantienen cinematic overlay opcional.
- **`WS_BUFFERED_LIMIT` feedback:** chip "buffer 64KB · 10FPS" en prototype; en producción `ws-client.js:21` `WS_BUFFERED_LIMIT=64KB` + `MAX_FPS=10` con `canSend()` leaky N=1, y habilidad de `enrollment-panel` bloquea si `bufferedAmount` alto. Estado `reconectando…` visible en `p-dot`.
- **Integración voz ↔ enrollment (005):** `main.js:122` `onSendToLLM` pre-llena `enrollment.setNombreFromVoice("me llamo/soy")` + `addBotMessage` feedback al registrar.

> Verificado 21-08-2026: `prototype-voz.html` 3 variantes OK, `voice-chat.js` producción en `http://localhost:5173` con STT es-AR Chrome/Edge, TTS es-AR, `POST /voz` Muse Spark fallback, `pytest 64` + `vite build` OK.

> Estado previo: en progreso · Frontera (desbloqueado) · HITL

## Question

¿Cómo se ve y se siente el flujo voz?

Prototipo throwaway en `frontend/src/main.js` + `percepcion-panel`: botón push-to-talk, waveform, transcript usuario/LLM, y botón replay TTS. Definir estados:

- Idle → Listening (mantener pulsado) → Sending → Thinking (Muse Spark) → Speaking (TTS) → Idle
- Feedback de `WS_BUFFERED_LIMIT` 64KB y `MAX_FPS 10` de `ws-client.js`
- Ubicación del transcript (overlay sobre `cam-wrap` vs panel lateral) y manejo de errores STT

Links: prototipo en `plataforma/webcam/frontend/src/variants/` o rama `prototype/voz-ux`.

Bloqueado hasta tener research STT/TTS y face.
