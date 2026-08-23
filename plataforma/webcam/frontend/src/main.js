import { createMockSim } from "./sim.js";
import { variants } from "./variants/index.js";
import { createPerceptionClient } from "../ws-client.js";
import { createOverlay } from "../overlay.js";
import { createVoiceChat } from "./voice-chat.js";
import { createEnrollmentPanel } from "./enrollment-panel.js";
import "../styles.css";

const sim = createMockSim();
const keys = Object.keys(variants);
let active = null;
let percepcion = null;
let wsClient = null;
let overlay = null;
let webcam = { video: null, cam: null, stream: null, raf: 0, frameId: 0 };

function currentKey() {
  return new URL(window.location.href).searchParams.get("variant") ?? keys[0];
}

function mount(key) {
  if (active) active.dispose();
  const container = document.getElementById("app");
  container.innerHTML = "";
  const spec = variants[key];
  active = spec.mount(container, sim);
  document.getElementById("variant-label").textContent = `${key.toUpperCase()} — ${spec.name}`;
  // re-attach percepcion panel after mount
  attachPercepcionPanel();
}

function switchTo(key) {
  const url = new URL(window.location.href);
  url.searchParams.set("variant", key);
  history.replaceState({}, "", url);
  mount(key);
}

function cycle(dir) {
  const i = (keys.indexOf(currentKey()) + dir + keys.length) % keys.length;
  switchTo(keys[i]);
}

document.getElementById("prev").addEventListener("click", () => cycle(-1));
document.getElementById("next").addEventListener("click", () => cycle(1));
window.addEventListener("keydown", (e) => {
  const t = e.target;
  if (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable) return;
  if (e.key === "ArrowLeft") cycle(-1);
  if (e.key === "ArrowRight") cycle(1);
});

// ---- Percepción panel (S2-D) ----
function createPercepcionDOM() {
  const panel = document.createElement("div");
  panel.id = "percepcion-panel";
  panel.className = "percepcion-panel";
  panel.innerHTML = `
    <div class="percepcion-head">
      <span>PERCEPCIÓN · WEBCAM</span>
      <span style="display:flex;align-items:center;gap:8px">
        <span id="p-dot" class="dot off" title="WS desconectado"></span>
        <span id="p-state" class="chip mission-tag" style="padding:2px 6px">desconectado</span>
      </span>
    </div>
    <div class="cam-wrap" id="cam-wrap">
      <video id="webcam" autoplay playsinline muted class="cam-hidden"></video>
      <canvas id="cam"></canvas>
      <canvas id="overlay"></canvas>
      <div id="cam-placeholder" style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:#475569;font-size:12px;background:#020617">cámara no iniciada</div>
    </div>
    <div class="percepcion-chips">
      <div id="p-gesto" class="chip off">gesto: —</div>
      <div id="p-estado" class="chip mission-tag">estado: —</div>
    </div>
    <div class="percepcion-telem">
      <div><span>fps</span><b id="p-fps">—</b></div>
      <div><span>infer</span><b id="p-infer">—</b></div>
      <div><span>det</span><b id="p-count">0 obj</b></div>
    </div>
    <div class="percepcion-controls">
      <button id="p-start">Iniciar cámara</button>
      <button id="p-mock">Mock boxes</button>
    </div>
    <div class="percepcion-hint">pulgar arriba → RUNNING · palma abierta → PAUSED · puño → ABORTED · WS <code>ws://localhost:8000/ws/percepcion</code> (buffer 64KB · 10 FPS · reconexión exponencial)</div>
  `;
  return panel;
}

function attachPercepcionPanel() {
  if (!percepcion) return;
  // try to place inside controlroom dash if present, else floating
  const dash = document.querySelector(".room-dash");
  if (dash) {
    // avoid duplicate
    if (percepcion.parentElement !== dash) dash.appendChild(percepcion);
    percepcion.style.position = "";
    percepcion.style.right = "";
    percepcion.style.top = "";
    percepcion.style.width = "";
    percepcion.style.zIndex = "";
  } else {
    // floating for hud/cinematic
    if (percepcion.parentElement !== document.body) document.body.appendChild(percepcion);
    Object.assign(percepcion.style, {
      position: "fixed",
      right: "16px",
      top: "16px",
      width: "300px",
      zIndex: "20",
      maxHeight: "90vh",
      overflowY: "auto",
    });
  }
}

