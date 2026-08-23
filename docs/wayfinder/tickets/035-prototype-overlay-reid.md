# Ticket 035 — Prototype: Overlay con badge re-id + trayectorias

> Parent: `006-map-vision-viva` · Label: `wayfinder:prototype` · Estado: abierto · Tipo: HITL · Bloqueado por 033

## Question

Throwaway `prototype-vision-viva.html` (no plegar a prod): ¿cómo se **ve y se siente** re-id en vivo?

- Badge `Hola <nombre> ✓` vs `desconocido` sobre `box person` (¿dentro `x,y,w,h` + texto o barra superior `percepcion-panel`?)
- Trayectoria tracking (línea `IoU` / color por `conf` verde `0.42` → amarillo `0.55`)
- Feedback enroll vs re-id (¿mismo `enrollment-panel.js:112` o panel separado?)
- Estado `pending_sync` / `enroll_ack` vs `reid` continuo
- Mostrar `fps/infer_ms` con costo extra detector+embed
- Variante multi-person (2 `person` con 2 badges)

Comparar 2 variantes (badge-box vs chip-list) y elegir una para plegar en Ticket 036. Links a assets, no código prod.

## Blocking

- Bloquea a 036. Bloqueado por 033.

## Resolution

> Estado: **cerrado 2026-08-23** · Prototype HITL UI branch · Artefacto: `plataforma/webcam/frontend/prototype-vision-viva.html` (throwaway, rama `prototype/035-vision-viva` — no plegar a main)

**Artefacto:** `plataforma/webcam/frontend/prototype-vision-viva.html` — UI con 2 variantes switchables `?variant=a|b` + bottom bar, `canvas` mock 640×480, `boxes` + `traj` + `overlayDom`, controles Mock 1/3/oclusión/ABORTED/enroll, `state` surface completo (`last_identidades`, `hyst N=3`, `tracks IoU edad5`, `pending_sync`, `budget 107ms`).

- **Variante A — Badge-box:** badge pegado al box `x,y-18` con `Hola <nombre> ✓ 0.31` verde `<0.42`, `posible <nombre>?` amarillo `0.42–0.55`, `desconocido` gris `>0.55`, borde box colorea igual, trayectoria `IoU` polyline por `track.traj.slice(-12)`, N=3 histéresis visible.
- **Variante B — Chip-list:** barra superior fuera del canvas con chips `Hola/posible/desconocido` + boxes solo `person conf`, trayectorias no dentro del box.

**Veredicto para 036 (plegar a prod):** **Variante A** como default (badge espacialmente ligado a `box person`, embodiment directo, trayectoria visible sin separar contexto). **Variante B** como fallback cuando `identities.length>2` (evita solape badges) o para `percepcion-panel` chip compacto. ABORTED overlay-only verificado (Whiteboard no muta), oclusión `face null` blockReason amarillo, `pending_sync` flush simulado.

**Reglas prototype aplicadas:** throwaway desde día 1, trivial `double-click prototype-vision-viva.html` o `vite` serve, sin persistencia (solo `gallerySeed` memoria), skip polish, state surfaceado en `state` JSON cada acción, sin tests.

**Siguiente:** 036 plegará badge A (colores por `estado`) + `overlay.js` `drawBoxes` extendido con `identities`, `enrollment-panel.js` loop híbrido, `WhiteboardState.last_identidades`.

<!-- context pointer para mapa -->
