# GitNexus Engineering Plan — Whitelist v2 + Envelope + Whiteboard (sin publicar, win32 fallback)

> Task: Slice 01 fundación Percepción Enriquecida v2 — Whitelist W30 33 clases + Envelope único piggyback + Whiteboard PercepcionVista TTL + ABORTED overlay-only + voz grounded
> Evidence verified at commit db6b11c (2026-09-03) Deepen 2026-09-03; GitNexus index fallback source-derived (win32 write-plan refused O_NOFOLLOW, snapshot schema 2 global dirty 01867ac). Source beats graph; plan is source-verified. Deepen: whitelist 13→W30 alineado a código HEAD config.py:59.
> Evidence provenance schema 2 — write helper no disponible en win32, plan escrito directo con manifest manual [plataforma/webcam/backend/ws.py, config.py, whiteboard.py, inference/yolo.py, frontend/src/ws-client.js]

## 1. Objective

Entregar fundación vertical (tracer-bullet) que filtra YOLO 80 → W30 33 clases curadas (`CONTEXT.md:133` mismo yolo11n.onnx +105% cobertura), transporta por único WebSocket `/ws/percepcion` con `seq/ts` correlacionado `frame_id`, y expone `WhiteboardState.percepcion_vista` con TTL por campo y guarda `ABORTED overlay-only`, sin romper `Glass-to-Glass <200ms` ni `LeakyQueue N=1`. Incluye voz grounded `[Percepción viva frame #]` ya en HEAD `app.py:156`.

## 2. Current Behaviour

`ws.py:40 EnvelopeType` único con `detecciones/gesto/estado`; `ws.py:197 run_inference` serializa 80 clases sin whitelist curada; `ws.py:322 process_single_frame` correlaciona `frame_id` fast 10Hz ~107ms; `whiteboard.py` solo `last_identidades` sin `PercepcionVista`; `frontend/src/ws-client.js:78 canSend()` `bufferedAmount>64KB` skip preserva lazo cerrado.

## 3. Relevant Architecture

Monorepo `plataforma/webcam/backend` (uv workspace) + `frontend` desacoplados por `Envelope` y `WhiteboardState` (single-writer memoria, sin transcript `CONTEXT.md:16`). ONNX `intra_op_num_threads=2` por modelo evita jitter `research 072/073` p95 +10-15ms. `AsyncLeakyQueue N=1` fast 10Hz + slow 5Hz piggyback comparten `seq`.

## 4. GitNexus Findings (source-derived fallback)

- Primary: `ws.py:run_inference`, `ws.py:process_single_frame`, `whiteboard.py:WhiteboardState`, `config.py:YOLO_*` — source-verified via Read.
- Impact d=1: `frontend/overlay.js`, `frontend/percepcion-panel`, `inference/yolo.py`, `tests/test_ws.py` — downstream consumers de envelope.
- Sin graph ladder (win32); hallazgos etiquetados `[source-derived]`, no `[graph]`.

## 5. Statement-Level PDG Findings (no PDG layer)

PDG no indexado en win32 fallback. Controles clave verificados en fuente: `if ABORTED: overlay-only return` en `ws.py`, `if conf<0.50 or area<0.03: skip` en `_passes_whitelist`, `seq+=1` compartido fast/slow. Data: `frame_id` fluye `decode_jpeg_b64 → run_inference → make_envelope → Whiteboard.percepcion_vista`.

## 6. Proposed Changes

