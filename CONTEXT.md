# Glosario de dominio — Embodied AI

Glosario y nada más: sin specs, sin implementación. Los términos se agregan a medida que se resuelven en las sesiones.

## Términos del proyecto

- **Roadmap de aprendizaje ejecutable**: el destino de este esfuerzo. Un plan, en español, de qué construir y en qué orden para aprender Embodied AI/AIoT, donde cada fase cierra con un **hito** (proyecto mínimo que corre y se entiende). El mapa de wayfinder **decide**, no ejecuta.
- **Fase 0 — Fundamentos**: fase de prerrequisitos previa a la guía. Cubre Python básico, git/GitHub, Linux básico y Docker.
- **Hito**: proyecto mínimo que corre y el aprendiz lo entiende. Criterio de finalización de una fase.
- **Destino (wayfinder)**: qué significa llegar al final del mapa. Fija el alcance de todo el esfuerzo.

## Términos del dominio técnico (Guía Maestra)

- **Orquestador cognitivo**: el "cerebro" local del agente; gestiona estados y coordina modelos.
- **StateGraph**: estructura para transiciones lógicas de estado del agente.
- **Whiteboard / WhiteboardState**: mecanismo de intercambio de contexto entre modelos; en sim `WhiteboardState(BaseModel)` dentro de `MissionState` (`ctx.state.whiteboard`) con `estado, frame_id, last_gesto, last_observation, last_decision, metrics`, **sin `transcript`** (voz queda en `plataforma/webcam`), single-writer memoria, `Reducer` en fog.
- **Whiteboard**: mecanismo de intercambio de contexto entre modelos. (ver WhiteboardState)
- **Reducer**: consolidación de estados del agente.
- **Grammar-Constrained Decoding**: restricción de la salida del LLM a un esquema estricto (ej. Pydantic).
- **Glass-to-Glass Latency**: tiempo total desde la captura del fotón hasta el renderizado del píxel procesado. Meta: < 200ms.
- **Leaky Queue (N=1)**: procesamiento "solo frame más reciente" para evitar lag acumulado.
- **MOG2**: algoritmo de sustracción de fondo basado en mezclas de gaussianas.
- **CLAHE**: Contrast Limited Adaptive Histogram Equalization; mejora de contraste para visión nocturna.
- **KCF**: Kernelized Correlation Filters; tracking visual para persistencia entre frames de inferencia.
- **WebRTC**: protocolo de streaming de baja latencia con control de congestión nativo.
- **Hysteresis (Histéresis)**: retardo temporal que impide oscilación rápida de estados; un evento solo se confirma si persiste durante T_onset.
- **IoU**: Intersection over Union; métrica de precisión de localización.
- **Inference Latency**: tiempo de tránsito en GPU/NPU.
- **Deadman's Switch**: interruptor de seguridad que requiere señal activa continua; su ausencia detiene toda actuación física.
- **Heartbeat**: señal de baja frecuencia (1-5Hz) que confirma la integridad del enlace entre el orquestador de IA y el controlador de vuelo (FCU).
- **Geofencing**: envolvente de seguridad lógica basada en coordenadas para prevenir la fuga del agente.
- **Stick Override**: prioridad de interrupción del control manual sobre los comandos de la IA.
- **Failsafe**: respuesta automática segura ante falla del enlace (ej. aterrizaje inmediato).
- **Offboard mode**: modo de vuelo donde la IA manda comandos al FCU vía MAVSDK.
- **Safety Envelope**: límites físicos (torque, velocidad, aceleración) impuestos en el firmware que la IA no puede vulnerar.
- **ROSClaw**: capa de puente de baja latencia entre la lógica cognitiva y el torque físico.

## Términos del dominio de la plataforma (`plataforma/`)

