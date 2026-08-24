# Wayfinder Map — Memoria de Objetos (REMIND destilado)

> Label: `wayfinder:map` · Estado: cerrado — way completo · Tracker: local-markdown · Creado: 2026-08-24 · Cerrado: 2026-08-24

## Destination

**Spec para handoff** que decide *cómo* destilar `REMIND` (`arXiv:2607.09267`) — `dual-bank multi-prototype + part/background + neighbor context + Hungarian + ambiguous/provisional` — al **tracking de objetos genéricos** `Whitelist v2` (`plataforma/webcam/frontend/src/main.js` y `ws.py:197`) sin traer `DINOv3` ViT crudo a `Glass-to-Glass <200ms`. Cierra cuando la spec define: (a) banca dual y política `insert/EMA` adaptada a `YOLO11n + mobilefacenet 128-d` proxy, (b) grafo de vecinos `co-ocurrencia` + `veto contextual` para desambiguar `chair vs chair`, (c) `Hungarian joint` vs `IoU greedy edad 5` (`CONTEXT.md:101`), y (d) señal `ambiguous/provisional` blanca en `overlay.js` y `WhiteboardState.last_identidades` sin romper `ABORTED`/`N=3`/`LeakyQueue N=1`.

## Notes

- Dominio: Embodied AI platform · `plataforma/webcam` (`enrollment-panel.js:334`, `face-embedding.js:70`, `ws.py:197`, `overlay.js`, `ws-client.js:1`) + `plataforma/sim` (`WhiteboardState` `plataforma/sim/whiteboard.py:55`) + `fase-1` no tocado (solo `DecisionAgentica`)
- Skills a consultar por sesión: `grilling`, `domain-modeling`, `research`, `prototype`
- Preferencias fijas: **plan, no ejecuta** este mapa (spec, no código); ReID facial `BlazeFace + mobilefacenet 128-d` (`CONTEXT.md:98`) queda intacto y aislado — este mapa ataca **objetos genéricos** `chair, couch, bottle, cup, cell phone, laptop, keyboard, mouse, book, backpack, handbag, remote` (Whitelist v2 `CONTEXT.md:109`); budgets no negociables `Glass-to-Glass <200ms` (`CONTEXT.md:104`), `LeakyQueue N=1` (`MAX_FPS=10` + `WS_BUFFERED_LIMIT=64KB`), `ABORTED overlay-only` (`CONTEXT.md:102`), `COSINE_THRESHOLD=0.42 + gray [0.42,0.55] + N=3 grace2` (`CONTEXT.md:100`); `monorepo desacoplado` + `uv workspace` + `conftest.py`/`pythonpath=["."]` + `ruff/mypy strict`
- Referencias REMIND verificadas: `arXiv:2607.09267` + `https://github.com/cvar-vision-dl/remind-reid-tracker` (`config/default_config.yaml`, `features/`, `memory/`, `association/`, `pipeline/`, `REMIND_METHOD.md`) — `DINOv3` frozen pesado `29M-300M` a `5 FPS`, no apto browser wasm sin destilación
- Estado actual: `006-map-vision-viva` cerrado 2026-08-23; `tracker IoU greedy >0.5 edad 5 <1ms` operativo, `IdentidadVista`/`last_identidades` en `WhiteboardState` (`plataforma/sim/whiteboard.py:70`), pero sin memoria multi-prototype ni contexto vecinos ni Hungarian global

## Decisions so far

<!-- índice — una línea por ticket cerrado: gist + link; el detalle vive en el ticket -->

