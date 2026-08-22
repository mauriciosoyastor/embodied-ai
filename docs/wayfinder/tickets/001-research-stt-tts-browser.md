# Ticket 001 — Research: Compatibilidad STT/TTS browser es-AR

> Label: `wayfinder:research` · Parent: `000-map-voz-camara-registro.md` · Estado: cerrado · Resolución: 2026-08-21

## Resolución

**Respondido por subagente research (branch `research/stt-tts-browser`):**

- Chrome/Edge (Chromium) soportan `webkitSpeechRecognition` es-AR vía cloud Google, `localhost:5173` es secure context sin HTTPS, push-to-talk cumple requisito de gesto de usuario para `start()` y `speechSynthesis.speak()`.
- Firefox desktop ❌ disabled by default, requiere fallback a input texto. Safari 14.1+ parcial.
- `speechSynthesis` universal pero voces `es-AR` dependen de OS; fallback a `es-ES` si no instalada.
- **Decisión:** Prototipo híbrido browser STT+TTS es viable, target Chrome/Edge, sin backend Whisper para MVP. Detalle en `docs/wayfinder/000-map-voz-camara-registro.md`.

> Estado previo: abierto · Frontera

## Question

¿Qué cobertura real tiene Web Speech API (`webkitSpeechRecognition` + `speechSynthesis`) en Chrome/Edge/Firefox/Safari para `es-AR` con push-to-talk, y qué permisos/HTTPS se requieren en `localhost:5173`?

Investigar:
- `webkitSpeechRecognition` vs `SpeechRecognition` standard, soporte por navegador y prefijo
- Códigos de idioma `es-AR` vs `es-ES` y calidad de reconocimiento
- Permisos `getUserMedia` vs `SpeechRecognition` — ¿requiere gesto de usuario (push-to-talk) en cada sesión?
- `localhost` vs `https` para STT/TTS, y si `speechSynthesis` requiere voces instaladas del OS
- Latencia típica y si soporta `continuous` + `interimResults` para feedback en `percepcion-panel`

Resolver con research subagent — capturar hallazgos en branch `research/stt-tts-browser` con puntero de contexto.
