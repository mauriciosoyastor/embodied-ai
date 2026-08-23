# 023 — Research: Enrollment actual + WS sync + file lock (hibrido)

> Parent: `docs/wayfinder/004-map-enrollment-hibrido.md` · Ticket 023 · Rama `research/023-enrollment-hibrido` · 2026-08-23 · AFK research

Fuentes primarias: lectura local `Read` de `plataforma/webcam/frontend/src/enrollment-panel.js`, `face-embedding.js`, `frontend/ws-client.js`, `backend/ws.py`, `backend/app.py`, `backend/config.py`, `tests/test_ws.py`, `pyproject.toml`, `.gitignore` + docs `asyncio.Lock` (https://docs.python.org/3/library/asyncio-sync.html#asyncio.Lock).

---

## 0. Resumen ejecutivo

| Pregunta Ticket | Hallazgo | Bloqueante |
|---|---|---|
| ¿Estado `enrollment-panel.js`? | `localStorage:webcam.identities` OK, `THUMBS_N=5` + `GRACE=3`, single-person guard, consent `webcam.consent`, galería render + `Borrar todos` solo local. No sync servidor aún. | Base para hibrido |
| ¿Estado `face-embedding.js`? | 128-d L2-norm, `stubEmbedding` xorshift determinístico, `COSINE_THRESHOLD 0.42` (0.42-0.55 gris), lazy `onnxruntime-web` `/models/mobilefacenet.onnx`. | Schema `identities.json` debe guardar `Float32[128]` L2 |
| ¿Estado `ws.py` D5? | Envelope `{type,seq,ts,payload}` validado estricto, `type∈{frame,detecciones,gesto,estado}`, Leaky `N=1` sync+async, `WS_BUFFERED_LIMIT 64KB` cliente. Solo `frame` entra a leaky queue. | Nuevo `enroll_sync/purge` **fuera** de leaky queue |
| ¿Estado `app.py` lifespan? | `lifespan` lazy init YOLO+gesture con log stub, `yield`, `app=FastAPI(lifespan=lifespan)`. Punto de extensión natural para cargar `identities.json`. No hay `GET /identities` aún. | Añadir carga + lock ahí |
| ¿File lock? | `asyncio.Lock` recomendado (single-process uvicorn). `fcntl`/`msvcrt` descartado — no portable Win32, bloquea threads no coroutines. | `asyncio.Lock` + write atómico `temp+rename` |
| ¿Carga al iniciar? | `backend/models/.gitignore` = `*` (solo `.gitignore`), `identities.json` gitignoreado en raíz (`**/identities.json`). Archivo no existe aún — lifespan debe crear si falta. | `lifespan` carga o `[]`, `GET /identities` hidrata frontend |
| ¿Evento sync sin romper leaky? | `ws-client.js` throttled 10 FPS + `bufferedAmount>64KB` skip solo para `frame`. `enroll_sync` ~2.1KB JSON (128 floats) <64KB, debe bypass `canSend()`. | Receiver bifurcar `frame` vs `enroll_sync/purge` |

**Conclusión:** Extensión de bajo riesgo. No tocar `LeakyQueue`, añadir branch `enroll_sync`/`purge` paralelo, proteger `identities.json` con `asyncio.Lock` global + `async with`, cargar en `lifespan`, exponer `GET /identities`.

---

## 1. `enrollment-panel.js` — estado actual

**Archivo:** `plataforma/webcam/frontend/src/enrollment-panel.js:1` (375 líneas)

| Aspecto | Detalle | Líneas |
|---|---|---|
| Clave storage | `STORAGE_KEY = "webcam.identities"` | 8 |
| Load/save | `loadGallery()` try/catch JSON, `saveGallery()` `JSON.stringify` | 12-24 |
| ID | `nanoid()` `Math.random().toString(36).slice(2,9)` — no UUID, colisión baja pero auditar | 25-27 |
| Consent | `webcam.consent` `"1"/"0"`, bloquea `evaluate()` si `!consentGiven` | 40-43, 210 |
| Histéresis | `THUMBS_N=5`, `GRACE_FRAMES=3`, `thumbsCount`/`grace` reset si `blockReason` | 9-10, 314-332 |
| Gate `evaluate()` | `person>0.6 & area>0.15` (`selectPerson`), single-person, `mockFaceFromPerson` inset 25%/50%x35%, `ABORTED` bloquea, `validNombre` 2-32 letras | 195-242 |
| Threshold | Importa `COSINE_THRESHOLD` de `face-embedding.js` solo display, no filtra aquí | 71 |
| Embedding | `embedder.embed(cropSource||{112x112}, seed)` seed=`nombre|x|Date.now()` | 244-268 |
| Registro | `rec={id,nombre,embedding:Array.from(embedding),ts,frame_id,person_box,face_box}` → `gal.push` → `saveGallery` → `renderGallery` | 269-288 |
| Galería | `renderGallery()` lista con `👤`, `nombre`, `ts`, `id.slice(0,4)`, botón `data-del` borra uno | 90-118 |
| Borrar todos | `confirm()` → `saveGallery([])` — **solo local**, no emite WS | 168-173 |
| Wiring | `handleDetecciones/ Gesto/ Estado` públicos, `setNombreFromVoice`, `onEnroll` callback | 301-374 |
| Voz | `setNombreFromVoice` regex `me llamo|soy|mi nombre es` + 2 palabras | 341-358 |

**Deuda para hibrido:**
- `tryEnroll` no hace `fetch` ni `ws.send` — punto de inserción para `enroll_sync`. Debe mantener `localStorage` primero (render sin latencia) luego sync.
- `clear` y `data-del` no notifican servidor — para purga dual necesitan emitir `purge`.
- `id` nanoid 7 chars OK para prototipo, pero servidor debe tratarlo como idempotencia key (si cliente reintenta mismo `id`, no duplicar).

## 2. `face-embedding.js` — 128-d

**Archivo:** `plataforma/webcam/frontend/src/face-embedding.js:1` (145 líneas)

| Aspecto | Detalle |
|---|---|
| Dim | `EMBEDDING_DIM=128` |
| Threshold | `COSINE_THRESHOLD=0.42`, `COSINE_GRAY=[0.42,0.55]` — grilling 005; CONTEXT map 004 menciona 0.4 pero código dice 0.42 (preferir 0.42) |
| Norm | `l2Normalize(vec)` `Float32Array` |
| Distancia | `cosineDistance(a,b)=1-dot` clamp [-1,1], `cosineSimilarity=1-distance` |
| Stub | `stubEmbedding(seedStr)` hash FNV-1a `2166136261` + xorshift32 → `rnd()*2-1` → `l2Normalize` — determinístico mismo seed |
| Validación | `isValidNombre` `/^[A-Za-zÁÉÍÓÚáéíóúÑñ ]+$/.test` 2-32 chars |
| Embedder | `createFaceEmbedder({modelUrl:"/models/mobilefacenet.onnx"})`, `init()` intenta `import("onnxruntime-web")` + `HEAD /models/...` → `InferenceSession.create(wasm)`, fallback `isStub=true` |
| `embed()` | Si stub/no session → `stubEmbedding(seedHint)`; si real: `canvas 112x112`, `ImageData`, `Float32Array[1*3*112*112]` `(x-0.5)/0.5` per channel, `session.run({input:Tensor})` → `l2Normalize(vec.slice(0,128))` |
| Reuso onnx | Pin existente `onnxruntime==1.29.*` en `backend/pyproject.toml:9` y `frontend` vía `onnxruntime-web` — sin colisión TFLite (ver Ticket 002) |

**Implicancias hibrido:**
- Servidor no recalcula embedding (cliente lo genera). Servidor solo valida `Array.isArray(e) && e.length===128 && e.every(n=>typeof n==="number")` y que esté L2-norm (~1.0 ±0.01).
- Promedio al re-enrolar mismo `nombre`/`id`: `new=(old*count+incoming)/(count+1)` luego `l2Normalize` — debe vivir en servidor (`identities.json` store).
- Tamaño: cada identidad JSON ~ 128*~10 chars + metadata ≈ 1.5-2KB. 100 identidades ≈ 200KB, trivial.

## 3. `ws.py` — envelope D5 + Leaky Queue N=1

**Archivo:** `plataforma/webcam/backend/ws.py:1` (328 líneas) · **Cliente:** `plataforma/webcam/frontend/ws-client.js:1` (155 líneas)

### 3.1 Envelope D5

```python
# ws.py:58-68
make_envelope(type_: EnvelopeType, seq: int, payload: dict, ts=None) -> {"type","seq","ts","payload"}
parse_envelope(raw: str) -> dict  # valida 4 keys + type in {frame,detecciones,gesto,estado}
now_ms() -> int(time.time()*1000)
```

```js
// ws-client.js:94-99
{ type:"frame", seq, ts:Date.now(), payload:{ frame_id, jpeg_b64, width, height } }
```

| Campo | Tipo | Notas |
|---|---|---|
| `type` | `Literal["frame","detecciones","gesto","estado"]` | Extender para `enroll_sync`, `enroll_ack`, `purge`, `purge_ack` (ver §7) |
| `seq` | `int` incremental cliente `seq++`, servidor `seq_counter[0]++` por cada envío | Para `enroll_sync` el servidor debe incrementar su `seq_counter` al responder `enroll_ack` |
| `ts` | `int` ms epoch | Ya en todos |
| `payload` | `dict` libre por type | Validar esquema por type |

Validación actual `ws.py:77-78` rechaza `type` desconocido → `ValueError` → `continue` en receiver:32. **Necesario ampliar whitelist** antes de añadir nuevos types.

### 3.2 Leaky Queue N=1

```python
# ws.py:105-166
LeakyQueue[T](maxsize=1)      # sync deque(maxlen=1), put()->bool discarded
AsyncLeakyQueue[T](maxsize=1) # asyncio.Condition, put()->bool, get()->T, qsize()
config.py:9 LEAKY_QUEUE_SIZE=1
```

Servidor handler `ws.py:269-328`:

```python
queue = AsyncLeakyQueue(maxsize=1)


async def receiver():
    env = parse_envelope(raw)
    if env["type"] != "frame":
        continue  # ← descarta no-frame
    await queue.put(payload)


async def processor():
    frame_payload = await queue.get()
    await process_single_frame(ws, frame_payload, seq_counter)
```

Cliente `ws-client.js:78-84`:

```js
canSend() => ws.OPEN && bufferedAmount <= 64KB && now-lastSendMs >= 100ms (10 FPS)
sendFrame() => if (!canSend()) return false
```

Enforced por `WS_BUFFERED_LIMIT=64*1024` (`ws-client.js:21`, `config.py:10`).

**Invariante a preservar:** `frame` es el único tipo con backpressure leaky. Nuevos eventos de control **no deben** entrar a `AsyncLeakyQueue` ni respetar `canSend()`/throttle 10 FPS. Deben ser enviados/recibidos por canal paralelo priorizado.

### 3.3 Riesgo si se rompe

| Error | Efecto |
|---|---|
| Meter `enroll_sync` en leaky queue | Si usuario envía frame rapido después de `enroll_sync`, el enroll se descarta silencioso (deque maxlen=1) → pérdida de identidad |
| Aplicar `bufferedAmount>64KB` a `enroll_sync` | En burst de frames, enroll queda bloqueado indefinidamente |
| Reutilizar `type:frame` para enroll | Colisión payload, `process_single_frame` intenta `jpeg_b64` decode y falla silencioso |

## 4. `app.py` — lifespan

**Archivo:** `plataforma/webcam/backend/app.py:1` (187 líneas)

```python
# app.py:27-45
@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yolo=get_yolo_detector()
    gesture=get_gesture_recognizer()
    if yolo.is_stub: logger.info(...)
    if gesture.is_stub: logger.info(...)
    yield
    logger.info("Shutdown webcam backend")

app=FastAPI(title="webcam-backend", version="0.1.0", lifespan=lifespan)

@app.get("/health") -> {"status":"ok"}
@app.websocket("/ws/percepcion") -> await perception_ws_handler(websocket)
@app.post("/voz") -> proxy Groq→HF→Gemini→mock
```

| Hallazgo | Implicancia hibrido |
|---|---|
| `lifespan` es único punto de init | Cargar `identities.json` ahí: `identities = await load_identities(path)`; exponer vía `app.state.identities` + `app.state.identities_lock = asyncio.Lock()` |
| No hay `GET /identities` | Necesario para hidratación inicial frontend (evita WS roundtrip al cargar página) |
| `pyproject.toml` root correcta | `tool.setuptools.packages.find include=["plataforma*"]` + `conftest.py` presente — CI no romperá al añadir `backend/store.py` |
| Modelos dir | `plataforma/webcam/backend/models/` contiene `yolo11n.onnx`, `hand_landmarker.task`, `.gitignore` con `*` (todo ignorado excepto `.gitignore` mismo). `identities.json` viviría ahí pero gitignore lo oculta intencionalmente (ver `.gitignore:19-22`). Recomendación: crear `backend/models/.gitkeep` track + `identities.json` runtime gitignoreado — ya configurado |
| Import desacoplado | `ws.py:12` solo importa inference, no FSM — añadir `store` no acopla |

**Patrón lifespan extendido propuesto:**

```python
from plataforma.webcam.backend.store import IdentitiesStore

store = IdentitiesStore(path=Path(__file__).parent / "models" / "identities.json")


@asynccontextmanager
async def lifespan(app):
    # ... yolo/gesture ...
    await store.load()  # lee [] si no existe, valida schema
    app.state.store = store
    yield
```

## 5. File lock — `asyncio.Lock` vs `fcntl`

### 5.1 Tabla comparativa

| Patrón | Qué protege | Portable Win32 | Async-safe | Multi-worker (2+ uvicorn) | Complejidad | Recomendación |
|---|---|---|---|---|---|---|
| `asyncio.Lock()` | Coroutines dentro del mismo loop/event loop | ✅ Sí (puro Python) | ✅ `async with lock` fair FIFO (`docs/python: asyncio.Lock.acquire` fair) | ❌ No — locks son por proceso; 2 workers tienen locks separados | Baja: `lock=asyncio.Lock(); async with lock: read→mutate→write` | **Elegir** — proyecto corre 1 worker `uvicorn` dev/prod actual |
| `threading.Lock` | Threads OS | ✅ | ❌ Bloquea event loop (no `await`) | ❌ | No usar en async | Descartado |
| `fcntl.flock` / `fcntl.lockf` | Procesos (file descriptor) | ❌ No existe en `win32` (`Python docs: fcntl Unix only`) | ⚠️ Bloqueante syscall, necesita `run_in_executor` | ✅ Entre procesos | Media: `import fcntl` falla en Windows `ModuleNotFoundError` | Descartado — repo corre en `win32` (`env platform: win32`) |
| `msvcrt.locking` | Procesos Windows | ✅ Win32 | ⚠️ Bloqueante | ✅ | Media | Alternativa Windows-only, no portable Linux CI |
| `filelock` (PyPI) | Procesos cross-platform | ✅ | ⚠️ Sync, usar `run_in_executor` | ✅ | Añade dependencia | Overkill para single-worker; considerar solo si se escala a `uvicorn --workers 4` |
| `aiofiles` + `asyncio.Lock` | Async file I/O sin bloquear loop | ✅ | ✅ | ❌ | Media | Opcional: si `identities.json` >500KB, evita bloquear loop en `read/write` |
| Atomic write `temp+rename` | Crash safety (corte mitad escritura) | ✅ `Path.replace` atómico en POSIX/Win | — | — | Baja | **Complemento obligatorio** junto a `asyncio.Lock` |

### 5.2 Fuente `asyncio.Lock`

> "An asyncio lock can be used to guarantee exclusive access to a shared resource... `async with lock: # access shared state` ... Acquiring a lock is fair: the coroutine that proceeds will be the first coroutine that started waiting." — https://docs.python.org/3/library/asyncio-sync.html#asyncio.Lock

No es thread-safe, no acepta `timeout` (usar `asyncio.wait_for`), y se recomienda `async with`. Exactamente lo que necesita `ws.py` (single thread, múltiples coroutines `receiver`/`processor`/varios WS clientes concurrentes).

### 5.3 Recomendación concreta

```python
# plataforma/webcam/backend/store.py (nuevo)
import asyncio, json, tempfile
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class IdentitiesStore:
    def __init__(self, path: Path):
        self.path = path
        self.lock = asyncio.Lock()
        self._data: list[dict] = []

    async def load(self):
        # sync read OK (<200KB), o aiofiles si se prefiere no bloquear
        if not self.path.exists():
            self._data = []
            return
        try:
            raw = self.path.read_text(encoding="utf-8")
            arr = json.loads(raw)
            self._data = arr if isinstance(arr, list) else []
        except Exception as e:
            logger.warning("identities.json corrupto, reset []: %s", e)
            self._data = []

    async def upsert(self, rec: dict) -> dict:
        async with self.lock:
            # validar 128-d, upsert por id, promedio L2 si duplicado nombre, persistir atómico
            ...
            # write atómico
            tmp = self.path.with_suffix(".tmp")
            tmp.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            tmp.replace(self.path)  # atómico
            return rec

    async def purge(self, ids: list[str] | None, all_: bool) -> int:
        async with self.lock:
            ...
```

- Si a futuro `uvicorn --workers >1`, migrar a `filelock.FileLock(str(path)+".lock")` vía `await asyncio.to_thread(lock.acquire)` + `lock.release` + mantener `asyncio.Lock` interno (doble barrera).
- No usar `fcntl` — falla en Windows dev (`win32` env verificado).

## 6. Carga al iniciar + `GET /identities`

| Paso | Dónde | Detalle |
|---|---|---|
| 6.1 Crear `IdentitiesStore` | `backend/store.py` nuevo | Encapsula `path`, `lock`, `_data`, métodos `load/upsert/get_all/purge` con validación |
| 6.2 Lifespan | `app.py:27` | `await store.load()` antes de `yield`; asignar `app.state.store` |
| 6.3 Endpoint hidratación | `app.py` nuevo `@app.get("/identities")` | `async def list_identities(request: Request) -> list[dict]: return request.app.state.store.get_all_sync()` (copia). Frontend lo llama al montar `enrollment-panel` para merged view `localStorage ∪ servidor`. Sin auth (prototipo). |
| 6.4 Validación carga | `store.load()` | Si JSON corrupto → `[]` + `logger.warning`, no crashea lifespan (ya hace `try/except` para YOLO) |
| 6.5 Tamaño | — | `identities.json` 100 entries ≈ 200KB, lectura <5ms, no necesita paginación |

Frontend hidratación: `fetch("http://localhost:8000/identities")` → merge por `id` (server wins si colisión, o mostrar badge `local/server`).

## 7. Evento `enroll_sync` / `purge` — diseño sin romper Leaky Queue ni `WS_BUFFERED_LIMIT`

### 7.1 Problema

- `ws.py:289-295` `receiver` filtra `type!="frame"` → `continue`. Añadir `enroll_sync` ahí lo descartaría hoy.
- `ws-client.js:86-107` `sendFrame` es único sender con throttle. `enroll_sync` no debe pasar por `canSend()`.

### 7.2 Envelope propuesto (para Ticket 024)

Ampliar `EnvelopeType` en `ws.py:36` y `parse_envelope:77`:

```python
EnvelopeType = Literal[
    "frame",
    "detecciones",
    "gesto",
    "estado",
    "enroll_sync",
    "enroll_ack",
    "purge",
    "purge_ack",
]
```

Payloads:

```python
# cliente → servidor
{
    "type": "enroll_sync",
    "seq": n,
    "ts": ms,
    "payload": {
        "id": str,
        "nombre": str,
        "embedding": [float * 128],
        "ts": str,
        "frame_id": int | None,
    },
}
{
    "type": "purge",
    "seq": n,
    "ts": ms,
    "payload": {"all": bool, "ids": [str]},
}  # all:true o ids:[]

# servidor → cliente (ack dirigido, no broadcast)
{
    "type": "enroll_ack",
    "seq": m,
    "ts": ms,
    "payload": {"id": str, "status": "ok" | "error", "reason": str | None},
}
{"type": "purge_ack", "seq": m, "ts": ms, "payload": {"purged": int, "status": "ok"}}
```

Validación servidor: `isValidNombre(nombre)`, `len(embedding)==128`, `all(isinstance(x,float))`, `l2_norm≈1.0`.

### 7.3 Flujo sin Leaky Queue

```python
# ws.py receiver — bifurcación
async def receiver():
    while True:
        env = parse_envelope(await websocket.receive_text())
        if env["type"] == "frame":
            await queue.put(env["payload"])  # leaky N=1
        elif env["type"] in ("enroll_sync", "purge"):
            # procesar inline sin queue, bajo lock
            await handle_control(websocket, env, seq_counter)
        else:
            continue
```

O alternativa task separada `control_queue = asyncio.Queue()` ilimitada para control (no leaky).

**Importante:** `handle_control` debe `await websocket.send_text(json.dumps(make_envelope("enroll_ack",...)))` incrementando `seq_counter[0]` (mismo contador que `process_single_frame` comparte, no dos contadores separados).

Cliente `ws-client.js`:

```js
sendEnrollSync(rec) {
  // bypass canSend, pero respetar ws.OPEN y bufferedAmount con límite mayor
  if (!ws || ws.readyState!==WS.OPEN) return false
  // opcional: if (ws.bufferedAmount > 256*1024) retry 100ms
  ws.send(JSON.stringify({type:"enroll_sync", seq:++seq, ts:Date.now(), payload:rec}))
}
sendPurge(all, ids) { similar }
```

Tamaño `enroll_sync`: `id(7)+nombre(<32)+embedding(128*~8 chars≈1024)+ts ≈ 1.2-2.1KB` — <64KB, incluso 10 enrolls simultáneos <25KB, no presiona `WS_BUFFERED_LIMIT`. `purge` <200 bytes.

**Offline/cola:** Si `ws.readyState !== OPEN` al enrolar, `enrollment-panel.js` ya guardó en `localStorage` (render inmediato). Encolar `enroll_sync` en `localStorage:webcam.pending_sync` y reintentar en `ws.onopen` / `setInterval 2s` (definir en Ticket 024).

### 7.4 Interacción con `Leaky Queue N=1` y `WS_BUFFERED_LIMIT`

| Invariante | Preservada si... |
|---|---|
| Leaky `N=1` solo para `frame` | `enroll_sync/purge` no pasan por `AsyncLeakyQueue` |
| `WS_BUFFERED_LIMIT 64KB` cliente | `enroll_sync` hace `send` directo sin `canSend()` throttle, pero chequea `bufferedAmount <256KB` opcional |
| `seq` monotónico | Un solo `seq_counter` compartido entre `processor` y `handle_control` |
| `parse_envelope` no rechaza | Ampliar whitelist de `type` |
| `process_single_frame` intacto | No modificar firma; `processor` task sin cambios |

## 8. Riesgos y decisiones pendientes (para grilling 024/025)

| # | Riesgo | Mitigación propuesta |
|---|---|---|
| R1 | Dos clientes enrolan mismo `id` simultáneo (race) | `asyncio.Lock` serializa `upsert`; idempotencia por `id` (segundo es no-op o update) |
| R2 | Mismo `nombre` distinto `id` (duplicado lógico) | Política: si `nombre` existe con `cosineDistance <0.42` → promedia embedding `(old*count+new)/(count+1)` + L2-norm + `count++`; si `>0.55` → crear nueva entrada con sufijo `nombre#2`. Definir en 025 |
| R3 | `identities.json` corrupto (corte mitad escritura) | Atomic write `tmp→replace` + `json.loads` try/catch en `load` |
| R4 | WS desconectado al enrolar | Guardar `pending_sync` en localStorage y retry en `onopen` (Ticket 024) |
| R5 | `ws-client` reconexión exponencial `500ms→10s` | `enroll_sync` reintento con backoff 500ms cap 5s, max 3 reintentos |
| R6 | Tamaño `identities.json` ilimitado | Por ahora ilimitado (<1K identidades). Si crece >1MB, LRU por `updatedAt` (025) |
| R7 | `pyproject.toml` packages | Root `include=["plataforma*"]` OK; backend `packages=[]` legacy pero no afecta (instalable vía root). No tocar. |
| R8 | Compat `presentation` | Frontend `enrollment-panel.js` ya lee `localStorage` sync; hidratación server vía `GET /identities` + WS ack debe mostrar badge `local/server synced` (026) |

## 9. Recomendaciones para Tickets 024/025

### Para 024 — Grilling protocolo WS sync y purga dual

- **Envelope:** usar `type: enroll_sync` + `enroll_ack` y `type: purge` + `purge_ack` como arriba, **no** reutilizar `frame`. Añadir a `EnvelopeType` y `parse_envelope` whitelist.
- **Separación Leaky:** `receiver` bifurca `frame→leaky queue` vs `enroll_sync/purge → handle_control` directo. Documentar que `frame` queda `N=1` intacto.
- **Cliente:** añadir `sendEnrollSync`/`sendPurge` en `ws-client.js` que bypass `canSend()`/throttle pero chequean `ws.OPEN`. No tocar `MAX_FPS`.
- **Idempotencia:** `id` nanoid como key; servidor responde `enroll_ack {id,status}`; cliente marca `synced` en UI al recibir ack.
- **Purge:** `payload:{all:true}` borra todo `identities.json` + `localStorage` (cliente limpia al recibir `purge_ack`). `payload:{ids:[...]}` borra subset.
- **Offline:** definir `pending_sync` localStorage queue + retry en `ws.onopen`.
- **HITL grilling:** confirmar orden `localStorage write → ws.send(enroll_sync) → await enroll_ack → mostrar synced` vs optimista.

### Para 025 — Grilling schema `identities.json` y embedding promediado

- **Schema JSON:** `[{id:str, nombre:str, embedding:number[128], count:int, updatedAt:str(ISO), source:"ws"|"local"}]` — `count` para promedio, `updatedAt` para LRU.
- **Promedio:** `new_emb = l2Normalize( (old_emb*count + new_emb) / (count+1) )` (media ponderada L2-norm). Validar L2≈1.0.
- **Threshold:** reutilizar `COSINE_THRESHOLD=0.42` (no 0.4 del mapa) para match; zona gris 0.42-0.55 requiere confirmación manual.
- **Store:** `IdentitiesStore` con `asyncio.Lock` + atomic write, `load()` en `lifespan`, `GET /identities` para hidratación.
- **Concurrencia:** `asyncio.Lock` suficiente hoy (1 worker). Si se escala a multi-worker, añadir `filelock` como segunda barrera.
- **Límite:** ilimitado por ahora; definir LRU cuando `len>500` en grilling.
- **Privacidad:** mantener `.gitignore` `identities.json` y `webcam.identities` consent bloqueante del Ticket 007.

---

## 10. Archivos y líneas clave (para navegación)

```
plataforma/webcam/frontend/src/enrollment-panel.js:8       STORAGE_KEY
plataforma/webcam/frontend/src/enrollment-panel.js:9-10    THUMBS_N/GRACE
plataforma/webcam/frontend/src/enrollment-panel.js:195     evaluate()
plataforma/webcam/frontend/src/enrollment-panel.js:244     tryEnroll()
plataforma/webcam/frontend/src/face-embedding.js:8-10      EMBEDDING_DIM/THRESHOLD
plataforma/webcam/frontend/src/face-embedding.js:56        stubEmbedding
plataforma/webcam/frontend/src/face-embedding.js:76        createFaceEmbedder
plataforma/webcam/frontend/ws-client.js:21                 WS_BUFFERED_LIMIT
plataforma/webcam/frontend/ws-client.js:78                 canSend()
plataforma/webcam/frontend/ws-client.js:86                 sendFrame()
plataforma/webcam/backend/ws.py:36                         EnvelopeType
plataforma/webcam/backend/ws.py:58-80                      make/parse_envelope
plataforma/webcam/backend/ws.py:105                        LeakyQueue
plataforma/webcam/backend/ws.py:142                        AsyncLeakyQueue
plataforma/webcam/backend/ws.py:269                        perception_ws_handler
plataforma/webcam/backend/app.py:27                        lifespan
plataforma/webcam/backend/config.py:9-10                   LEAKY_QUEUE_SIZE/WS_BUFFERED
plataforma/webcam/backend/models/.gitignore:1              * (todo ignorado)
.gitignore:19-22                                            identities.json
pyproject.toml:15-16                                        packages.find include=["plataforma*"]
conftest.py:1                                               ancla pytest rootdir
```

---

## 11. Checklist entrega Ticket 023

- [x] Rama `research/023-enrollment-hibrido` creada
- [x] `docs/agents/research/023-enrollment-hibrido.md` con hallazgos scannable (tablas + líneas)
- [x] Evaluación `asyncio.Lock` vs `fcntl` con fuente `docs.python.org/3/library/asyncio-sync.html`
- [x] Recomendaciones para 024/025 sin implementar código productivo
- [ ] No cerrar ticket (solo archivo) — resto vía wayfinder 024/025
