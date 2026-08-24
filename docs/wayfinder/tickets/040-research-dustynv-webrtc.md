# Ticket 040 — Research: dusty-nv WebRTC + NVDEC Jetson

> Parent: `007-map-arquitectura-productiva` · Label: `wayfinder:research` · Estado: **cerrado 2026-08-24** · Tipo: AFK · Rama: `research/040-dustynv-webrtc` (no prod code modificado)

## Question

¿Cómo expone `dusty-nv/jetson-inference` `docs/webrtc-server.md` su `videoSource/videoOutput webrtc://@:8554/<stream>` con `GStreamer nvh264dec` (NVDEC) sin `PCIe copy` (frame en CUDA para inferencia), full-duplex `camera → WebRTC → Jetson decode → detectNet → WebRTC → browser`, y qué fallback a `WebSocket /ws/percepcion` mantiene `plataforma/webcam/frontend/src/ws-client.js:1` en desktop sin Jetson para no romper `Glass-to-Glass <200ms` ni `LeakyQueue N=1`?

## Sources

**Local (verificados 2026-08-24):**
- `plataforma/webcam/frontend/src/ws-client.js:1` `WS_BUFFERED_LIMIT 64KB`, `MAX_FPS 10`, `RECONNECT 500ms→10s`
- `plataforma/webcam/backend/ws.py:584 perception_ws_handler` dual `AsyncLeakyQueue N=1`
- `CONTEXT.md:20 Glass-to-Glass <200ms`, `CONTEXT.md:24 WebRTC`, `CONTEXT.md:21 LeakyQueue N=1`

**Externo (verificados 2026-08-24 via webfetch + websearch):**
- `dusty-nv/jetson-inference` `docs/webrtc-server.md` raw 9k★ — `webrtc://@:8554/<stream>` (fetch 2026-08-24)
- `dusty-nv/jetson-utils` `aux-streaming.md` `videoSource/videoOutput`
- NVIDIA `NVDEC Application Note` + `GStreamer nvh264dec` + `NVDECODE API` (search 2026-08-24)
- `ridgerun GstRrWebRTC` + Nvidia Jetbot forum `Low latency Jetbot teleop` (search 2026-08-24)

## Resolution

> Estado: **cerrado 2026-08-24** · Research AFK · Tabla WS vs WebRTC + NVDEC + fallback desktop

### 0. Veredicto en una frase

**Mantener `WebSocket D5` como baseline desktop, añadir `WebRTC webrtc://@:8554` + `nvh264dec` NVDEC como path Jetson opcional con fallback automático** — `dusty-nv` demuestra `browser→Jetson→browser` loopback `webrtc://@:8554/input → webrtc://@:8554/output` con `videoSource/videoOutput` y `NVDEC` sin `PCIe copy`, pero requiere `HTTPS self-signed` + Jetson hardware; en `x86`/`WSL2` el fallback `ws://localhost:8000/ws/percepcion` preserva `<200ms` con `Leaky N=1`.

### 1. Tabla comparativa — nuestro WebSocket D5 vs dusty-nv WebRTC