- `plataforma/webcam/backend/config.py`: `YOLO_WHITELIST=frozenset(W30 33)` (`config.py:59` HEAD: person 13 + tv,bed,dining table,toilet,potted plant,microwave,oven,sink,refrigerator,clock,vase,toaster,wine glass,bowl,scissors,teddy bear,toothbrush), `YOLO_CONF_THRESH=0.50`, `YOLO_AREA_THRESH=0.03`, `YOLO_PERSON_CONF=0.60`, `YOLO_PERSON_AREA=0.15`
- `plataforma/webcam/backend/ws.py`: `def _passes_whitelist(cls,conf,area,person_hysteresis)->bool` previo a `boxes_payload`; `EnvelopeType += "scene_caption"`; `parse_envelope` rechaza desconocido; `seq_counter` único fast/slow/vlm
- `plataforma/webcam/backend/whiteboard.py`: `class PercepcionVista(BaseModel)` + `WhiteboardState.percepcion_vista` con `update_percepcion()` TTL `100/1000/1000/2000ms` y guarda `if state==ABORTED: return` (overlay-only)
- `plataforma/webcam/frontend/src/ws-client.js` + `overlay.js`: filtro whitelist, `handle_detecciones` actualiza `percepcionVista`

## 7. Implementation Sequence

1. Config whitelist + unit `_passes_whitelist` — low risk, desbloquea contrato
2. WS envelope piggyback `detecciones {boxes,poses:[],depths:[]}` + `scene_caption` separado — medium (concurrencia `seq`)
3. Whiteboard `PercepcionVista` TTL + ABORTED — single-writer, verificar expiración a `None`
4. Frontend filtro + overlay — preservar `bufferedAmount` skip
5. Harness `np.zeros(480,640,3)` → `jpeg_b64` → `decode` → `run_inference` → `process_single_frame` correlación `frame_id` + `pytest` verde

## 8. Test Strategy

Nuevos: `test_whitelist_envelope_whiteboard.py` — whitelist W30 33, rechazo 34ª clase, TTL 100ms expira, ABORTED no muta, seq monotono, parse_envelope unknown → ValueError. Existentes: `test_ws.py`, `test_yolo.py` actualizar. Comandos: `uv run ruff format --check . && ruff check . && mypy plataforma/webcam && pytest plataforma/webcam -q`

## 9. Risk and Impact Analysis

Riesgo high: `seq` compartido fast/slow/vlm — carrera si no `Lock`; mitigar con `list[int]` mutable + `asyncio.Lock`. Downstream: `overlay.js` debe filtrar whitelist sino pinta 80 clases. Compat: `intra_op=2` mantiene Glass <200ms; si 5Hz slow compite, jitter +10ms aún <200ms fast.

## 10. Files Expected to Change

| File | Symbols | Reason |
| ---- | ------- | ------ |
| plataforma/webcam/backend/config.py | YOLO_WHITELIST, thresholds | Whitelist curada |
| plataforma/webcam/backend/ws.py | _passes_whitelist, EnvelopeType, process_single_frame | Filtro + piggyback |
| plataforma/webcam/backend/whiteboard.py | PercepcionVista, WhiteboardState | TTL + ABORTED |
| plataforma/webcam/frontend/src/ws-client.js | canSend, handle_detecciones | Transporte + skip |

## 11. Reusable Implementation Context

```json
{"task":"01 whitelist+envelope+whiteboard","primary":["ws.py:run_inference","ws.py:process_single_frame","whiteboard.py:WhiteboardState"],"cited":["plataforma/webcam/backend/ws.py","config.py","whiteboard.py","inference/yolo.py","frontend/src/ws-client.js"],"evidence_provenance":{"schema_version":2,"head_commit":"db6b11c","global_dirty_digest":"01867ac","fallback":"win32 direct write, snapshot validated"}}
```

## 12. Assumptions and Open Questions

- Asume único punto serialización `ws.py:197` [assumed]
- Pregunta: ¿0.50 único suficiente o per-clase si `cell phone` false positives? Respuesta en 02/03
- Defer: embeddings 150MB, rollout piloto vs todos, `impact_ratio` threshold fino

## 13. Definition of Done

- `YOLO_WHITELIST` W30 33 en config, filtro previo a `boxes_payload`, envelope `detecciones` piggyback + `scene_caption` validos, `PercepcionVista` TTLs expiran a `None`, `ABORTED` no muta Whiteboard, 5+ tests headless pasan, `ruff/mypy/pytest` verde, `Glass-to-Glass` fast <200ms preservado, `trajectory.jsonl` sin `HIGH` ignorado