- **Monorepo modular desacoplado**: arquitectura del repo donde `plataforma/` se divide en subsistemas autocontenidos (`backend`, `frontend`, `sim`) con sus propios runtimes y sin dependencias cruzadas; comparten un solo repositorio git.
- **Workspace de uv**: agrupación de paquetes Python (backend + sim) bajo un mismo proyecto `uv` que comparten lockfile y caché pero mantienen entornos aislados.
- **Path filtering**: técnica de CI que dispara jobs solo cuando cambian archivos de una ruta (ej. `plataforma/frontend/`), evitando instalar cadenas de dependencias pesadas cuando se modifican otros directorios.
- **Contrato de datos (sim → backend)**: interfaz explícita (Pydantic/OpenAPI) que define cómo el simulador expone estado y recibe comandos, desacoplando los subsistemas.

## Términos del contrato de simulación (Bridge/Adapter)

- **Bridge/Adapter**: patrón que abstrae el simulador detrás de una interfaz común (Protocol), para que MuJoCo hoy y Gazebo/PX4 mañana se conecten igual.
- **SimObservation**: estado del mundo que todo sim expone — pose `(x, y, yaw)`, twist `(v_x, v_y, omega_z)`, timestamp, frame id y sensores opcionales. Unidades SI y world frame siempre; cada adapter normaliza.
- **CmdVel**: comando de velocidad `(v_x, omega_z)` con clamp por rango; la conversión a velocidades de rueda es interna a cada adapter.
- **SimMetrics**: métricas del motor de simulación (steps/s, wall time, dt real vs sim) expuestas aparte del estado; las consume el recomendador, no la FSM.
- **MujocoAdapter**: adapter concreto sobre MuJoCo con un MJCF propio estilo TurtleBot (dos ruedas con actuadores `velocity` + caster); contiene la cinemática diferencial `(v_x, omega_z) → (ω_L, ω_R)`.
- **FakeAdapter**: adapter sin simulador real para tests y demos; respeta el mismo Protocol.

## Términos del contrato de percepción → orquestador (D5/D6)

- **Envelope WebSocket**: wrapper común `{ type, seq, ts, payload }` sobre un único WebSocket `/ws/percepcion`; `seq` detecta drops, `ts` es Unix ms, `type` discrimina `frame|detecciones|gesto|estado`.
- **GestoReconocido**: evento de dominio `{ label: open_palm|fist|thumbs_up|none, conf, frame_id, ts }` que la FSM consume vía `handle_gesto`; desacopla MediaPipe del orquestador.
- **evento_observacion**: telemetría informativa `{ frame_id, cls, conf, area }` emitida cuando YOLO detecta `person` con `conf>0.6` y `area>15%`; no dispara transiciones de la FSM.
- **ABORTED latch**: estado `ABORTED` enclavado que ignora todo gesto hasta `reset()` explícito; prioridad absoluta sobre `RUNNING`/`PAUSED`.
- **handle_gesto**: función pura `Estado = handle_gesto(GestoReconocido)` con histéresis N=5 frames consecutivos (`conf≥0.7`, ~500 ms @10 Hz); permite tests headless sin cámara.
- **SIM_IDLE / SIM_RUNNING / SIM_PAUSED / SIM_ABORTED**: estados del StateGraph sim (`plataforma/sim`) espejo de `MissionFSM`; `SIM_ABORTED` es `End[data=ABORTED]` terminal en `pydantic-graph` hasta `reset()` externo. Histéresis N=5 idéntica, `none`/`<0.7`=no-op, `TickNode` avanza `frame_id` a 10Hz.
- **TickNode / DecisionNode / ActNode**: nodos `pydantic-graph` `BaseNode[StateT,DepsT,RunEndT]` — `TickNode` avanza sim 100ms, `DecisionNode` (solo si `SIM_RUNNING`) invoca `Agent[HardwareContext,DecisionAgentica]` (Muse Spark/TestModel) → `CmdVel`, `ActNode` hace `FakeAdapter.send_cmd_vel`+`step`.

## Términos del pipeline de agentes (workflow AFK)