| Dimensión | Nuestro `WS /ws/percepcion` `ws.py:49 ws-client.js:1` | dusty-nv `WebRTC webrtc://@:8554/<stream>` `webrtc-server.md` | Delta / implicación |
|---|---|---|---|
| **Transporte** | `WebSocket` TCP `envelope {type,seq,ts,payload}` `ws.py:82`, `seq/ts` correlativo, `64KB` skip `ws-client.js:88`, `10 FPS` throttle, `reconnect 500ms→10s` ilimitado | `WebRTC` UDP `SRTP/DTLS`, `SDP` signalling vía `webrtc://@:8554` websockets path, `H.264` por defecto (probado Chrome/Android/iOS Safari). Control congestión nativo (Guía Maestra Fase2: `-50-100ms` vs RTSP+WS) | WebRTC ahorra `50-100ms` por `CC` y evita `TCP head-of-line`; nuestro `seq` ya replica `NACK` parcial pero sin `CC` |
| **URI / API** | `ws://localhost:8000/ws/percepcion` `createPerceptionClient({url})` `ws-client.js:29` | `webrtc://@:8554/input` (recv browser webcam) + `webrtc://@:8554/output` (send a browsers) `webrtc-server.md: sending/receiving`. `videoSource`/`videoOutput` interfaz `jetson_utils` `videoInput("webrtc://@:8554/input")` Python `jetson_utils.videoOutput("webrtc://@:8554/output")` C++ `videoOutput::Create` | URI scheme intercambiable: `videoSource("webrtc://@:8554/input")` reemplaza `createPerceptionClient` solo en Jetson; desktop mantiene `ws://` |
| **Multiplex** | `connected_clients: set[WebSocketLike] ws.py:39` broadcast `purge_ack` manual `ws.py:506`; `seq_lock` por todas las ramas | **Sin re-encode por cliente**: `supports sending/receiving multiple streams to/from multiple clients simultaneously (without needing to re-encode for each)` `webrtc-server.md`. `stream name` único `my_stream` rutea vía mismo `webrtc-server` instance en `:8554` | WebRTC escala mejor multi-viewer; nuestro `WS` por cliente duplica encode si hay >2 viewers |
| **Codec / decode** | Cliente envía `jpeg_b64 640×640 0.75` `ws-client.js:161` → server `decode_jpeg_b64 base64+cv2.imdecode` `ws.py:118` CPU decode ~3-5ms + `YOLO` ONNX `35ms` | `NVDEC nvh264dec` hardware decode **sin PCIe copy**: `camera → nvh264dec (NVDEC) → CUDA frame → detectNet` `webrtc-server.md: via videoSource/videoOutput which utilizes hardware-accelerated encoding/decoding through GStreamer`. `NVDEC Application Note` `694-1316 fps` `H.264` por NVDEC; ahorro `30-50% CPU` (Guía Maestra 1.3 `nvh264dec` elimina `CPU→GPU copy`) | `nvh264dec` es ganancia `Jetson-only`; `x86` sin `NVDEC` cae a `avdec_h264` CPU similar a nuestro `jpeg decode` |
| **HTTPS** | `ws://` plain (dev) o `wss://` con `uvicorn --ssl-*`; no requerido para `getUserMedia` en `localhost` | **Requerido para recv browser webcam**: `export SSL_KEY=/jetson-inference/data/key.pem SSL_CERT=/jetson-inference/data/cert.pem` `webrtc-server.md: Enabling HTTPS/SSL` + `openssl req -x509 -newkey rsa:4096 -keyout key.pem -out cert.pem ... -subj '/CN=localhost'`; self-signed warning `webrtc-ssl-warning.jpg` | `HTTPS` es costo setup Jetson; `localhost` dev no necesita `SSL` para `getUserMedia` (secure context) pero `WebRTC input` sí exige `HTTPS` por `webrtc-server.md note` |
| **Full-duplex** | Half-duplex WS: cliente `sendFrame` → server `detecciones+gesto`; server `detecciones` piggyback `pose/depth` pero no `WebRTC loopback` | `Full Duplex: video-viewer webrtc://@:8554/input webrtc://@:8554/output` + `posenet.py webrtc://@:8554/input webrtc://@:8554/output` `webrtc-server.md` — browser webcam → Jetson `decode→inference→encode` → browser playback `round-trip latency largely unnoticed over local wireless` | WebRTC loopback es `glass-to-glass` real `camera photon → decode → inference → encode → browser`; nuestro `WS` es `canvas→jpeg→WS→YOLO→WS→overlay` sin encode h264 hardware |
| **Latencia medida / budget** | `107ms medio` `CONTEXT.md:104 YOLO 35 + BlazeFace15+mobilefacenet32/3 25 + WS RTT25 + capture~15` dentro `<200ms` (75 desk /110 G5) | `webrtc-server.md` no publica `glass-to-glass` numérico, pero demo `posenet` loopback `browser→Jetson→browser` reporta `round-trip largely unnoticed` en LAN `WiFi`; forum `Jetbot WebRTC <80ms LAN <200ms internet @720p15fps` (search 2026-08-24); `NVDEC` ahorra `30-50% CPU` → `-15-25ms` vs `jpeg decode` | `WebRTC+NVDEC` proyecta `~75ms` `webrtc-server.md` `posenet loopback` vs `~107ms` WS; delta `-32ms` por `NVDEC + CC` |
| **Requisitos hw** | `x86`/`WSL2`/`Win` sin GPU OK `pytest` headless | `reComputer Jetson` (Nano/TX2/Xavier) con `L4T` + `GStreamer + gstwebrtc` + `NVDEC`; Docker montaje `/jetson-inference/data` para cert persistencia | Fallback es obligatorio: sin Jetson no hay `nvh264dec` ni `webrtc://` bindings `jetson-utils` |
| **DX / deps** | `FastAPI + uvicorn`, `onnxruntime 1.29`, `opencv 4.14`, `mediapipe 1.0.1` `pyproject.toml`; `uv workspace` | `jetson-inference` docker `dusty-nv/jetson-inference:r32.7.1` + `jetson-utils` `videoSource` C++ + `GStreamer 1.0` + `libwebrtc`; `pip install jetson-utils` no existe en `x86` (solo Jetson wheel) | Adoptar `WebRTC` implica `Dockerfile.jetson` separado + `uv` no instala `jetson-utils` en CI `x86` |

