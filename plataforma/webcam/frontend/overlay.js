/**
 * overlay.js — Overlay de percepcion para S2-D (#53).
 * - Renderiza boxes normalizadas [0,1] sobre <canvas> overlay (no Three.js).
 * - Muestra gesto.label + conf, estado FSM, telemetria fps/infer_ms.
 * - Consume callbacks de ws-client.js.
 */

const COLORES = ["#58a6ff", "#3fb950", "#d29922", "#f85149", "#bc8cff", "#39c5cf"];
const GESTO_LITERALS = ["open_palm", "fist", "thumbs_up", "none"];

export function createOverlay({
  canvas,
  gestoEl,
  estadoEl,
  fpsEl,
  inferEl,
  totalEl,
  countEl,
} = {}) {
  if (!canvas) throw new Error("[overlay] canvas requerido");
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("[overlay] 2d context no disponible");

  let lastBoxes = [];
  let lastGesto = { label: "none", conf: 0 };
  let lastEstado = "—";
  let lastFps = 0;
  let lastInferMs = 0;

  // Para FPS local si backend no manda timing
  let frameCount = 0;
  let lastFpsTs = performance.now();

  function resizeFromVideo(video) {
    if (!video) return;
    const w = video.videoWidth || 640;
    const h = video.videoHeight || 480;
    // mantener ratio 640 max, pero overlay usa tamaño del video/canvas fuente
    const cw = Math.min(w, 640);
    const ch = Math.min(h, 480);
    if (canvas.width !== cw || canvas.height !== ch) {
      canvas.width = cw;
      canvas.height = ch;
    }
  }

  function clear() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
  }

  /**
   * Dibuja boxes normalizadas [0,1] → pixeles.
   * @param {Array<{x:number,y:number,w:number,h:number,cls:string,conf:number}>} boxes
   */
  function drawBoxes(boxes) {
    clear();
    if (!Array.isArray(boxes)) return;
    lastBoxes = boxes;
    const W = canvas.width;
    const H = canvas.height;
    for (const [i, b] of boxes.entries()) {
      const color = COLORES[i % COLORES.length];
      // clamp [0,1] ya viene del backend, pero defendemos
      const x = Math.max(0, Math.min(1, Number(b.x) || 0)) * W;
      const y = Math.max(0, Math.min(1, Number(b.y) || 0)) * H;
      const w = Math.max(0, Math.min(1, Number(b.w) || 0)) * W;
      const h = Math.max(0, Math.min(1, Number(b.h) || 0)) * H;
      const cls = String(b.cls ?? "obj");
      const conf = Math.max(0, Math.min(1, Number(b.conf) || 0));

      ctx.strokeStyle = color;
      ctx.lineWidth = 2;
      ctx.strokeRect(x, y, w, h);

      // etiqueta con fondo
      const label = `${cls} ${(conf * 100).toFixed(0)}%`;
      ctx.font = "11px ui-monospace, monospace";
      const tw = ctx.measureText(label).width + 8;
      const th = 16;
      // evitar salir por arriba
      const ly = y - th < 0 ? y : y - th;
      ctx.fillStyle = color;
      ctx.fillRect(x, ly, tw, th);
      ctx.fillStyle = "#0b0f14";
      ctx.fillText(label, x + 4, ly + 11);
    }
    if (countEl) countEl.textContent = `${boxes.length} obj`;
  }

  function setGesto(payload) {
    // payload {label, conf, frame_id}
    if (!payload || typeof payload.label !== "string") return;
    lastGesto = payload;
    if (gestoEl) {
      const label = GESTO_LITERALS.includes(payload.label) ? payload.label : "none";
      const conf = (Number(payload.conf) || 0).toFixed(2);
      gestoEl.textContent = `gesto: ${label} · ${conf}`;
      gestoEl.classList.toggle("on", label !== "none");
      gestoEl.classList.toggle("off", label === "none");
      // color por gesto
      gestoEl.dataset.label = label;
    }
  }

  function setEstado(payload) {
    // payload puede ser {mission} o string
    const mission = typeof payload === "string" ? payload : payload?.mission ?? payload?.estado ?? "—";
    lastEstado = mission;
    if (estadoEl) {
      estadoEl.textContent = `estado: ${mission}`;
      estadoEl.dataset.estado = mission;
      estadoEl.className = `chip mission-tag ${mission}`;
    }
  }

  function setTelemetry({ fps, inferMs, totalMs, yoloMs, manoMs } = {}) {
    if (typeof fps === "number") lastFps = fps;
    if (typeof inferMs === "number") lastInferMs = inferMs;
    if (fpsEl) fpsEl.textContent = `${Math.round(lastFps)} fps`;
    if (inferEl) inferEl.textContent = `${Math.round(lastInferMs)} ms`;
    if (totalEl) {
      const t = typeof totalMs === "number" ? `${Math.round(totalMs)} ms` : `${Math.round(lastInferMs)} ms`;
      totalEl.textContent = t;
    }
    // opcional yolo/mano breakdown si se quiere mostrar en tooltip
    if (canvas) {
      canvas.title =
        typeof yoloMs === "number" && typeof manoMs === "number"
          ? `yolo ${Math.round(yoloMs)} ms · mano ${Math.round(manoMs)} ms`
          : "";
    }
  }

  // handlers directos para ws-client
  function handleDetecciones(payload) {
    if (!payload) return;
    const boxes = Array.isArray(payload.boxes) ? payload.boxes : [];
    drawBoxes(boxes);
    // si payload trae timing, usarlo; si no, estimar fps local
    frameCount++;
    const now = performance.now();
    if (now - lastFpsTs > 1000) {
      const fps = (frameCount * 1000) / (now - lastFpsTs);
      setTelemetry({ fps });
      frameCount = 0;
      lastFpsTs = now;
    }
  }

  function handleGesto(payload) {
    setGesto(payload);
  }

  function handleEstado(payload) {
    setEstado(payload);
  }

  return {
    drawBoxes,
    setGesto,
    setEstado,
    setTelemetry,
    handleDetecciones,
    handleGesto,
    handleEstado,
    resizeFromVideo,
    clear,
    get lastBoxes() {
      return lastBoxes;
    },
    get lastGesto() {
      return lastGesto;
    },
    get lastEstado() {
      return lastEstado;
    },
    canvas,
    ctx,
  };
}
