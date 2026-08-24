# Ticket 042 — Grilling: Contrato Whiteboard con ReID calibrada + Bridge

> Parent: `007-map-arquitectura-productiva` · Label: `wayfinder:grilling` · Estado: **cerrado 2026-08-24** · Tipo: HITL · Bloqueado por 038,039 (liberado)

## Question

Con datos Research 038 (basabraj per-person + LanceDB) + 039 (ros_gz bridge): ¿cómo evoluciona `WhiteboardState` para consumir ReID calibrada sin romper single-writer?

## Grilling Round — 2026-08-24 (HITL)

**Participantes:** human (decisor) + agent (griller) + `domain-modeling`

**Frontera preguntada:**

- Q1 — Payload `detecciones` extendido vs nuevo `type:reid`
- Q2 — Threshold fijo `0.42` + LanceDB vs per-person calibrado
- Q3 — `GzAdapter` + privacidad client-side vs server-side

**Respuestas humanas (verbatim 2026-08-24):**

> lo recomendado esta ok. Bypass para Operaciones de Galería: Las llamadas enroll_sync y purge deben omitir el buffer AsyncLeakyQueue(N=1) mediante un canal de eventos síncrono dedicado para evitar la pérdida de comandos de persistencia durante caídas de cuadros.
> Aislamiento de Muestra Single-Writer: Asegurar que WhiteboardState.last_identidades actúe como una proyección de lectura para superposiciones (overlay.js) y contextualización de agentes conversacionales (DecisionAgentica), impidiendo que afecte directamente al bucle reactivo de movimiento.
> Integración de Simulación Agnóstica: Diseñar GzAdapter como una implementación directa del protocolo SimAdapter, lo que permite intercambiar sin cambios el motor de física (de FakeGzTransport a MuJoCoAdapter o Gazebo Transport C++ API).

Aprobado `Q1 A + Q2 A (Fase1) + Q3 A` con 3 refinamientos arriba.

## Resolution

> Estado: **cerrado 2026-08-24** · HITL grilling + domain-modeling · Decisión unánime

### Decisión 042 — Contrato Whiteboard extiende `detecciones`, threshold Fase 1, GzAdapter agnóstico

**Q1 — Aprobado: Extender `detecciones {boxes, identities?: IdentidadVista[]}`**

- `detecciones` payload existente `ws.py: run_inference → boxes_payload + gesto_payload` se extiende con campo opcional `identities?: IdentidadVista[]` (backward-compat, sin nuevo `EnvelopeType` `type:reid`). `seq/ts` correlativo preservado por `seq_lock ws.py:634`.
- `IdentidadVista {id,nombre,cosine,conf,estado: confirmado(<0.42)|posible(0.42-0.55)|desconocido(>0.55), box,face_box,frame_id,ts, threshold_per_person?: number}` `whiteboard.py:38` client-side `last_identidades: list[IdentidadVista]|None` max 3, `single-writer` memoria, sin `transcript`, no `Reducer` fog.
- `ABORTED overlay-only`: re-id sigue pintando `overlay.js` pero no muta `WhiteboardState.last_identidades` ni alimenta `DecisionAgentica` hasta `reset()` — idéntico a `handle_gesto` latch `CONTEXT.md:59`.
- `DecisionAgentica` (`plataforma/sim DecisionNode` + `Muse Spark/TestModel`) consume `last_identidades` solo como **contexto personalización** (`Hola <nombre>`), no como `CmdVel` reactivo.

**Q2 — Aprobado: `0.42` fijo + `centroid` Fase 1, per-person Fase 2 condicionado, no `LanceDB` ahora**

- **Fase 1 inmediata (este mapa):** Mantener `COSINE_THRESHOLD 0.42` distancia `face-embedding.js:9` + zona gris `0.42-0.55` + `REID_N=3 grace2` + `IoU>0.5 edad5` + `REID_EVERY=3 + IOU_TRIG 0.7` `enrollment-panel.js:13-19`, añadir `centroid mean→L2` por nombre + `margin 0.05` vs runner-up + `track_skip 2-3` + `window 3 aggregate` + gates cheap `blur/pose` — sin `LanceDB`.
- Galería `localStorage:webcam.identities + backend/models/identities.json` híbrido mapa 004 + `GET /identities` snapshot + `enroll_sync/purge` delta permanece; `embedding[128] L2` intacto.
- **Fase 2 condicionada:** Solo si enroll multi-foto `3-5` por nombre, entonces `calibrate_person_thresholds low=0.60 high=0.65` + `ml-matrix SVD` port JS, fallback `0.42` si `len<2`, recalibrar `inter_max/intra_min` locales (no `0.1-0.9` hailo). `LanceDB` diferido hasta `>500` embeddings (server-side `gallery_db/` opcional).
- `threshold_per_person` opcional debug en `IdentidadVista` sin romper wire.

**Q3 — Aprobado: Client-side matching + `GzAdapter` agnóstico**

- **Privacidad client-side:** `face-embedding.js` WASM `128-d` nunca imagen cruda (`CONTEXT.md:82`), `enrollment-panel.js:385 runReId` hasta 3 caras `IoU greedy` + `reIdHyst Map`.
- **Bypass Galería:** `enroll_sync` / `purge` **omiten** `AsyncLeakyQueue(N=1)` `ws.py:654` vía **canal de eventos síncrono dedicado** (rama paralela con `asyncio.Lock` + `store.enroll/purge` atomic `tmp→replace`) + `PendingSync localStorage:webcam.pending_sync` + broadcast `connected_clients ws.py:39` — evita pérdida de persistencia durante `frame drops` (research 023 patrón).
- **Aislamiento Single-Writer:** `WhiteboardState.last_identidades` es **proyección de lectura** para `overlay.js handleIdentidades` y `DecisionAgentica` prompt context; **no afecta bucle reactivo `ActNode → FakeAdapter.send_cmd_vel + step`** — `CmdVel` solo desde `DecisionNode` `Agent` sin acoplar a `cosine`.
- **Integración Agnóstica:** `GzAdapter(SimAdapter)` `plataforma/sim/gazebo_adapter.py` implementa directo `adapter.py:8 Protocol` (`get_observation/send_cmd_vel/get_metrics/step(dt_ms=100)`) → intercambiable `FakeGzTransport ↔ MuJoCoAdapter ↔ Gazebo Transport C++ API` sin cambios caller. `CmdVel(v_x [-1,1], omega_z [-1.5,1.5]) → Twist linear.x/angular.z` `gz.msgs.Twist ROS_TO_GZ` `/model/turtlebot/cmd_vel`, `Odometry nav_msgs/gz.msgs GZ_TO_ROS` `/model/turtlebot/odometry`, `Clock` (039).

### Domain-modeling

- `CONTEXT.md:106 Whiteboard last_identidades` + `IdentidadVista` + `AtributoVista` permanecen; añadir nota `Bypass Galería` + `Single-Writer proyección` como glosario.
- `SimAdapter` `adapter.py:8` sin cambios; `GzAdapter` es peer `MujocoAdapter`; `ABORTED` single-writer preservado.

### Impacto mapa

- Desbloquea `043 Prototype Overlay ReID + Leaky vivo` (ahora frontera tras 041+042).
- No requiere `LanceDB` deps ahora; `Task 044` toma `GzAdapter` agnóstico.

## Blocking

- Bloquea a 043. Bloqueado por 038,039 — **liberado** al cerrar (043 ahora frontera).
