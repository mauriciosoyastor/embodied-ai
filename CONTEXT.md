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

## Términos de Memoria de Objetos (detalle en ADR-0011 apéndice)

- **Banca Dual work/stable**: bancas separadas persona vs objetos.
- **Prototipo**: embedding representante con políticas insert/EMA/merge/promote.
- **EMA (Exponential Moving Average)**: promedio móvil gated por similitud.
- **Gating STRONG/AMBIGUOUS/WEAK**: mapeo a histéresis de zonas coseno.
- **Lifecycle objetos**: estados NEW → TENTATIVE → CONFIRMED → INACTIVE, memoria volátil.
- **Parts/BG desactivados v1**: solo canal appearance global.
- **Grafo de Vecinos (NeighborGraph)**: co-ocurrencia dirigida, solo contexto.
- **Contexto Vecinal (NeighborSets)**: bonus/penal con gates de calidad y veto.
- **Hungarian híbrido**: asignación per-class con fallback IoU.
- **Ambiguo / Provisional**: estados que no mutan Whiteboard.
- **TTL vecino**: expiración episódica de aristas fugaces.

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

## Términos de arquitectura productiva (detalle en ADR-0014)

- **Bypass Galería**: persistencia fuera de la cola de frames.
- **Single-Writer proyección**: lectura para overlay sin afectar el bucle reactivo.
- **GzAdapter agnóstico**: simulador intercambiable sin cambios al llamador.
- **selectTransport fallback**: WebRTC con fallback a WS.
- **Warmup ONNX**: compilación anticipada contra cold-start.
- **Zero-Copy memoryview**: views sin copia inter-proceso.
- **Dropped frames**: contador de descartes expuesto en métricas.
- **threshold_per_person**: umbral por persona solo para debug.

## Términos del harness P-E-V (detalle en harness/README)

- **Harness P-E-V**: loop plan → execute en sandbox → verify con sensores.
- **3 tiers**: read-only / sandbox-edit (default) / full-access.
- **Sensores B**: pytest + ruff + mypy + aserciones de dominio + bundle.
- **Traza A**: trajectory append-only + logs por run.
- **Human gate (HITL B)**: destructivas o red no listada piden humano.
- **Sandbox-edit**: escrituras confinadas al sandbox.
- **Plan as Contract**: intent, files, invariants, validation, rollback.
- **Evidence bundle**: veredicto ok exige tests verdes + dominio ok.

## Términos de la fusión Golden Path (detalle en ADR-0007/0008)

- **Golden Path Fusión**: pipeline único Issue → triage → wayfinder? → to-tickets → plan → work → reviews → merge humano.
- **DoD Golden Path**: CI verde + verify ok/low + sin HIGH ignorado + índice corriente.
- **Linter de Documentación**: sin anclas efímeras; detalle en ADRs.
