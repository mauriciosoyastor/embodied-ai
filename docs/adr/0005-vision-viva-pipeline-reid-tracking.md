# ADR 0005 — Pipeline visión viva: ReID híbrido + tracker IoU + histéresis

- **Estado:** aceptado 2026-08-23
- **Contexto:** wayfinder 006 Tickets 031 (`BlazeFace short-range` 0.2 MB 12–22ms) + 032 (`mobilefacenet 128-d` 4.2 MB 30–42ms) + 033 grilling HITL (7 preguntas, `Glass-to-Glass <200ms`, `LeakyQueue N=1` 10Hz, `ABORTED` latch, `COSINE_THRESHOLD 0.42`). Alternativas: embed cada frame vs cada N vs IoU trigger; tracker `KCF`/`ByteTrack` vs `IoU greedy`; threshold binario vs zona gris; histéresis N=3 vs N=5 vs sin; `ABORTED` overlay vs pausa total.
- **Decisión:** ReID híbrido **cada 3 frames + IoU<0.7 trigger**, zona gris **0.42–0.55** (solo `<0.42` a Whiteboard), tracker **IoU greedy `>0.5` + edad 5 (~500ms)**, histéresis **N=3 grace 2**, **10 FPS** con `LeakyQueue`, **ABORTED overlay-only** (no muta Whiteboard), enroll 1 cara / re-id hasta 3.
- **Consecuencias:** `~107ms` Glass-to-Glass medio (<200ms), `<1ms` tracker vs `KCF` 10ms, evita `ByteTrack` Kalman overkill, flicker controlado N=3, Whiteboard no contaminado en gris/`ABORTED`, desbloquea 034 (contrato `identities`) y 035 (prototype badges) y 036 (task migración).