- **Pipeline AFK**: automatización que resuelve un issue hasta PR + CI + review sin intervención humana; el humano solo hace el merge final.
- **Agente coder**: agente que implementa el código del issue en una rama y abre el PR. Modelo: `sonnet`.
- **Agente reviewer (red-team)**: agente que revisa el diff del PR con foco en seguridad, consistencia y adherencia al issue; aprueba o pide cambios. Modelo: `opus`.
- **Iteración (loop N=3)**: cada ciclo del reviewer pidiendo cambios. Contador en el body del PR; al llegar a N=3 el issue pasa a `needs-human-attention`.
- **Anti-bucle**: mecanismo por el cual los eventos disparados por `GITHUB_TOKEN` no re-disparan workflows; se usa token de GitHub App para que el CI corra sobre PRs del agente.
- **Installation access token**: token de una GitHub App (expira en 1h) que actúa en nombre de la app; otorga permisos acotados y re-dispara workflows.
- **Labels del ciclo**: `ready-for-agent` (disparador) → `agent:in-progress` (trabajando) → `needs-human-attention` (loop agotado) | `APPROVE` → merge humano.
- **Rama de agente**: rama `agent/<issue-number>-<slug>` creada por el coder; el reviewer solo procesa PRs con head `agent/`.

## Términos de interacción voz y registro facial (detalle en ADR-0010)

- **Push-to-talk**: micrófono por pulsación mantenida, sin escucha continua.
- **STT (Speech-to-Text)**: audio→texto en es-AR, híbrido con servidor.
- **TTS (Text-to-Speech)**: síntesis de voz sin salir del frontend.
- **Transcript**: par usuario→LLM y LLM→usuario para telemetría (no vive en Whiteboard).
- **Enrollment facial**: detección → embedding → asociación a nombre con gesto confirmado.
- **Embedding facial**: vector de identidad; nunca imagen cruda.
- **Registro (face)**: persistencia de embedding + nombre para re-identificar.
- **Muse Spark 1.2 free**: LLM por defecto vía API OpenAI-compatible.
- **Proveedor LLM gratuito**: chat completions sin coste, hospedado o local.
- **Free-tier hospedado**: cuota sin tarjeta con base URL propia.
- **Fallback local**: respaldo offline cuando hosted falla.
- **Cadena de fallback**: orden hosted → local → mock.
- **EnrollSync / EnrollAck**: sincronización de enrolamientos con ack e idempotencia.
- **Purge / PurgeAck**: limpieza broadcast con ack por cliente.
- **PendingSync**: cola offline vaciada al reconectar.
- **Hidratación híbrida**: snapshot base por HTTP, deltas por WS.
- **Bypass de Leaky Queue**: rama dedicada fuera de la cola de frames.
- **IdentitiesStore**: persistencia de identidades con promedio móvil.

## Términos de visión viva (detalle en ADR-0011)

- **ReID híbrido per-frame**: embedding periódico más trigger por solape bajo.
- **Zona gris coseno**: banda de match solo-informativo sin promover.
- **Histéresis ReID N=3**: identidad confirmada tras matches consecutivos.
- **Tracker IoU greedy + edad 5**: persistencia de id ante flicker.
- **ABORTED overlay-only**: pintar sin mutar en latch.
- **Multi-person viva**: enroll unitario, re-id multi-cara.
- **Budget visión viva**: reparto de latencia dentro del presupuesto.
- **IdentidadVista**: vista per-frame con estado confirmado/posible/desconocido.
- **Whiteboard last_identidades**: proyección de solo-lectura para overlay y personalización.

## Términos de Percepción Enriquecida v2 (detalle en ADR-0012)

