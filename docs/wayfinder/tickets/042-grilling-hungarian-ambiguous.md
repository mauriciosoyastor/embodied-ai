# Ticket 042 — Grilling: Hungarian joint vs IoU greedy + señal ambiguous/provisional

> Parent: `007-map-memoria-objetos.md` · Label: `wayfinder:grilling` · Estado: **cerrado 2026-08-24** · Tipo: HITL (grilling + domain-modeling) · Claim: `mauri`

## Resolution

**Decidido con el usuario 2026-08-24 (Q1-Q4 aprobados):**

- **Q1 híbrida B:** `Hungarian per-class locks 0.90/0.10 dummies 0.05→0.72` como primary para objetos genéricos; fallback `IoU greedy >0.5 edad 5` si `quality<0.35` o `s_sim<0.60 rescue` (040/041). Ambos <0.1ms para `n≤13` (039), no rompe `Glass-to-Glass 71/92ms` ni `LeakyQueue N=1`.
- **Q2 5 estados A:** `IdentidadVista.estado` se extiende de `confirmado|posible|desconocido` a `confirmado|posible|ambiguo|provisional|desconocido` (`plataforma/sim/whiteboard.py:42`). `ambiguo`= gap<0.03 + quality<0.35 → blanco REMIND `EMA*0.2` sin promo; `provisional`= TENTATIVE `confirm 2`.
- **Q3 consumo:** `DecisionAgentica` vía `WhiteboardState.last_identidades` (`plataforma/sim/whiteboard.py:70`) — si `ambiguo>2` o `provisional` → `wait/rotate` no `CmdVel`.
- **Q4 ABORTED:** Hungarian + `NeighborGraph bump` no mutan en `ABORTED` latch (`enrollment-panel.js:468`), overlay sí pinta blanco/verde (`CONTEXT.md:102`).

## Verificación adicional — TTL NeighborGraph para giros rápidos (pedido usuario 2026-08-24)

**Estado verificado: REMIND NO tiene TTL; tu idea es mejora válida destilada.**

- `memory/neighbor_graph.py:1-71` + `config memory.neighbors` muestran `episode_count` + `weight` + `last_seen_ts/episode` con `decay_per_episode 1.0` (sin decaimiento) y `trim_strategy weight/recent` `max_neighbors 20` — no hay expiración temporal. `debounce_frames 3` + `force_episode_every_frames 3` + `episode` por racha amortigua jitter YOLO, pero **giro rápido 90° en 200ms** genera co-visibilidades espurias `silla salón ↔ silla cocina` que quedan permanentes (bias).
- `update` no purga por tiempo; solo `episode_count` crece monotónico. No hay campo `ttl` ni `expiry`.
- **Recomendación destilada:** Añadir **TTL episódico** `ttl_episodes=10` (~2s @5FPS episodio/3frames) a `NeighborEdge` — si `current_episode - last_seen_episode > TTL`, ignorar edge en `p_conditional` y `weight` (o podar `trim` prioritario). Evita sesgar `Δ+` por vecinos fugaces de giro, sin costo. Se documenta como extensión propia, no de REMIND. Ver `NeighborEdge.last_seen_episode` ya existe para implementarlo.

Términos en `CONTEXT.md:117` (`Hungarian híbrido`, `Ambiguo/Provisional`, `TTL vecino`).

## Question

Con `040`+`041` más `039` (costo Hungarian), decidir:

- ¿Arquitectura assignment: `Hungarian joint global` reemplaza `IoU greedy >0.5` (`enrollment-panel.js:359`) para genéricos, o híbrida `Hungarian (appearance+context)` primero + `IoU` solo fallback posicional? ¿Cuándo `greedy N=3` de REMIND ablation (`Table VI 90.54% vs 90.35%`) justifica no-Hungarian?
- ¿Semántica señal `ambiguous` (REMIND white box: no comprometer identidad hasta más evidencia) + `provisional` en `IdentidadVista.estado` (`plataforma/sim/whiteboard.py:42`) — extiende hoy `confirmado/posible/desconocido` a `ambiguo/provisional`? ¿Qué consume `DecisionAgentica` (ej `no mover si ambiguous>2`)?
- ¿Cómo preserva `Hungarian` el `Glass-to-Glass <200ms` para `n<=13` (costo `~0.2ms` JS estimado) y compatibilidad `ABORTED overlay-only` (`CONTEXT.md:102`) y `LeakyQueue N=1`?

## Notes

- Skills: `grilling` + `domain-modeling`.
- Requiere `040` y `041` cerrados.
