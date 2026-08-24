# Ticket 040 — Grilling: Dual-bank adaptada a webcam — prototipos + política update

> Parent: `007-map-memoria-objetos.md` · Label: `wayfinder:grilling` · Estado: **cerrado 2026-08-24** · Tipo: HITL (grilling + domain-modeling) · Claim: `mauri`

## Resolution

**Decidido con el usuario 2026-08-24 (Q1-Q5 aprobados):**

- **Q1 Bancas separadas A:** `person` (`thr 0.42` facial) y `objetos` (`thr 0.92` REMIND) aisladas — previene falsos positivos OOD sin tocar ReID facial validado (`006`).
- **Q2 Capacidad B 8/8:** `work 8 + stable 8` (16×128×4B ≈105KB para 13 objetos, dentro de `localStorage 5MB`), `promote 5` `count_cap 10` `dup 0.92 merge 0.90 novel 0.78`.
- **Q3 Gating:** `confirmado <0.42 N=3 → STRONG full | posible 0.42-0.55 → AMBIGUOUS EMA*0.2 | desconocido >0.55 → WEAK skip` — protege drift.
- **Q4 Parts/BG A:** `false` v1 solo `appearance global w 1.0` — evita `+128ms`, mantiene `71/92ms`.
- **Q5 max_misses:** `10` (1000ms) objetos vs `5` person.

Términos cristalizados en `CONTEXT.md:116` (`Banca Dual`, `Prototipo`, `EMA`, `Gating`, `Lifecycle`, `Parts/BG`). `ABORTED overlay-only` y `LeakyQueue N=1` preservados.

## Question

Con inputs de `037` (dual-bank REMIND) y `039` (proxy features), decidir para objetos `Whitelist v2`:

- ¿Cuántos prototipos por objeto (REMIND usa `multi-prototype`, ¿k=3-5?) y separación `appearance vs part vs background` adaptada a `mobilefacenet 128-d` genérico?
- ¿Política `insert` (nuevo cluster) vs `EMA promote` (`alpha` base vs `alpha reducido` en `AMBIGUOUS`) y `WEAK = no update` mapeada a tu `Histéresis ReID N=3 grace2` (`CONTEXT.md:100`) + `Tracker IoU edad 5` (`CONTEXT.md:101`)?
- ¿Bancas separadas para `person` (facial ya existente) vs genéricos, o una sola? ¿Persistencia `localStorage + identities.json` con LRU cap `min(N,5)` (`CONTEXT.md:94`)?
- HITL: validar `COSINE_THRESHOLD=0.42` + gray `0.42-0.55` se mantienen o se recalibran por clase (ej `chair` más similar que `bottle`).

Bloquea a `043`/`044` hasta cerrar.

## Notes

- Skills: `grilling` + `domain-modeling` — afinar términos `Banca`, `Prototipo`, `Insert`, `EMA`, `Gating` en `CONTEXT.md`.
- Respeta `ABORTED overlay-only` y `single-writer memoria` (`CONTEXT.md:102`).