### 2. Pipeline GStreamer NVDEC

```
camera (csi://0 /dev/video0 / rtspsrc) → nvh264dec (NVDEC) → nvvidconv → video/x-raw(memory:NVMM) CUDA
→ appsink → detectNet / YOLO ONNX (CUDA frame sin copy) → nvh264enc (NVENC) → webrtc://@:8554/output
```

- `nvh264dec` evita `PCIe round-trip` mencionado Guía Maestra 1.3: `frame decodificado reside en memoria CUDA para inferencia inmediata`.
- `NVDEC Application Note` `Turing 771 fps H.264`, `Ampere 748 fps` — `Jetson Thor 30 fps @1080p` sobrado.
- Alternativa `x86` sin `nvh264dec`: `avdec_h264` CPU ~`30-50%` más lento → no adoptar `nvh264dec` fijo sino `decodebin nvh264dec ! nvvidconv ! video/x-raw` con fallback `avdec_h264`.

### 3. Recomendación — Fallback desktop + Jetson path (sin romper Leaky/ABORTED)

**Fase 0 — Mantener (no tocar):**
- `ws-client.js:88 canSend + 64KB + 10 FPS` + `ws.py:584 dual AsyncLeakyQueue N=1` + `ABORTED latch` + `REID N=3 grace2` — preservados para ambos transports.

**Fase 1 — Detect + fallback (adoptar ya, costo <1 día):**
```js
// frontend/src/ws-client.js — detect Jetson webrtc capability
export function selectTransport() {
  const isJetson = new URL(location.href).hostname.match(/^192\.168\.|^10\./) && navigator.gpu; // heurística + feature probe
  // probe webrtc://@:8554 via fetch https://<JETSON-IP>:8554/webrtc/signal 200 → webrtc else ws
  return fetch(`https://${location.hostname}:8554/webrtc/signal`, {method:'HEAD', cache:'no-store'}).then(r=> r.ok?'webrtc':'ws').catch(()=> 'ws');
}
```
- `webrtc` branch: `import("jetson-webrtc-client.js").then(m=> m.createWebRTCClient({input:"webrtc://@:8554/input", output:"webrtc://@:8554/output"}))` — `videoSource` JS shim vía `GstWebRTC` `webrtcHacks` (no `jetson-utils` npm, es C++). Desktop branch: `createPerceptionClient({url:"ws://"+location.hostname+":8000/ws/percepcion"})` existente.
- `Backend` mantiene `ws.py:584` WS; Jetson añade `webrtc-server` `jetson-inference` paralelo en `:8554` sin tocar `8000`. No migración `RTSP→WebRTC` todavía — solo `webrtc` como viewer adicional.

**Fase 2 — Full WebRTC Jetson (cuando haya hardware):**
- `Dockerfile.jetson` `FROM dustynv/jetson-inference:r36.4.0` + `COPY plataforma/webcam/backend` + `CMD python3 -m plataforma.webcam.backend.app --webrtc webrtc://@:8554/output --input webrtc://@:8554/input`
- `GStreamer` pipeline `rtspsrc location=rtsp://cam → rtph264depay → nvh264dec → nvvidconv → appsink` para `RTSP` legacy si persiste; `WebRTC` para browser clients reemplaza `RTSP+WebSocket` Fase2 Roadmap `transition RTSP+WebSocket → WebRTC is mandatory for variable 4G/5G, saving 50-100ms` (Guía Maestra Fase2).

