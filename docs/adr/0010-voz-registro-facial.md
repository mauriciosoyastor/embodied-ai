# 0010 — Interacción voz y registro facial (detalle migrado del glosario)

**Status**: accepted (2026-09-04, mapa wayfinder #149 oleada 1). Detalle migrado desde `CONTEXT.md` para devolver al glosario a vocabulario puro (ADR-0007 linter anti-anclas).

**Context**: la sección de voz del glosario acumulaba parámetros de implementación (latencias, schemas WS, modelos) que pertenecen a un registro de decisión.

**Decision**: especificación vigente de voz + registro facial:

- **Push-to-talk**: micrófono por pulsación mantenida; evita escucha continua. Encaja con throttling de envío y límite de buffer del cliente WS.
- **STT**: audio→texto vía Web Speech API en `es-AR`; híbrido con servidor solo si falla el browser. Latencia objetivo <500 ms.
- **TTS**: síntesis desde texto vía `speechSynthesis` en `es-AR`, sin salir del frontend.
- **Transcript**: par usuario→LLM y LLM→usuario en el panel de percepción; fuente de telemetría y debug. No vive en el Whiteboard.
- **Enrollment facial**: YOLO person → detector facial → recorte → embedding → asociación a nombre; se dispara con gesto confirmado por histéresis.
- **Embedding facial**: vector denso de identidad; match por distancia coseno bajo umbral. Privacidad: nunca imagen cruda.
- **Registro (face)**: persistencia de embedding + nombre + ts en `localStorage` y opcional en backend; permite re-identificar sin re-enrollar.
- **Cadena LLM**: proveedor gratuito por defecto con fallback local offline y mock final tipado; `401` corta, `429` respeta retry.
- **EnrollSync / EnrollAck, Purge / PurgeAck, PendingSync, Hidratación híbrida, Bypass de Leaky Queue, IdentitiesStore**: protocolo de sincronización de identidades fuera de la cola de frames (rama dedicada con lock y escritura atómica), snapshot base por HTTP y deltas por WS, cola offline con vaciado al reconectar.

**Consequences**: el glosario conserva solo los nombres y una línea por concepto; los parámetros viven aquí.
