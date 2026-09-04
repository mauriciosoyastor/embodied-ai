# 0011 — Visión viva: ReID + Tracking per-frame (detalle migrado del glosario)

**Status**: accepted (2026-09-04, mapa wayfinder #149 oleada 1, Ticket 033). Detalle migrado desde `CONTEXT.md`.

**Decision**: especificación vigente de re-identificación y tracking:

- **ReID híbrido per-frame**: detección de persona → detector facial de corto alcance → embedding facial cada 3 frames, más trigger inmediato si el solape con el bbox previo cae bajo umbral. Balancea latencia glass-to-glass contra reactividad.
- **Zona gris de coseno**: banda donde el match es solo overlay informativo sin promover a identidad confirmada; por encima es desconocido.
- **Histéresis ReID**: la identidad confirmada exige matches consecutivos con reseteo ante fallos; evita flicker.
- **Tracker IoU greedy con edad**: matching greedy por área para persistir id ante flicker del detector; drop tras N frames sin match.
- **ABORTED overlay-only**: en latch ABORTED se sigue pintando pero sin mutar Whiteboard ni alimentar decisión.
- **Multi-person viva**: enroll bloqueado con 2+ personas; re-id hasta 3 caras simultáneas.
- **Budget visión viva**: reparto de latencia por etapa dentro del presupuesto glass-to-glass; cola N=1 y skip por buffer preservados.
- **IdentidadVista / Whiteboard last_identidades**: vista per-frame con estado confirmado/posible/desconocido; proyección de solo-lectura en Whiteboard para overlay y personalización (no actuación).

**Consequences**: parámetros (umbrales, conteos, latencias) viven aquí; el glosario conserva el vocabulario.
