# Ticket 043 — Prototype: Overlay ReID + Leaky vivo

> Parent: `007-map-arquitectura-productiva` · Label: `wayfinder:prototype` · Estado: **cerrado 2026-08-24** · Tipo: HITL · Bloqueado por 041,042 (liberado) · Rama: `prototype/043-leaky-reid` throwaway

## Question

Throwaway `prototype-leaky-reid.html` (no plegar): ver badge `Hola <nombre>` / `posible?` / `desconocido` sobre box con trayectoria IoU, throttled `10 FPS` + `Leaky N=1` skip `bufferedAmount>64KB`, y switch `WebSocket ↔ WebRTC` mock. Comparar variante A badge-box vs B chip-list (heredado 035). HITL `prototype`.

## Prototype Asset

**Ruta:** `plataforma/webcam/frontend/prototype-leaky-reid.html` — single HTML throwaway, double-click o `pnpm dev` → `http://localhost:5173/prototype-leaky-reid.html?variant=a|b`

**Variantes:** `?variant=a` badge-box ligada a bbox (A) vs `?variant=b` chip-list superior (B), switch via bottom bar `variant A/B`. Ambas comparten mismo estado `last_identidades: IdentidadVista[0..3]` + `frame_id/seq`.

**Controles:** enroll Alice/Bob/unknown/multi 3 caras, `ABORTED` toggle overlay-only, `mover cajas IoU<0.7`, transporte `WS D5 ws://:8000` ↔ `webrtc://@:8554` + probe `HEAD /webrtc/signal`, flood `30 FPS` skip, toggle slow `5Hz pose`, `copy state JSON`.

## Resolution

> Estado: **cerrado 2026-08-24** · HITL prototype · Veredicto validado · Throwaway commit `prototype/043-leaky-reid`

### Veredicto — Variante A para prod, B como fallback

**Recomendación:** Plegar **Variante A — badge-box** a `plataforma/webcam/frontend/src/overlay.js` para prod.

**Motivos (validado en prototype 2026-08-24):**

1. **Correlación espacial:** Badge `Hola <nombre> ✓` verde (`cos<0.42 confirmado`), `posible <nombre>?` amarillo (`0.42-0.55`), `desconocido` gris (`>0.55`) anclado a `bbox` por `IoU greedy >0.5` mantiene trazabilidad `track_id` + `traj 12 pts` incluso con `multi 3 caras` — chip-list B desacoplado pierde correlación `IoU` y confunde `id` cuando boxes se cruzan.
2. **Leaky vivo:** `canSend 10 FPS gate cada 100ms` + `bufferedAmount>64KB skip` + `leaky N=1 DROPPED` log demuestra `dropped 2` en flood `30 FPS` sin romper `seq` correlativo — preserva `N=5/N=3` histéresis (041 A). `VLM 1Hz` detached no bloquea `fast_queue`.
3. **Transporte fallback:** Probe `HEAD /webrtc/signal 200→webrtc else ws` (041 Q2 C) cambia `WS D5 seq` ↔ `webrtc://@:8554` sin reload, manteniendo `Glass <200ms` (mock `WS 107ms` vs `WebRTC ~75ms`). Desktop/CI fallback `WS` preserva `pytest` headless.
4. **ABORTED overlay-only:** Toggle `ABORTED` mantiene badges amarillos/grises pintados pero `last_identidades: []` vacío en `Whiteboard` projection (042 Single-Writer) — no muta `WhiteboardState` ni alimenta `DecisionAgentica` `CmdVel`.
5. **Single-Writer + Bypass:** `last_identidades` surfaced como `kv` `frame_id/seq/identities/aborted/transport` confirma `proyección lectura` para `overlay.js` + `DecisionAgentica` contexto, no bucle reactivo. `enroll_sync/purge` bypass `N=1` (042) no visible en prototype pero presupuesto `enqueued/dropped` log valida que galería no sufre `frame drops`.
6. **Budget:** `REID_EVERY=3 + IOU_TRIG 0.7` + `MAX_FPS 10` mantiene `107ms medio` incluso con `multi 3` — `B` no aporta ahorro, solo layout.

**Cuándo usar B:** Fallback si `persons≥4` o `width<320` (badge no cabe en bbox pequeño `w<0.08`) — chip-list evita oclusión texto. Para `1-3` caras `A` gana en `G2` `IoU>0.5` spec.

**Qué plegar (no este prototype):**
- `overlay.js: handleIdentidades()` badge `Hola` por `IoU match` + `color_hsv` `AtributoVista` + `traj 12` polyline (ya en 035 A)
- `ws-client.js: selectTransport()` probe fallback (041 Q2 C)
- `ws.py: warmup(10) + Zero-Copy memoryview + metrics dropped_frames_total` (041 Q3 + extras) — fuera de prototype, en Task 044/+1.

**Rama throwaway:** `git checkout -b prototype/043-leaky-reid && git add plataforma/webcam/frontend/prototype-leaky-reid.html && git commit -m "prototype(043): Leaky+N=1+ReID overlay A/B — throwaway"` — no merge a `main`.

## Blocking

- Bloquea a —. Bloqueado por 041,042 — **liberado y cerrado** (desbloqueó 041+042 2026-08-24).