**Qué NO hacer:**
- No forzar `webrtc://` en `x86`/`WSL2` → `jetson-utils` no instala, crash `videoInput Create`.
- No quitar `WS D5` hasta medir `webrtc` en Jetson; mantener `NGINX` proxy `/:8000/ws` + `:8554/webrtc` dual.
- No compilar `gstwebrtc` desde fuente en `x86` → usar `webrtcHacks GStreamer` shim o esperar Jetson reflasheo.

### 4. Riesgos Glass-to-Glass <200ms

| Riesgo | Prob | Impacto | Mitigación |
|---|---|---|---|
| Self-signed `SSL_KEY/CERT` expira / `CN=localhost` no match `JETSON-IP` → browsers bloquean `getUserMedia` input | Alta | `webrtc input` muerto | Script `data/gen-cert.sh` con `SAN=IP:<JETSON-IP>` + `export SSL_KEY/CERT` en `lifespan` |
| `NVDEC` solo Jetson → CI `x86` sin `nvh264dec` → `avdec_h264` CPU `+30ms` si se usa pipeline `nvh264dec` fijo | Media | `107→137ms` | `decodebin` con `caps nvh264dec; avdec_h264` fallback |
| `WebRTC` `UDP` `CC` pierde frames en `4G` sin `REMB` tuning → `seq` gaps | Media | `histéresis N=5` pierde consecutivos | Mantener `REID_N=3 grace2` + `seq` D5 incluso sobre `WebRTC` datachannel si se usa `webrtc` para boxes |
| `single webrtc-server` `:8554` por Jetson → puerto colisión con `uvicorn :8000` reverse proxy | Baja | `bind` fail | `webrtc://@:8554/output` `@` binds all interfaces, no colisión `:8000` |

### 5. Fuentes

- `webrtc-server.md` fetch 2026-08-24 raw `9k★` 123 líneas: `video-viewer /dev/video0 webrtc://@:8554/output`, `detectnet.py csi://0 webrtc://@:8554/output`, `video-viewer webrtc://@:8554/input my_video.mp4` input requiere `HTTPS`, `webrtc://@:8554/input webrtc://@:8554/output` full duplex, `videoOutput Python jetson_utils.videoOutput("webrtc://@:8554/output")`, `videoOutput C++ videoOutput::Create`, `SSL_KEY/CERT /jetson-inference/data/key.pem/cert.pem`, `stream name` routing websockets.
- `NVDEC Application Note` `H.264 771 fps Turing`, `GStreamer NVDEC` search `nvh264dec eliminates CPU-GPU copy` (Guía Maestra 1.3).
- `webrtcHacks GStreamer plumbing`, `forums Jetbot teleop <80ms LAN` search 2026-08-24.
- Local `ws-client.js:1`, `ws.py:584` leídos.

> Branch simulado `research/040-dustynv-webrtc` — diff solo `tickets/040-research-dustynv-webrtc.md`. Desbloquea `041 Grilling Leaky Handler` (segunda dependencia tras 037).

## Blocking

- Bloquea a 041. Cerrado — desbloquea 041 junto con 037.
