# Ticket 026 — Prototype: UI hibrido + purga

> Label: `wayfinder:prototype` · Parent: `004-map-enrollment-hibrido.md` · Estado: cerrado · Resolución: 2026-08-23 · Reclamado por Muse Spark · HITL

## Question

¿Como se ve sync hibrido? Badge `local` vs `server synced`, galeria con origen, boton `Borrar todos` con confirm que emite `purge` y limpia ambos. Throwaway `prototype-enrollment-hibrido.html` con 2 variantes (tabla vs chips) linkeado. HITL con `prototype` + `domain-modeling`. Bloqueado por 024,025.

## Resolución

**Prototype throwaway:** `plataforma/webcam/frontend/prototype-enrollment-hibrido.html` — doble-click para abrir, `?variant=table|chips` + floating bar. Estado en `state` JSON tras cada acción.

- **Variante A Tabla:** filas `id/nombre/count/origen/sync/updatedAt` con badges `server synced` vs `local • pending` — scannable para debug, preferida para `Not yet specified` de LRU futuro.
- **Variante B Chips:** galería `Mauri #a1b2` con `count` + origen — más visual para `percepcion-panel` en `controlroom` dash.

**Flujos prototipados:**
- `Enrolar Mauri` → `enroll_sync` (WS OPEN → `server synced`, CLOSED → `local • pending` + `pending_sync` 1) + transición verde badge
- `Simular reconexión` → vacía `pending_sync` → `enroll_ack` toast
- `Borrar todos` → confirm → `purge {all:true}` broadcast → limpia ambas fuentes + `purge_ack` toast

**Veredicto para Ticket 027:** Elegida **variante A Tabla** para producción (más explícita para `count`/`updatedAt`/`origin`), badge `pending_sync` en header + galería chips opcional en `hud` variant. Asset capturado en branch `prototype/026-hibrido` (throwaway, no mergear a `main`).

**Captura:** throwaway branch `prototype/026-hibrido` + link `prototype-enrollment-hibrido.html` (double-click, sin `npm`).

**Desbloquea:** 027
