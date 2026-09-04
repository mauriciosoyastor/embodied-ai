# 0014 — Arquitectura productiva: Leaky + ReID + Bridge + WebRTC (detalle migrado)

**Status**: accepted (2026-09-04, mapa wayfinder #149 oleada resto, Mapa 007). Detalle migrado desde `CONTEXT.md`.

**Decision**: especificación vigente:

- **Bypass Galería**: rama de persistencia fuera de la cola de frames con canal síncrono, lock, escritura atómica y broadcast; evita pérdida durante drops.
- **Single-Writer proyección**: las identidades en Whiteboard son proyección de lectura para overlay y personalización, sin afectar el bucle reactivo; ABORTED no muta.
- **GzAdapter agnóstico**: adapter de simulador intercambiable (mock, MuJoCo, Gazebo) sin cambios en el llamador.
- **selectTransport fallback**: probe de WebRTC con fallback a WS según el entorno.
- **Warmup ONNX**: compilación anticipada de grafos para amortizar cold-start.
- **Zero-Copy memoryview**: views sin copia inter-proceso hacia arrays.
- **Dropped frames**: contador de frames descartados por la cola, expuesto en métricas.
- **threshold_per_person**: umbral por persona opcional para debug, sin romper el wire.

**Consequences**: el glosario conserva los nombres; parámetros y rutas viven aquí.