function initPercepcion() {
  percepcion = createPercepcionDOM();
  // Voz chat — variante chat (ticket 003) plegada a producción + enrollment voz (005)
  let enrollmentRef = null;
  const voice = createVoiceChat({
    onSendToLLM: async (text) => {
      // Pre-llenar nombre si parece intención de registro (005)
      if (enrollmentRef && /me llamo|soy |mi nombre es/i.test(text)) {
        try {
          enrollmentRef.setNombreFromVoice(text);
        } catch {}
      }
      // Intenta backend voz si existe (ticket 004), fallback mock ya en voice-chat.js
      try {
        const r = await fetch("http://localhost:8000/voz", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ prompt: text }),
        });
        if (r.ok) {
          const j = await r.json();
          if (j && j.text) return j.text;
          if (j && j.reply) return j.reply;
        }
      } catch {}
      return null;
    },
  });
  percepcion.appendChild(voice.element);
  // Enrollment facial — Ticket 005 grilling (consent localStorage, N=5)
  const enrollment = createEnrollmentPanel({
    videoEl: null, // se asigna tras crear video
    canvasEl: null,
    onEnroll: (rec) => {
      // feedback voz al registrar
      try {
        voice.addBotMessage?.(`¡Registrado ${rec.nombre}! Quedaste en galería local (${rec.id.slice(0,4)}).`);
      } catch {}
    },
  });
  enrollmentRef = enrollment;
  percepcion.appendChild(enrollment.element);
  const video = percepcion.querySelector("#webcam");
  // actualizar ref video en enrollment (005)
  try {
    enrollment.setVideoEl(video);
  } catch {}
  const cam = percepcion.querySelector("#cam");
  const overlayCanvas = percepcion.querySelector("#overlay");
  const gestoEl = percepcion.querySelector("#p-gesto");
  const estadoEl = percepcion.querySelector("#p-estado");
  const fpsEl = percepcion.querySelector("#p-fps");
  const inferEl = percepcion.querySelector("#p-infer");
  const countEl = percepcion.querySelector("#p-count");
  const dotEl = percepcion.querySelector("#p-dot");
  const stateEl = percepcion.querySelector("#p-state");
  const placeholder = percepcion.querySelector("#cam-placeholder");
  const startBtn = percepcion.querySelector("#p-start");
  const mockBtn = percepcion.querySelector("#p-mock");

  webcam.video = video;
  webcam.cam = cam;

  overlay = createOverlay({
    canvas: overlayCanvas,
    gestoEl,
    estadoEl,
    fpsEl,
    inferEl,
    countEl,
  });

  wsClient = createPerceptionClient({
    url: "ws://localhost:8000/ws/percepcion",
    onDetecciones: (payload, env) => {
      overlay.handleDetecciones(payload);
      try {
        enrollment.handleDetecciones(payload);
      } catch {}
      if (payload && typeof payload.infer_ms === "number") {
        overlay.setTelemetry({ inferMs: payload.infer_ms, totalMs: payload.total_ms });
      }
    },
    onGesto: (payload) => {
      overlay.handleGesto(payload);
      try {
        enrollment.handleGesto(payload);
      } catch {}
    },
    onEstado: (payload) => {
      overlay.handleEstado(payload);
      try {
        enrollment.handleEstado(payload);
      } catch {}
    },
    onEnrollAck: (payload) => {
      try {
        enrollment.handleEnrollAck(payload);
      } catch {}
    },
    onPurgeAck: (payload) => {
      try {
        enrollment.handlePurgeAck(payload);
      } catch {}
    },
  });
  // hibrido: wire WS a enrollment para pending_sync flush y direct send
  try {
    enrollment.setWsClient(wsClient);
  } catch {}

  // monkey-patch onopen/onclose para dot
  const origConnect = wsClient.connect.bind(wsClient);
  wsClient.connect = () => {
    origConnect();
    // poll ws state for dot
    const check = setInterval(() => {
      const ws = wsClient.ws;
      if (!ws) return;
      if (ws.readyState === WebSocket.OPEN) {
        dotEl.className = "dot on";
        dotEl.title = "WS conectado";
        stateEl.textContent = "conectado";
        stateEl.className = "chip mission-tag RUNNING";
        try {
          enrollment.flushPending();
        } catch {}
        clearInterval(check);
      }
    }, 300);
    // onclose handler ya existe, pero añadimos intervalo para reconectar visual
    if (wsClient.ws) {
      const prevClose = wsClient.ws.onclose;
      // No override; ws-client handles reconexión exponencial internamente
    }
  };

  // hook para detectar cierre y poner dot off
  const baseOnClosePoll = setInterval(() => {
    const ws = wsClient.ws;
    if (!ws || ws.readyState === WebSocket.CLOSED || ws.readyState === WebSocket.CLOSING) {
      dotEl.className = "dot off";
      dotEl.title = "WS desconectado — reconectando…";
      stateEl.textContent = "reconectando…";
      stateEl.className = "chip mission-tag PAUSED";
    } else if (ws.readyState === WebSocket.OPEN) {
      dotEl.className = "dot on";
      stateEl.textContent = "conectado";
      stateEl.className = "chip mission-tag RUNNING";
    }
  }, 500);
  // no clear, lightweight

  wsClient.connect();

  async function startCamera() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 } },
        audio: false,
      });
      webcam.stream = stream;
      video.srcObject = stream;
      await video.play();
      placeholder.style.display = "none";
      video.classList.remove("cam-hidden");
      const w = Math.min(video.videoWidth || 640, 640);
      const h = Math.min(video.videoHeight || 480, 480);
      cam.width = w;
      cam.height = h;
      overlayCanvas.width = w;
      overlayCanvas.height = h;
      overlay.resizeFromVideo(video);
      startBtn.textContent = "Cámara activa";
      startBtn.disabled = true;
      startSendLoop();
    } catch (e) {
      console.warn("[percepcion] getUserMedia failed", e);
      placeholder.textContent = "sin cámara — usa Mock boxes o backend mock";
      placeholder.style.display = "flex";
    }
  }

  function startSendLoop() {
    let lastSend = 0;
    const loop = () => {
      webcam.raf = requestAnimationFrame(loop);
      if (!wsClient || !video.videoWidth) return;
      const now = performance.now();
      // throttled via wsClient.canSend (10 FPS + bufferedAmount)
      if (now - lastSend < 100) return; // ~10 FPS cap adicional
      if (!wsClient.canSend()) return;
      // dibujar frame actual en canvas oculto para JPEG
      const ctx = cam.getContext("2d");
      if (!ctx) return;
      ctx.drawImage(video, 0, 0, cam.width, cam.height);
      const ok = wsClient.sendFrame(cam, webcam.frameId++);
      if (ok) lastSend = now;
    };
    loop();
  }

  startBtn.addEventListener("click", startCamera);
  mockBtn.addEventListener("click", () => {
    // mock sin backend: dibuja boxes demo y gesto random
    const demoBoxes = [
      { x: 0.2, y: 0.2, w: 0.25, h: 0.4, cls: "person", conf: 0.92 },
      { x: 0.55, y: 0.3, w: 0.18, h: 0.22, cls: "chair", conf: 0.71 },
    ];
    overlay.drawBoxes(demoBoxes);
    try {
      enrollment.handleDetecciones({ boxes: demoBoxes });
    } catch {}
    const gestures = ["open_palm", "fist", "thumbs_up", "none"];
    const g = gestures[Math.floor(Math.random() * gestures.length)];
    const payload = { label: g, conf: 0.85, frame_id: webcam.frameId++ };
    overlay.setGesto(payload);
    try {
      enrollment.handleGesto(payload);
    } catch {}
    overlay.setTelemetry({ fps: 10, inferMs: 42 });
    // también mostrar que mock funciona sin WS
    placeholder.style.display = "none";
    // asegurar overlay visible aunque sin video
    if (overlayCanvas.width === 0) {
      overlayCanvas.width = 640;
      overlayCanvas.height = 480;
    }
  });

  // auto-intentar cámara si permiso ya concedido (no bloquear)
  // no auto-start para respetar autoplay policy; usuario debe click
}

// init
initPercepcion();
mount(currentKey());

// cleanup on page unload
window.addEventListener("beforeunload", () => {
  if (webcam.raf) cancelAnimationFrame(webcam.raf);
  if (webcam.stream) webcam.stream.getTracks().forEach((t) => t.stop());
  if (wsClient) wsClient.disconnect();
});