- [Research: Budget wasm sin DINOv3 — Ticket 039](tickets/039-research-budget-wasm.md) — `mobilefacenet 128-d 4.2MB` único que cabe en `Glass-to-Glass <200ms` (71ms medio / 92ms pico desktop) como `phi_gl` placeholder OOD; `ConvNeXt-Tiny 29M` no cabe (165ms median + 111MB + `dinov3-license` gated); `Hungarian per-class` <0.1ms despreciable vs `IoU greedy edad 5` → veredicto: reuse `face-embedding.js:70` tipado + `neighbor Δ+0.20` rescue (2026-08-24)
- [Research: REMIND internals dual-bank — Ticket 037](tickets/037-research-remind-memory.md) — `work/stable 20/20` `dup 0.92 merge 0.90 promote 5` `alpha 0.02-0.08` + parts `k=4 merge 0.8` + BG `inner3 outer6` + lifecycle `confirm 2 max_miss 10` + gating `STRONG full / AMBIGUOUS EMA*0.2 / WEAK skip` (off por defecto) portable a `mobilefacenet 128-d` solo canal `global` (2026-08-24)
- [Research: Neighbor context + geometry-aware — Ticket 038](tickets/038-research-remind-neighbors.md) — `Co-occurrence kernel α0.5 debounce 3` `Distance 2D` sin depth/pose (100% RGB) + `Δ+0.20/Δ-0.10 capped` `quality 0.35` `veto supported≤3 quality0.60` + `known-set distance` post-Hungarian `max_group4` — portable Whitelist co-visible (2026-08-24)
- [Grilling: Dual-bank adaptada — Ticket 040](tickets/040-grilling-memoria-dual-bank.md) — bancas separadas `person 0.42 vs objetos 0.92`, `8/8 work/stable 16` ~105KB, gating `STRONG/AMBIGUOUS*0.2/WEAK` mapeado a `confirmado/posible/desconocido`, parts/BG `false` v1, `max_misses 10` objetos (2026-08-24)
- [Grilling: Grafo vecinos — Ticket 041](tickets/041-grilling-grafo-vecinos.md) — `co-visible D5 12` debounce3 α0.5 max20 excluye `person`, `Δ+0.20/Δ-0.10 quality0.35 rescue0.60` veto `≤3/0.60` solo `Co-occurrence` v1 client-side (2026-08-24)
- [Grilling: Hungarian + ambiguous — Ticket 042](tickets/042-grilling-hungarian-ambiguous.md) — híbrida `Hungarian per-class 0.90/0.10` fallback `IoU 0.5 edad5` si `quality<0.35`, `IdentidadVista` 5 estados `ambiguo|provisional` blanco, `DecisionAgentica` wait si `ambiguo>2`, `ABORTED` no muta + **TTL vecino verificado** `ttl≈10` episodios para giros rápidos (no en REMIND, mejora destilada) (2026-08-24)
- [Prototype: Overlay white-ambiguous — Ticket 043](tickets/043-prototype-overlay-memoria.md) — throwaway `prototype-memoria-objetos.html` `?variant=a|b` 5 estados blanco dashed `?`, veredicto **A badge-box** + traza 12 para prod (2026-08-24)

## Not yet specified

<!-- fog hacia el destino — no ticketizable aún con nitidez; gradúa cuando la frontera avance -->

<!-- graduado 2026-08-24: proxy features → Ticket 039 cerrado (mobilefacenet placeholder, ConvNeXt descartado) -->
- Profundidad `MiDaS 256 42ms 5Hz` (`CONTEXT.md:113`) como complemento a `neighbor context` geométrico — fog post-memoria.
- Persistencia `identities.json` LRU y `pending_sync` para objetos (hoy solo caras) — fog post-contrato Whiteboard.
- Evaluación tracking real: `IDF1/AssA/HOTA` like REMIND vs `IoU` simple; harness `testing/run_tracking_test.py` style pero headless JS — fog post-spec.
- Safety Envelope consumiendo `ambiguous` (no avanzar si `desconocido`>N) — fog post-señal incierta.

## Out of scope

- Traer `DINOv3` ViT puro a browser wasm sin destilar — rompe `Glass-to-Glass <200ms`; explorado solo como referencia en research.
- Reemplazar ReID facial `BlazeFace + mobilefacenet` — queda aislado (`CONTEXT.md:98`), este mapa es para objetos genéricos.
- Entrenar modelo facial/objeto propio desde cero — solo reuse prototipos existentes + `onnxruntime-web`.
- Video grabación persistente / dataset biometría — solo memoria 128-d volátil + `localStorage` idéntico a caras (`CONTEXT.md:94`).
- ROS2/Gazebo/PX4 Offboard como consumer directo — solo `WhiteboardState.last_identidades` aquí.

## Tickets (frontera)

> Cada ticket es un child de este mapa. Bloqueos: `Bloquea:` = este ticket bloquea a otros. Frontera = abiertos sin bloqueos.

### Ticket 037 — Research: REMIND internals dual-bank + part/background + update gating [wayfinder:research] — CERRADO 2026-08-24

**Question:** ¿Cómo funciona la banca dual `multi-prototype` de REMIND (`memory/`, `features/` en `remind-reid-tracker`) — `appearance + part (K-means/attention) + background`, `insert vs EMA` por `alpha`, y gating `confident vs AMBIGUOUS (EMA-only alpha reducido) vs WEAK (no update)`? Extraer del paper `§3 REMIND Methodology` y `REMIND_METHOD.md` + `config/default_config.yaml`.

**Bloquea:** 040, 041

**Estado:** cerrado — ver [037](tickets/037-research-remind-memory.md) — `20/20 promote5 dup0.92 alpha0.02-0.08` portable solo `global`

### Ticket 038 — Research: Neighbor context + geometry-aware disambiguation [wayfinder:research] — CERRADO 2026-08-24