- **Whitelist v2**: clases curadas filtradas previo a serialización; persona estricta, genéricas umbral único.
- **PercepcionVista**: agregado en Whiteboard con TTL por campo, sin transcript.
- **Postura**: keypoints piggyback en detecciones; ABORTED overlay-only.
- **Profundidad**: profundidad relativa piggyback en paralelo.
- **LeyendaEscena**: caption vía cadena VLM con mock final.
- **ABORTED overlay-only v2**: canales solo pintan sin mutar en latch.

## Términos de Memoria de Objetos (REMIND destilado) — Ticket 040

- **Banca Dual work/stable**: por objeto `Whitelist v2` mantiene `work[8] + stable[8]` prototipos `128-d` `ℓ2` (max 16) — `work` se actualiza, `stable` se promueve tras `promote_hits 5`. Bancas separadas: `person` (`thr 0.42`, `ABORTED` ReID N=3) vs `objetos` (`thr 0.92`, `max_misses 10`) para aislar OOD `mobilefacenet` sin degradar facial.
- **Prototipo**: embedding `128-d` representante de una vista; `insert` si `s_max<0.78` (novel) crea nuevo, `dup s_max>0.92` dispara `EMA`, `merge >0.90` fusiona redundantes, `promote` copia a `stable` tras 5 hits, `count_cap 10` limita historial.
- **EMA (Exponential Moving Average)**: `ê ← normalize((1-α)ê + αx)` con `α 0.02-0.08` gated por `s_max` (más similar → mayor `α`). En `AMBIGUOUS` escala `×0.2` (`α 0.004-0.016`) para no corromper con evidencia dudosa.
- **Gating STRONG/AMBIGUOUS/WEAK**: mapeo a histéresis `Zonas coseno`: `confirmado <0.42 N=3 → STRONG full (insert/merge/promote/EMA)`, `posible 0.42-0.55 → AMBIGUOUS EMA*0.2 only`, `desconocido >0.55 → WEAK skip (no update)`. `provisional`/`ambiguous` blancos overlay no mutan `WhiteboardState` en `ABORTED` latch.
- **Lifecycle objetos**: `NEW → TENTATIVE → CONFIRMED → INACTIVE`; `confirm_hits 2`, `max_misses 10` (1000ms @10Hz) para estáticos vs `5` para `person` (500ms). `remove false`, TTL 0 — memoria volátil.
- **Parts/BG desactivados v1**: `parts.enabled false` y `bg.enabled false` para objetos — solo canal `appearance global` (`w 1.0`); evita `+128ms` de 4 crops `56×56` y mantiene `budget 71/92ms` dentro de `Glass-to-Glass <200ms`.
- **Grafo de Vecinos (NeighborGraph)**: `Map<objId → NeighborEdge{o→o' cooc_count, weight, episode}>` dirigido cross-class (sin `person`), co-ocurrencia = `co-visible mismo frame D5 Whitelist 12` con `debounce 3 / force 3 / α0.5 / max 20 / jaccard 0.85`; weight kernel `p=(cAB+α)/(cA+αV)` `α0.5`; solo contexto, sin `Distance Graph` v1.
- **Contexto Vecinal (NeighborSets)**: bonus `Δ+0.20` / penal `Δ-0.10` capped `score_assign = s_sim + Δ` sobre `cost matrix` pre-Hungarian, gate `quality≥0.35 rescue≥0.60` (solo `WEAK/AMBIGUOUS`), veto `|supported|≤3 quality≥0.60 pruning≥0.35 class≥0.50` anula `o∉supported`; quality `0.25best+0.20cov+0.15mad+0.10dens+0.15size+0.15pruning`; `min_hits 2 ratio 0.25` evita falsos vecinos `conf>0.50`.
- **Hungarian híbrido**: `Hungarian per-class locks 0.90/0.10 dummies 0.05→0.72` primary para objetos, fallback `IoU greedy >0.5 edad 5` si `quality<0.35` o `s_sim<0.60`; costo <0.1ms `n≤13` compatible `Glass-to-Glass 71/92ms`.
- **Ambiguo / Provisional**: `IdentidadVista.estado` `ambiguo` (gap<0.03 + quality bajo → caja blanca EMA*0.2 sin promo, no a Whiteboard `confirmado`) y `provisional` (TENTATIVE `confirm 2` antes de crear) extienden `confirmado|posible|desconocido`; `DecisionAgentica` espera si `ambiguo>2`.
- **TTL vecino**: expiración episódica `ttl_episodes≈10` sobre `NeighborEdge.last_seen_episode` para descartar aristas fugaces de giros rápidos; no existe en REMIND (`decay 1.0`), mejora destilada para evitar bias.

