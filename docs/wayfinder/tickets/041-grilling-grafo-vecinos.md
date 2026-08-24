# Ticket 041 — Grilling: Grafo vecinos para indoor estático

> Parent: `007-map-memoria-objetos.md` · Label: `wayfinder:grilling` · Estado: **cerrado 2026-08-24** · Tipo: HITL (grilling + domain-modeling) · Claim: `mauri`

## Resolution

**Decidido con el usuario 2026-08-24 (Q1-Q5 aprobados A):**

- **Q1:** co-ocurrencia = `co-visible D5 12 clases` episodio `debounce 3 / α0.5 / max20`.
- **Q2:** defaults REMIND `Δ+0.20/Δ-0.10 quality0.35 rescue0.60 veto≤3/0.60` + `min_hits2 ratio0.25`.
- **Q3:** `person` excluido del grafo objetos estáticos.
- **Q4:** solo `Co-occurrence` v1, `Distance Graph` fog.
- **Q5:** client-side `Map` volátil (`ABORTED overlay-only`).

Términos en `CONTEXT.md:117` (`Grafo de Vecinos`, `Contexto Vecinal`).

## Question

Con inputs de `038` (neighbor graphs REMIND) y `039` (budget), decidir:

- ¿Definimos co-ocurrencia como `co-visible en mismo frame D5` (`ws.py:197` boxes `Whitelist v2`) sin pose/depth, acumulando `episode counts + exponentially-weighted frequency kernel per edge` por objeto `o`?
- ¿Umbrales para activar `context bonus delta+ / penal delta-` y `veto contextual` (REMIND Table VIII) escalados por cobertura/madurez/densidad? ¿Cómo evitar falsos vecinos con `YOLO conf>0.50 area>3%`?
- ¿Neighbor set incluye `person` como ancla o solo objetos estáticos (`chair, couch, laptop...`)?
- Modelar término `NeighborSet`/`Veto` en `CONTEXT.md` y si vive client-side (privacidad) o `ws.py` server-side.

## Notes

- Skills: `grilling` + `domain-modeling`.
- Depende de `037`/`038` cerrados — no adivinar `delta` sin research.
