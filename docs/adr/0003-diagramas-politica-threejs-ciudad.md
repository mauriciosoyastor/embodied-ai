# 0003 — Política de diagramas: MDA prohibido, bocetos + ciudad Three.js viva

**Status**: accepted (2026-08-21, mapa wayfinder #60 D5)

## Contexto

Uncle Bob: el código es el único plano detallado; los diagramas son bocetos efímeros en pizarra. El repo ya grita dominio con 3 zones ciudad (`centro`/`industrial`/`suburbios`/`outskirts`, ver `docs/architecture/architecture-policy.json`).

## Decisión

1. **Prohibir MDA/BDUF**: ningún diagrama UML/C4 completo antes de programar. No hay herramienta CASE como fuente de verdad.
2. **C4/UML solo como boceto**: permitido como boceto pre-implementación en `docs/adr/` o PR description, nunca como artefacto vivo. Se archiva y no se mantiene.
3. **Ciudad Three.js como única visualización viva**: `docs/architecture/city-model.html` (Three.js r155 ortographic + BoxGeometry + lines, ~600KB) + `dependency-graph.json` generados por CI (`import-linter` + `dependency-cruiser` → `scripts/gen-city-grafo.js`). Es el único visor que refleja el estado real del código.
4. **CI como guardián**: job `architecture` falla si `center→periphery` (calle roja) — ver `architecture-policy.json:rules.forbidden`.

## Consecuencias

- `C4` no se versiona como fuente de verdad; la ciudad sí (CI).
- Nuevo diagrama debe justificarse en ADR y marcarse "boceto — no mantener".
- `CONTEXT.md` añade `Arquitectura Visual = representación type-aware de dependencias en 3D`.
