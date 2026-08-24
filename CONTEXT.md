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

## Términos de visión viva (ReID + Tracking per-frame) — Ticket 033

- **ReID híbrido per-frame**: pipeline `YOLO person (conf>0.6)` → `BlazeFace short-range` → `mobilefacenet 128-d` que calcula embedding cada 3 frames @10Hz (~300ms) + trigger inmediato si `IoU<0.7` vs bbox previo; balancea `Glass-to-Glass <200ms` (75 ms desktop / 110 ms Moto G5) vs reactividad.
- **Zona gris coseno 0.42–0.55**: rango `cosineDistance` donde `0.42`=match firme `Hola <nombre>` → Whiteboard, `0.42–0.55`=`posible <nombre>?` solo overlay amarillo sin promover, `>0.55`=desconocido.
- **Histéresis ReID N=3**: confirmación `Hola <nombre>` solo tras 3 matches `cos<0.42` consecutivos, `grace=2` frames fallidos resetean; evita flicker `desconocido↔Hola`, análogo a `handle_gesto N=5`.
- **Tracker IoU greedy + edad 5**: matching `IoU>0.5` greedy por área `w*h` para persistir `id` cuando YOLO flickerea 1 frame; `<1ms` vs `KCF`/`ByteTrack`; drop si 5 frames sin match (~500ms).
- **ABORTED overlay-only**: en `ABORTED` latch re-id sigue pintando `overlay.js` pero **no** muta `WhiteboardState` ni alimenta `DecisionAgentica`; seguridad idéntica a `handle_gesto` latch.
- **Multi-person viva**: `enroll` bloquea si `persons>=2`, `re-id` permite hasta 3 caras simultáneas con badges separados e `IoU` independiente.
- **Budget visión viva**: reparto `YOLO ~35ms server paralelo + BlazeFace ~15ms + mobilefacenet ~32ms/3 media ~25ms + WS RTT ~25ms = ~107ms` medio dentro de `<200ms`; `MAX_FPS=10` + `LeakyQueue N=1` + `bufferedAmount>64KB` skip permanece.
- **IdentidadVista**: vista per-frame `{id,nombre,cosine,conf,estado: confirmado (<0.42)|posible (0.42–0.55)|desconocido (>0.55), box, face_box, frame_id, ts}` producida por ReID híbrido client-side (hasta 3 por frame) desde `loadGallery()` hidratada.
- **Whiteboard last_identidades**: campo `WhiteboardState.last_identidades: list[IdentidadVista] | None` (single-writer memoria, sin `transcript`); extiende envelope D5 `detecciones` con `identities` opcional, update híbrido cada 3 frames + `IoU<0.7`, client-side patch directo sin `LeakyQueue N=1`, reusa `GET /identities` + `PendingSync`, `DecisionAgentica` lo consume como contexto personalización (no `CmdVel`).

## Términos de Percepción Enriquecida v2 (Whitelist + Canales nuevos) — Ticket 075

- **Whitelist v2**: 13 clases COCO curadas `person, chair, couch, bottle, cup, cell phone, laptop, keyboard, mouse, book, backpack, handbag, remote` filtradas en `plataforma/webcam/backend/ws.py:197 run_inference` **previo a serialización** `boxes_payload`; fuera de whitelist log-only, no entra a `WhiteboardState.PercepcionVista` ni dispara `DecisionAgentica`. `person` mantiene `conf>0.6 area>15%` + histéresis N=5/ReID N=3; genéricas `conf>0.50 area>3%` único.
- **PercepcionVista**: agregado `WhiteboardState.percepcion_vista: {detecciones, posturas, profundidades, leyenda}` con TTL por campo (detecciones 100ms, postura 150ms, profundidad 200ms, leyenda 1000ms), single-writer memoria, sin `transcript`; consumido por `DecisionAgentica`.
- **Postura**: `Postura {frame_id, keypoints: [{x,y,conf}] 17 COCO [0,1], conf_global}` producida por `YOLO11n-pose` 5Hz piggyback en `detecciones`; ABORTED overlay-only.
- **Profundidad**: `Profundidad {z_rel: float 0..1, z_m: float|null, box_center: {x,y}}` mediana 3×3 centro bbox desde `MiDaS small 256` (~42ms) 5Hz piggyback; `intra_op_num_threads=2` + `asyncio.to_thread` paralelo sin jitter.
- **LeyendaEscena**: `LeyendaEscena {caption: str es-AR 1 frase, objects: [str], conf, ts}` vía VLM 1Hz `scene_caption` separado (leaky-skip 1/30) cadena `Groq llama-4-scout → HF Qwen2.5-VL → Gemini 2.0 Flash → mock` (~300ms p50).
- **ABORTED overlay-only v2**: en `ABORTED` latch todos los canales v2 (postura/profundidad/caption) solo pintan `overlay.js`/`percepcion-panel` sin mutar `WhiteboardState`.

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
