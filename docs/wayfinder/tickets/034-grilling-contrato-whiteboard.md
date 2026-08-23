# Ticket 034 — Grilling: Contrato percepción → WhiteboardState

> Parent: `006-map-vision-viva` · Label: `wayfinder:grilling` · Estado: abierto · Tipo: HITL · Bloqueado por 033

## Question

¿Qué **contrato** nuevo entre `plataforma/webcam` y `plataforma/sim` `WhiteboardState` expone re-id?

- ¿Extender `detecciones {frame_id,boxes:[{x,y,w,h,cls,conf}]}` con `identities:[{id,nombre,conf,cosine,box,face_box}]` vs nuevo envelope `type:reid` D5?
- `WhiteboardState` actual (`plataforma/sim` Ticket 010): `estado, frame_id, last_gesto, last_observation, last_decision, metrics` sin `transcript`, single-writer memoria, `Reducer` fog. ¿Agregar `last_identidades` o `last_reid`? ¿Payload `EnrollSync`/`IdentitiesStore` reuse?
- ¿Matching **client-side** (privacidad: embedding nunca sale del browser, solo `id/nombre/cosine` via WS) vs **server-side** (enviar crop JPEG y `identities.json` match en `ws.py`)?
- ¿Cómo `DecisionAgentica` (`plataforma/sim` `DecisionNode` `Muse Spark`) consume `last_identidades`? ¿`CmdVel` condicionado a `nombre` (ej. `Hola <nombre>` en `voice-chat.js`)?
- Envelope D5: ¿reusar `seq/ts` existente, `LeakyQueue N=1` excluye `reid` como `enroll_sync` (bypass) o pasa por queue?
- ¿Hidratación híbrida `GET /identities` + `pending_sync` se extiende a `reid`?

HITL con `grilling` + `domain-modeling`. Bloqueado por 033 (necesita pipeline 033).

## Blocking

- Bloquea a 036. Bloqueado por 033.

## Resolution

> Estado: **cerrado 2026-08-23** · Grilling HITL 2 rondas (6 preguntas) + `domain-modeling` · Bloqueo liberado: 036 parcial

**Decisión cerrada — contrato percepción → Whiteboard:**

- **Payload D5:** extender `detecciones {frame_id, boxes:[{x,y,w,h,cls,conf}], identities?: IdentidadVista[]}` en mismo `type:detecciones`; **no** nuevo `type:reid` (evita duplicar `seq/ts` y `LeakyQueue`). Compatible backward (clientes viejos ignoran `identities`).
- **Schema Whiteboard:** `WhiteboardState.last_identidades: list[IdentidadVista] | None` (`whiteboard.py:35`) con `IdentidadVista {id,nombre,cosine,conf,estado,box,face_box,frame_id,ts}`; single-writer memoria, sin `transcript`, init `None`, update cada 3 frames + `IoU<0.7` (hereda híbrido 033), max 3.
- **Matching lado:** **client-side** (`face-embedding.js` + `loadGallery()` hidratada vía `GET /identities`); embedding 128-d **nunca** sale del browser (privacidad), no ocupa `LeakyQueue N=1` ni requiere `crop JPEG` a `ws.py`/`IdentitiesStore`.
- **LeakyQueue:** re-id **no** via `AsyncLeakyQueue N=1`; patch directo `WhiteboardState` en JS (memoria) + opcional broadcast `type:identities` bypass si multi-cliente (patrón `enroll_sync`), pero no piggyback en `frame` queue. YOLO `boxes` sigue `N=1`.
- **Hidratación:** reusa `GET /identities` + `PendingSync` existente; re-id lee `loadGallery()` ya hidratada al iniciar (`enrollment-panel.js:42 hydrateFromServer`), cap 5 `hat_e` preservado.
- **Consumo DecisionAgentica:** `DecisionNode` (`graph.py:118`) inyecta `last_identidades` como contexto LLM `"personas: Hola Ana (0.91) | posible Bob? (0.48)"` para personalizar `voice-chat.js` saludo/razón, **no** condiciona `CmdVel` directo (seguridad; `ABORTED` ya bloquea).

**Glosario actualizado:** `CONTEXT.md:102` `IdentidadVista` + `Whiteboard last_identidades`.

**ADR:** `docs/adr/0006-whiteboard-last-identidades.md` (extender detecciones vs nuevo type, client-side vs server-side, last_identidades lista).

**Implicaciones para 035/036:**

- 035 prototype debe renderizar `identities` extendidas con `estado` color verde `<0.42` / amarillo `0.42–0.55` / gris `>0.55` y confirmar N=3.
- 036 task implementa `WhiteboardState.last_identidades` Pydantic + TS `IdentidadVista`, patch JS `whiteboard.last_identidades = identities` tras `cosineDistance` N=3, sin tocar `ws.py` YOLO.
