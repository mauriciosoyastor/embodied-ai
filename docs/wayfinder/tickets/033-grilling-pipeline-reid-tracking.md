# Ticket 033 — Grilling: Pipeline re-id per-frame + tracking persistente

> Parent: `006-map-vision-viva` · Label: `wayfinder:grilling` · Estado: abierto · Tipo: HITL · Bloqueado por 031,032

## Question

Con 031/032 resueltos, ¿pipeline exacto **re-identificación per-frame + tracking**?

- **Cuándo embed+match:** ¿cada frame, cada N=3, o solo cuando YOLO `person` bbox `IoU<0.5` vs previo?
- **Threshold:** `COSINE_THRESHOLD=0.42` (mapa 000) + `COSINE_GRAY=[0.42,0.55]` — ¿`0.42` firme, `0.55` pendiente, o promedio móvil `hat_e = normalize(e_old*min(N,5)+e_new) cap5` también para re-id?
- **Multi-person:** ¿bloquear enroll si `persons>=2` (actual `enrollment-panel.js:294`) pero permitir re-id múltiple con IDs estables? ¿Qué pasa con oclusión / `face null`?
- **Tracking:** ¿IoU simple `w*h` overlap (ya en `selectPerson` sort `w*h`) vs KCF vs ByteTrack lite para persistir `id` cuando YOLO flickerea 1 frame?
- **Budget latencia:** ¿cómo repartir `Glass-to-Glass <200ms` entre YOLO (~40ms) + detector facial (~30ms) + embed (~30ms) + `LeakyQueue N=1` 10Hz? ¿Caída a `MAX_FPS=10` suficiente o bajar a 5FPS si embed+detect excede?
- **Histéresis:** ¿reusar `THUMBS_N=5`/`GRACE_FRAMES=3` para confirmar `nombre` (evitar flicker `desconocido↔Hola`)?
- **ABORTED latch:** ¿re-id sigue informando pero no muta `WhiteboardState` si `ABORTED`?

HITL con `grilling` + `domain-modeling`. Actualizar `CONTEXT.md` con términos `ReID`, `IoU tracker`.

## Blocking

- Bloquea a 034,035,036. Bloqueado por 031,032.

## Resolution

> Estado: **cerrado 2026-08-23** · Grilling HITL 2 rondas (7 preguntas) + `domain-modeling` · Bloqueos liberados: 034,035

**Decisión cerrada — pipeline visión viva per-frame:**

- **Timing híbrido:** embed+match cada **3 frames @10Hz (~300ms)** + trigger inmediato si `IoU<0.7` vs bbox previo (persona se movió). No cada frame (32ms fijo supera budget secuencial 82ms). Coste medio ~25ms/frame + YOLO 35ms paralelo server = ~60ms cliente, Glass-to-Glass ~107ms medio <200ms.
- **Threshold + zona gris:** `<0.42` = `Hola <nombre>` firme → promueve a `WhiteboardState`; `0.42–0.55` = `posible <nombre>?` amarillo solo overlay, sin Whiteboard; `>0.55` = `desconocido`.
- **Multi-person:** enroll bloquea `persons>=2` (actual `enrollment-panel.js:294`); re-id permite **hasta 3 caras** simultáneas con badges separados, cada una con su `IoU` track independiente; oclusión `face null` → `blockReason` amarillo sin embed.
- **Tracker:** **IoU greedy `IoU>0.5` + edad 5 frames (~500ms drop)**; `<1ms`, suficiente para 1–3 caras @10FPS; descartado `KCF` (~10ms + `cv2`) y `ByteTrack lite` (overkill Kalman) — ver ADR 0005.
- **FPS budget:** mantener `MAX_FPS=10` + `LeakyQueue N=1` + `bufferedAmount>64KB skip` (`ws-client.js:21`); no bajar a 8 FPS; presupuesto `BlazeFace 15ms + mobilefacenet 32/3 + YOLO 35ms paralelo + RTT 25ms` deja 93ms margen.
- **Histéresis ReID:** confirmar `Hola` solo tras **N=3 matches `cos<0.42` consecutivos**, `grace=2` frames fallidos resetean a 0; evita flicker `desconocido↔Hola`, análogo a `handle_gesto N=5`.
- **ABORTED latch:** re-id sigue pintando `overlay.js` (telemetría) pero **no muta `WhiteboardState` ni alimenta `DecisionAgentica`**; seguridad idéntica a `ABORTED latch` gesto.

**Glosario actualizado:** `CONTEXT.md:96` sección *Visión viva (ReID + Tracking per-frame)* con 7 términos (`ReID híbrido`, `Zona gris 0.42–0.55`, `Histéresis ReID N=3`, `Tracker IoU greedy edad 5`, `ABORTED overlay-only`, `Multi-person viva`, `Budget visión viva`).

**ADR:** `docs/adr/0005-vision-viva-pipeline-reid-tracking.md` propuesto (IoU vs KCF/ByteTrack, híbrido 3+IoU vs cada frame, gris vs binario).

**Implicaciones para 034/035/036:**

- 034 (contrato Whiteboard) puede asumir `identities:[{id,nombre,cosine,conf,box,face_box}]` con estado `confirmado|posible|desconocido` y `client-side` matching (privacidad, embedding no sale del browser) — `LeakyQueue` bypass como `enroll_sync` no necesario (re-id es telemetría 10Hz, no control).
- 035 (prototype) debe mostrar variantes badge `Hola <nombre> ✓` verde `<0.42` vs `posible?` amarillo `0.42–0.55` vs `desconocido` gris, con N=3 confirmación y trayectos IoU.
- 036 (task) implementa `face-detector.js` (Ticket 031 BlazeFace) + `face-embedding.js:70` `wasmPaths` + `enrollment-panel.js` loop híbrido + `overlay.js` badge + `IoU` tracker edad 5, sin tocar `ws.py` YOLO.

<!-- context pointer para mapa -->
