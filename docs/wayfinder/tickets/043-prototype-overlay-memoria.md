# Ticket 043 — Prototype: Overlay white-ambiguous + badge por estado objeto

> Parent: `007-map-memoria-objetos.md` · Label: `wayfinder:prototype` · Estado: **cerrado 2026-08-24** · Tipo: HITL (prototype) · Claim: `mauri`

## Resolution

**Throwaway producido 2026-08-24 — rama `prototype/043-memoria-objetos` (no plegado):**

- **Asset:** `prototype-memoria-objetos.html` (`?variant=a|b` ya soportado) — mock `Whitelist 12` con 5 estados 042: `confirmado verde sólido ✓ / posible amarillo / ambiguo blanco dashed ? (caja blanca REMIND EMA*0.2) / provisional amarillo tenue dashed ⋯ TENTATIVE / desconocido gris`.
- **Variante A badge-box** (recomendada, hereda 035) vs **B chip-list** top para `>2 objetos` — toggle `btn-a/b` en header. Traza `traj 12` (`enrollment-panel.js:371`) mock.
- **Veredicto:** Confirmar **Variante A** para prod — badge ligado a box, verde/amarillo/blanco/gris por `estado`, `ambiguo` blanco punteado con `?` centro, tooltip `Δ+0.20 rescue` `TTL 10` (041/042). B fallback si `n>4` por clase.

## Question

Throwaway `prototype-memoria-objetos.html` (no plegar a prod, branch `prototype/043-memoria-objetos`): ¿cómo se ve detection en `white` (`ambiguous` REMIND) vs `confirmado` verde / `posible` amarillo / `desconocido` gris para objetos `Whitelist v2` (`chair`, `couch`...)? Evaluar:

- Badge ligado a box (Variante A `docs/wayfinder/tickets/035-prototype-overlay-reid.md` ganadora) vs chip-list B para >2 objetos.
- Visual memoria prototypes (mini traza como `tracker traj 12` en `enrollment-panel.js:372`) + counter `prototipos/object`.
- Feedback `ambiguous` (ej borde blanco punteado + `?`) vs `provisional` (amarillo tenue) para `DecisionAgentica` no actúe.
- Link asset prototype y veredicto grilling para pliegue futuro en `overlay.js`.

## Notes

- Skill: `prototype`.
- Bloom después de `040-042` pero puede esbozarse con mocks antes.
