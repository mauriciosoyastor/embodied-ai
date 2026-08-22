# Ticket 007 — Grilling: Privacidad y retención de embeddings

> Label: `wayfinder:grilling` · Parent: `000-map-voz-camara-registro.md` · Estado: cerrado · Resolución: 2026-08-21 · Reclamado por Muse Spark · HITL

## Decisión (grilling 2026-08-21)

**Persistencia elegida: `localStorage` únicamente — `webcam.identities: Array<{id,nombre,embedding[128],ts,frame_id,person_box,face_box}>` + `webcam.consent="1"`.** No `IndexedDB` (innecesario para galería ≤10 identidades prototype) ni `backend/models/identities.json` (evita fuga de biometría por commit/bak). Backend no almacena nada — `POST /voz` stateless, `WS /ws/percepcion` no guarda frames. Opción backend queda para futuro con cifrado at-rest, fuera de scope mapa actual.

**Respuestas grilling:**

- **Consentimiento explícito:** Checkbox obligatorio en `enrollment-panel.js:53` bloquea enrollment hasta aceptar. Texto: "Guardo mi embedding 128-d **localmente** (solo en este navegador). Puedo borrarlo en cualquier momento. No se sube al backend ni se commitea." Primer render muestra bloque; al tildar se persiste `webcam.consent=1` y oculta banner. Grilling domain: `Consentimiento` = acto informado previo a `Enrollment facial`.
- **Aviso de borrado:** UI ya implementada — botón ✕ por identidad (`data-del`) borrado inmediato + `setHint "Borrado {id}"`, y `Borrar todos` (`#enr-clear`) con `confirm()`. Sin backend sync. Para prototipo no hay "Olvidar mi rostro" global separado — es el mismo flujo. Acción es irreversible local, sin papelera.
- **¿Se commitean snapshots?** No. `models/*.onnx` ya ignorado; añadir `identities.json`, `gallery.json`, `webcam.identities` a `.gitignore` + pre-commit hook mental: `trajectory.jsonl` ya cubierto. Embeddings nunca van a Git, ni a `dist/`. Capturas `frame_id` solo en memoria.
- **Retención:** Persistente hasta borrado manual. No TTL ni expiración por sesión — decisión hard-to-reverse evitada: retener en localStorage simplifica re-identificación `thr cos 0.42` sin re-enrollment, pero el usuario controla borrado. Para producción futura valorar TTL 30d + re-consent.
- **Out of scope deliberado:** Sin cifrado localStorage (prototype), sin sync multi-dispositivo, sin DB central. Streaming voz no persiste `Transcript` — solo en `voice-chat.js` memoria.

## Domain-modeling

- `Registro biometrico local`: tupla `(nombre, embedding)` bajo control del usuario, no transferible.
- `Galería`: colección en `localStorage`, fuente de verdad para re-id; vacía = estado limpio privacy-by-default.
- `Borrado`: operación que elimina `Registro` y deja traza solo en UI `hint`, no recuperable.

> Estado previo: abierto · Frontera · HITL — desbloqueado tras 005 (localStorage ya operativo).