## Términos de Percepción descriptiva interactiva (detalle en ADR-0013)

- **Whitelist W30**: clases indoor curadas con mayor cobertura; W80 reservado outdoor.
- **AtributoVista**: atributos por objeto con TTLs por campo y guarda ABORTED.
- **Centroide**: centro normalizado para ordenamiento espacial.
- **Tamaño**: buckets por área, sin inferencia.
- **Color HSV**: histograma con máscara y fallback a color VLM.
- **ByteTrack**: tracking ligero con caché de color.
- **Zero-Copy**: views por referencia sin re-serializar.
- **Thread Pinning**: hilos de inferencia unificados y aislados.
- **OTel / Prometheus**: métricas de caché, TTLs y latencias.
- **PromptList Estática**: clases atómicas en inglés con features congeladas.
- **PromptList Dinámica**: prompts libres por voz con debounce, tras flag.
- **Mapeo en<->es-AR**: inglés para el detector, español para la voz.

## Términos de arquitectura productiva (Mapa 007 — Leaky + ReID + Bridge + WebRTC)

- **Bypass Galería**: rama `enroll_sync`/`purge` fuera de `AsyncLeakyQueue N=1` vía canal síncrono `ws.py` + `asyncio.Lock` + `store` atomic `tmp→replace` + `PendingSync localStorage:webcam.pending_sync` + `connected_clients` broadcast — evita pérdida persistencia durante `frame drops`.
- **Single-Writer proyección**: `WhiteboardState.last_identidades: list[IdentidadVista]|None` es proyección lectura para `overlay.js handleIdentidades` y `DecisionAgentica` contexto personalización, no afecta `ActNode → send_cmd_vel` bucle reactivo; `ABORTED overlay-only` no muta `Whiteboard`.
- **GzAdapter agnóstico**: `plataforma/sim/gazebo_adapter.py` `GzAdapter(SimAdapter)` con `_FakeGzTransport` mock `CmdVel→Twist@gz.msgs.Twist ROS_TO_GZ` `/model/turtlebot/cmd_vel` + `Odometry GZ_TO_ROS`, intercambiable `FakeGzTransport ↔ MujocoAdapter ↔ Gazebo Transport` sin cambios caller.
- **selectTransport fallback**: `frontend/src/ws-client.js:173 selectTransport()` probe `HEAD https://<JETSON-IP>:8554/webrtc/signal 200→webrtc else ws` (041 Q2 C + 040) — `WS D5` baseline `x86/WSL2/CI` + `webrtc://@:8554` Jetson `nvh264dec` con `fallback` sin `buffer bloat`.
- **Warmup ONNX**: `YoloDetector.warmup(10)` dummy `1×3×640×640` en `app.py lifespan` compila grafos ONNX/TensorRT amortiza `p99 120ms` cold-start (041).
- **Zero-Copy memoryview**: `ws.py` `decode_jpeg_b64` usa `memoryview(raw)` → `np.frombuffer` view sin copy inter-proceso hacia `np.ndarray` (041).
- **Dropped frames**: `metrics.py dropped_frames_total` counter `record_dropped_frame()` incrementado en `receiver` cuando `AsyncLeakyQueue.put` retorna `discarded=True` (fast/slow), expuesto `GET /metrics`.
- **threshold_per_person**: `IdentidadVista.threshold_per_person?: float|null` debug opcional `0.42-0.65` per-person calibrado, `None` si `0.42` fijo (042 Fase1) — no rompe wire `detecciones.identities`.

