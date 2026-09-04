# 0012 — Percepción Enriquecida v2: whitelist + canales nuevos (detalle migrado)

**Status**: accepted (2026-09-04, mapa wayfinder #149 oleada 1, Ticket 075). Detalle migrado desde `CONTEXT.md`.

**Decision**: especificación vigente:

- **Whitelist v2**: clases COCO curadas filtradas previo a serialización; fuera de whitelist es log-only. Persona mantiene umbrales estrictos + histéresis; genéricas umbral único.
- **PercepcionVista**: agregado en Whiteboard con TTL por campo, single-writer en memoria, sin transcript; consumido por la decisión agéntica.
- **Postura**: keypoints COCO piggyback en detecciones a baja frecuencia; ABORTED overlay-only.
- **Profundidad**: profundidad relativa desde modelo ligero piggyback, inferencia paralela sin jitter.
- **LeyendaEscena**: caption en español vía cadena VLM con mock final.
- **ABORTED overlay-only v2**: todos los canales solo pintan sin mutar Whiteboard en latch.

**Consequences**: el glosario conserva los nombres; TTLs, umbrales y cadenas de modelos viven aquí.