**Question:** ¿Cómo diseña REMIND el `Co-occurrence Neighbor Graph` (exponentially-weighted kernel por `co-visible IDs`) + `Distance Neighbor Graph` y el `context veto` con bonos `delta+` / `delta-` escalados por cobertura/madurez/densidad, y cómo se integra al `cost matrix` pre-Hungarian? Mapear a `association/` + `§3D-E` paper.

**Bloquea:** 041, 042

**Estado:** cerrado — ver [038](tickets/038-research-remind-neighbors.md) — `Δ+0.20/Δ-0.10 veto≤3` sin depth RGB-only

### Ticket 039 — Research: Budget wasm sin DINOv3 — proxy features + Hungarian cost [wayfinder:research] — CERRADO 2026-08-24

**Question:** ¿Qué proxy de features cabe en `Glass-to-Glass <200ms` sin DINOv3 `300M`? Medir opciones: (a) reuse `mobilefacenet 128-d` como `phi_gl` genérico crop 112×112, (b) `ConvNeXt-Tiny 29M` wasm destilado DINOv3 (`facebook/dinov3-convnext-tiny-pretrain-lvd1689m`), (c) embeddings `YOLO11n`. Costar `Hungarian O(n^3)` vs tu `IoU greedy <1ms` para `n<=13` Whitelist, bajo `LeakyQueue N=1`/`10Hz`.

**Bloquea:** 040, 042, 043

**Estado:** cerrado — ver [039](tickets/039-research-budget-wasm.md) — `mobilefacenet` único que cabe (71/92ms), ConvNeXt no cabe, Hungarian <0.1ms

### Ticket 040 — Grilling: Dual-bank adaptada a webcam — prototipos + política update [wayfinder:grilling] — CERRADO 2026-08-24

**Question:** ¿Cuántos prototipos por objeto Whitelist, cuándo `insert` vs `EMA` (alpha), y cómo el gating `confirmado (<0.42 N=3)` vs `posible (0.42-0.55)` vs `desconocido (>0.55)` + `ambiguous/provisional` de REMIND mapea a tu `Histéresis ReID N=3 grace2` (`CONTEXT.md:100`) y `Tracker IoU edad 5`? Dual-bank para `person` vs genéricos ¿compartida o separada? HITL `grilling` + `domain-modeling`.

**Bloquea:** 043

**Estado:** cerrado — ver [040](tickets/040-grilling-memoria-dual-bank.md) — `8/8 bancas separadas` gating STRONG/AMBIGUOUS/WEAK

### Ticket 041 — Grilling: Grafo vecinos para indoor estático [wayfinder:grilling] — CERRADO 2026-08-24

**Question:** ¿Definimos `co-ocurrencia` como `co-visible en mismo frame D5` (sin pose/depth) al estilo REMIND human-cognition motivation, con veto contextual y bonus `delta` sobre `cost matrix`? ¿Qué umbrales de cobertura/madurez activan neighbors, y cómo coexiste con `YOLO conf>0.50 area>3%` Whitelist (`CONTEXT.md:109`) sin generar falsos vecinos? HITL `grilling` + `domain-modeling`.

**Bloquea:** 042

**Estado:** cerrado — ver [041](tickets/041-grilling-grafo-vecinos.md) — `debounce3 Δ+0.20 veto≤3` client-side

### Ticket 042 — Grilling: Hungarian joint vs IoU greedy + señal ambiguous/provisional [wayfinder:grilling] — CERRADO 2026-08-24

**Question:** ¿Reemplaza `Hungarian joint` al `IoU greedy >0.5` (`enrollment-panel.js:359`) para objetos genéricos o lo complementa (Hungarian para ReID appearance + IoU solo como fallback posicional)? ¿Semántica `ambiguous` (blanco REMIND: no comprometer identidad hasta más evidencia) + `provisional` en `IdentidadVista.estado` y `WhiteboardState.last_identidades` sin romper `ABORTED overlay-only` (`CONTEXT.md:102`)? HITL `grilling` + `domain-modeling`.

**Bloquea:** 043

**Estado:** cerrado — ver [042](tickets/042-grilling-hungarian-ambiguous.md) — híbrida Hungarian/IoU 5 estados + TTL vecino

### Ticket 043 — Prototype: Overlay white-ambiguous + badge por estado objeto [wayfinder:prototype] — CERRADO 2026-08-24

**Question:** Throwaway `prototype-memoria-objetos.html` (no plegar): ¿cómo se ve detection en `white` (`ambiguous` REMIND) vs `confirmado` verde / `posible` amarillo / `desconocido` gris para objetos `chair/couch/...`? Badge ligado a box (Variante A `035` elegida) + traza mem prototipos? HITL `prototype`.

**Bloquea:** —

**Estado:** cerrado — ver [043](tickets/043-prototype-overlay-memoria.md) — veredicto **A badge-box** blanco dashed