## Términos del harness P-E-V (Plan-Execute-Verify) — port de scraperargenpro

- **Harness P-E-V**: loop `Plan → Execute en sandbox → Verify con sensores` portado de `scraperargenpro/harness/harness.py:300` (Ning et al. 2026 §3.4). Estado filesystem en `harness/` (`harness/harness.py:69` `ROOT/trajectory.jsonl`), traza append-only inspeccionable con `jq/grep`.
- **3 tiers**: `read-only / sandbox-edit (default) / full-access` (`harness/harness.py:32` `TIERS`) con default restrictiva (`harness/harness.py:33` `DEFAULT_TIER=sandbox-edit`).
- **Sensores B**: `pytest` + `ruff` + `mypy` + `domain_assertions` Embodied AI (`harness/harness.py:287` `CmdVel clamp ±1.0/±1.5`, `FakeAdapter frame_id avanza`, `SimObservation SI/world-frame`, `IdentitiesStore 128-d`) + `evidence bundle` (`harness/harness.py:86` `EvidenceBundle`).
- **Traza A**: `harness/trajectory.jsonl` + `harness/sensor_logs/<run_id>.log` (`harness/harness.py:426` `append_trajectory`) — una línea JSON por fase `plan|execute|verify|done|human_gate`.
- **Human gate (HITL B)**: `harness/harness.py:115` `check_permission` gatilla `needs-human` en destructivas (`rm -rf`, `push --force`, `.env`, `DROP`) o red no listada fuera de `ALLOWLIST_DOMAINS` (`localhost`, `huggingface.co`, `api.openai.com`).
- **Sandbox-edit**: escribe solo `harness/output/` · `harness/trajectory.jsonl` · `harness/sensor_logs/` · `plataforma/webcam/backend/models/identities.json` (demo en `harness/output/sim_state.json` para no contaminar `.gitignore:22` `identities.json` real).
- **Plan as Contract**: `harness/plan.example.json` · `harness/plan.sim-headless.json` · `harness/plan.webcam-percepcion.json` con `intent`, `files`, `invariants`, `validation`, `rollback`.
- **Evidence bundle**: `{tests_run, linter, mypy, domain_assertions, uncovered, risk: low|medium|high, risk_reason}` + `human_gate{needed, reason, approved_by}` + `sensor_log` — criterio `verdict=ok` requiere `risk=low` + `tests_failed=0` + `domain ok`.

## Términos de la fusión Golden Path (ADR-0007)

- **Golden Path Fusión**: pipeline único y obligatorio `Issue → triage → wayfinder? → to-tickets → gitnexus-plan → gitnexus-work(+harness verify) → reviews → merge humano`. Se invoca con `/golden-path`; `pytest` solo corre el seam `CI+Harness` y nunca ejecuta skills (las skills viven a nivel agente). Reglas anti-solape: `wayfinder` solo con niebla, `to-tickets` trocea una vez, un solo fix-cycle de reviews. Single-writer `trajectory.jsonl`, `sandbox-edit` default. Orden canónico de (1) Matt Pocock (2) GitNexus (3) repo más Harness; ver ADR-0007 y ADR-0008.
- **DoD Golden Path**: checklist verificable `CI fail rate <10%` + `harness verify verdict:ok risk:low` sin `UNKNOWN` sin confirmar + `detect_changes` sin `HIGH` ignorado + `pdg:true` `status:current`. `impact_ratio` es métrica observada, no gate en P0.
- **Linter de Documentación**: regla `\.py:\d+` sobre `CONTEXT.md` que prohíbe anclas `archivo:línea` efímeras; el glosario es puro, los detalles viven en ADRs/prototypes. Caso anti-pattern: `ws.py:197` (Whitelist) documentado en ADR-0007, no en glosario.
