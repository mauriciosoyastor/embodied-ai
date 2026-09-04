# 0013 — Percepción descriptiva interactiva: AtributoVista (detalle migrado)

**Status**: accepted (2026-09-04, mapa wayfinder #149 oleada 1, Mapa #88 S1). Detalle migrado desde `CONTEXT.md`.

**Decision**: especificación vigente:

- **Whitelist W30**: clases indoor curadas filtradas tras whitelist; mismo modelo base con mayor cobertura; W80 completo reservado outdoor.
- **AtributoVista**: atributos por objeto (track id, clase, conf, bbox, centroide, tamaño, profundidad, color, frame, ts, TTLs por campo); single-writer en memoria con guarda ABORTED dura.
- **Centroide / Tamaño / Color HSV**: derivados CPU sin inferencia (centroide normalizado, tamaño por área, histograma H con máscara).
- **ByteTrack**: tracking ligero con edad máxima, caché LRU de color por solape alto con TTL.
- **Zero-Copy / Thread Pinning**: views por referencia sin re-serializar; hilos ONNX unificados para aislar inferencia.
- **OTel / Prometheus**: métricas de caché, TTLs y latencias glass-to-glass e inferencia.
- **PromptList estática / dinámica / Mapeo en-es-AR**: clases atómicas en inglés para el detector con caché de features congelada; prompts libres por voz con debounce solo si el flag dinámico está activo; diccionario inglés↔español en la capa de voz.

**Consequences**: el glosario conserva los nombres; schemas, TTLs y parámetros viven aquí.
