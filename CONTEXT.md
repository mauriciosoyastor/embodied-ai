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

## Términos de interacción voz y registro facial (Voz + Cámara)

- **Push-to-talk**: activación de micrófono por pulsación mantenida del botón; evita escucha continua y falsos positivos. Encaja con throttling `MAX_FPS=10` y `WS_BUFFERED_LIMIT` de `ws-client.js`.
- **STT (Speech-to-Text)**: conversión audio→texto vía Web Speech API (`webkitSpeechRecognition`) en `es-AR`; híbrido con servidor solo si falla el browser. Latencia objetivo <500 ms.
- **TTS (Text-to-Speech)**: síntesis voz desde texto vía `speechSynthesis` del browser en `es-AR`; reproduce respuesta del LLM sin salir del frontend.
- **Transcript**: par `usuario→LLM` y `LLM→usuario` mostrado en panel `percepcion-panel` (`plataforma/webcam/frontend/src/main.js`); fuente para telemetría y debug.
- **Enrollment facial**: flujo `YOLO person (conf>0.6)` → detector facial (MediaPipe Face) → recorte 160×160 → extracción embedding → asociación a nombre. Se dispara con `thumbs_up` confirmado por histéresis (reusa `GestoReconocido`).
- **Embedding facial**: vector denso (ej. 128-d) que representa identidad; comparación por distancia coseno <0.4 = match. No almacena imagen cruda por privacidad.
- **Registro (face)**: persistencia de `embedding + nombre + ts` en `localStorage` y opcional `backend/models/identities.json`; permite re-identificar `person` en frames posteriores sin re-enrollar.
- **Muse Spark 1.2 free**: LLM por defecto `opencode/muse-spark-1.2-contributor-free` (Cursor free tier) vía API OpenAI-compatible; expone `OPENCODE_API_KEY/CURSOR_API_KEY/OPENAI_API_KEY` en `fase-1/.env`. Reemplaza `gemini-3.6-flash` en `fase-1/gemini_client.py` y `orchestrator.py` (`openai:opencode/muse-spark-1.2-contributor-free`).
- **Proveedor LLM gratuito**: servicio que expone chat completions sin coste (hosted free-tier o local). Hospedado no requiere VRAM (Groq, HF Router) y habla OpenAI-compatible vía `OPENAI_BASE_URL`; local (Ollama `qwen2.5:1.5b`) requiere 2GB RAM y `http://localhost:11434/v1` con `api_key=ollama`.
- **Free-tier hospedado**: cuota sin tarjeta (ej. Groq `llama-3.1-8b-instant` 14.400 RPD/30 RPM, HF Router `meta-llama/Llama-3.2-3B` $0.10/mes, OpenRouter `:free` 50 RPD). Expone `OPENAI_BASE_URL` distinto por proveedor.
- **Fallback local**: Ollama `qwen2.5:1.5b` (986MB, 128k, Apache-2.0) como respaldo offline ilimitado cuando hosted falla; latencia CPU 200-350ms TTFT.
- **Cadena de fallback**: orden `Groq → HF Router → Ollama → mock` en `plataforma/webcam/backend/app.py:57 POST /voz` y `fase-1/gemini_client.py`; `401` corta, `429` respeta `retry-after` o 30s, mock final con mensaje tipado en `percepcion-panel`.
- **EnrollSync / EnrollAck**: evento WS `enroll_sync {id,nombre,embedding[128],ts}` (bypass `Leaky Queue N=1`) + ack `enroll_ack {id,status}`; id `nanoid` 8-char garantiza idempotencia en reintentos tras reconexión.
- **Purge / PurgeAck**: evento `purge {all:true|ids:[]}` broadcast a todos los sockets activos que limpia `localStorage:webcam.identities` + `backend/models/identities.json` simultáneamente, con `purge_ack` por cliente.
- **PendingSync**: cola `webcam.pending_sync` en `localStorage` que acumula `enroll_sync`/`purge` cuando `ws.readyState !== OPEN` para cero pérdida offline, vaciada en `ws.onopen`.
- **Hidratación híbrida**: `GET /identities` al iniciar (`app.py` `lifespan` carga `identities.json`) provee snapshot base, WebSocket solo transporta deltas `enroll_sync`/`purge` en tiempo real.
- **Bypass de Leaky Queue**: `enroll_sync`/`purge` no pasan por `AsyncLeakyQueue N=1` (diseñada para `frame`), usan branch paralelo con `asyncio.Lock` + write atómico `tmp→replace` para `identities.json`.
- **IdentitiesStore**: archivo `plataforma/webcam/backend/models/identities.json` con schema `{id,nombre,embedding[128],count,updatedAt}`; promedio móvil `hat_e = normalize(e_old*min(N,5)+e_new)` con cap 5, threshold coseno 0.42, clave primaria `id` (nanoid) permite nombres duplicados, `GET /identities` + `lifespan` load.
