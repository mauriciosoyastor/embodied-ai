# Ticket 005 — Grilling: Flujo enrollment facial + confirmación por gesto

> Label: `wayfinder:grilling` · Parent: `000-map-voz-camara-registro.md` · Estado: cerrado · Resolución: 2026-08-21 · Reclamado por Muse Spark · HITL

## Decisión (grilling 2026-08-21)

**Flujo acordado:** `YOLO person (conf>0.6, area>15%)` → `MediaPipe Face Detection` dentro del crop person → `ArcFace mobilefacenet 128-d` (onnxruntime, `numpy 1.26`, 4-8MB, ~35ms) → `thumbs_up` histéresis **N=5** confirma → guarda en `localStorage` `webcam.identities: Array<{id,nombre,embedding[128],ts,frame_id,person_box}>` → UI nombrar/borrar. Consentimiento previo obligatorio.

**Respuestas grilling:**

- **Múltiples personas/caras:** Si ≥2 `person` con `conf>0.6 && area>0.15` → bloquear enrollment, overlay "Solo 1 persona en frame — despejá". Si 1 person pero 0 faces → "Acercá rostro, bien iluminado". Si >1 face dentro del mismo person (espejo/foto) → tomar face más grande, log warning. Solo se enrolla el `person` más grande que pase umbral.
- **Oclusión:** Rechazar si face `conf<0.7` o `eye landmarks` no visibles o bbox <8% frame. Reintento guiado por voz/TTS: "Quitá lentes/barbijo, mirá de frente".
- **Re-identificación:** Distancia coseno **0.42** (ArcFace L2-norm, equivalente euclidean ~1.05). Match <0.42 → misma identidad; 0.42-0.55 zona gris → "¿Sos X? Confirmá con pulgar"; >0.55 desconocido. Galería local para prototype.
- **Nombre:** Input texto obligatorio (`max 32, [A-Za-z ]`) + atajo voz `STT es-AR` "me llamo X / soy X" que pre-llena input. No se persiste sin nombre validado. `thumbs_up` confirma solo si input no vacío.
- **`ABORTED latch`:** Sí bloquea enrollment. Cuando FSM en `ABORTED` (aperiodic safety), botón Registrá deshabilitado + tooltip "Safety latch activo — reseteá". Enrollment no bypassa safety.
- **UX:** Modal consentimiento explícito (checkbox "Guardo mi embedding localmente, puedo borrarlo") previo a primera captura, retención solo `localStorage` (no `backend/models/`, no commit), TTL indefinido para prototype, borrado por identidad (✕) + "Borrar todos".

## Domain-modeling

- `Enrollment facial`: acto de capturar `Embedding facial` + `nombre` + consentimiento y persistirlo como `Registro`.
- `Embedding facial`: vector `128-d float32 L2-normalizado` extraído de face crop 112×112 alineado (ArcFace).
- `Registro`: `{id: nanoid, nombre, embedding, ts: ISO, frame_id, person_box: Box}` en galería local.
- `Galería`: `localStorage["webcam.identities"]`, fuente de verdad para re-id.

> Estado previo: en progreso · HITL — desbloqueado tras Ticket 002 (ArcFace onnxruntime reusable con hand_landmarker sin colisión TF Lite).

## Implementación (2026-08-21)

- `plataforma/webcam/frontend/src/face-embedding.js:1` `EMBEDDING_DIM=128`, `COSINE_THRESHOLD=0.42`, `l2Normalize`, `cosineDistance`, `stubEmbedding` determinístico + `createFaceEmbedder` con hook `onnxruntime-web` (variable import → stub si no modelo, ready en `/models/mobilefacenet.onnx`).
- `plataforma/webcam/frontend/src/enrollment-panel.js:1` `STORAGE_KEY=webcam.identities`, `THUMBS_N=5` + `GRACE=3`, `selectPerson(conf>0.6 && area>0.15)`, multi-person block, consent `localStorage:webcam.consent`, input texto + STT 🎤 "me llamo/soy", galería con ✕ + borrar todos, `ABORTED` bloquea, crop 112×112 para futuro ArcFace.
- `frontend/src/main.js:4` + `voice-chat.js:310` wiring: `enrollment.handleDetecciones/Gesto/Estado` desde `ws/percepcion`, `voice onSendToLLM` pre-llena nombre por voz, `addBotMessage` feedback al registrar, `Mock boxes` alimenta enrollment.
- Verificado: `ruff`/`mypy` clean, `pytest webcam 64 passed`, `vite build 13 modules 529KB`, `GET /health ok`, `POST /voz mock` ok, `http://localhost:5173` vivo (HMR).
