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
  badgeContainer: badgeContainerOpt,
} = {}) {
  if (!canvas) throw new Error("[overlay] canvas requerido");
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("[overlay] 2d context no disponible");

  let lastBoxes = [];
  let lastGesto = { label: "none", conf: 0 };
  let lastEstado = "—";
  let lastFps = 0;
  let lastInferMs = 0;
  // visión viva 033/034/035 — last identidades + tracker traj
  let lastIdentidades = [];
  let trajMap = new Map(); // id -> traj [{x,y} normalizado]
  // overlay dom for badges (if provided)
  let badgeContainer = null;

  badgeContainer = badgeContainerOpt || null;
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

  function colorForEstado(estado) {
    if (estado === "confirmado") return "#22c55e";
    if (estado === "posible") return "#f59e0b";
    return "#64748b";
  }

  /**
   * Dibuja boxes normalizadas [0,1] → pixeles.
   * @param {Array<{x:number,y:number,w:number,h:number,cls:string,conf:number}>} boxes
   * @param {Array} identitiesOpt - opcional identities para badge Variante A
   */
  function drawBoxes(boxes, identitiesOpt) {
    clear();
    if (!Array.isArray(boxes)) return;
    lastBoxes = boxes;
    if (Array.isArray(identitiesOpt)) lastIdentidades = identitiesOpt;
    const W = canvas.width;
    const H = canvas.height;
    // mapear identities por box IoU para badge
    for (const [i, b] of boxes.entries()) {
      let ident = null;
      if (lastIdentidades.length) {
        // buscar identidad cuyo box IoU >0.5 o más cercano
        let best = 0;
        let bestIoU = 0;
        const iouBox = (a, c) => {
          const ax1 = a.x, ay1 = a.y, ax2 = a.x + a.w, ay2 = a.y + a.h;
          const bx1 = c.x, by1 = c.y, bx2 = c.x + c.w, by2 = c.y + c.h;
          const ix1 = Math.max(ax1, bx1), iy1 = Math.max(ay1, by1);
          const ix2 = Math.min(ax2, bx2), iy2 = Math.min(ay2, by2);
          if (ix2 <= ix1 || iy2 <= iy1) return 0;
          const inter = (ix2 - ix1) * (iy2 - iy1);
          const uni = a.w * a.h + c.w * c.h - inter;
          return uni > 0 ? inter / uni : 0;
        };
        for (const cand of lastIdentidades) {
          const cb = cand.box || cand;
          const io = iouBox(b, cb);
          if (io > bestIoU) { bestIoU = io; best = cand; }
        }
        if (bestIoU > 0.3) ident = best;
      }
      const isPerson = b.cls === "person" && ident;
      const color = isPerson ? colorForEstado(ident.estado) : COLORES[i % COLORES.length];
      // clamp [0,1] ya viene del backend, pero defendemos
      const x = Math.max(0, Math.min(1, Number(b.x) || 0)) * W;
      const y = Math.max(0, Math.min(1, Number(b.y) || 0)) * H;
      const w = Math.max(0, Math.min(1, Number(b.w) || 0)) * W;
      const h = Math.max(0, Math.min(1, Number(b.h) || 0)) * H;
      const cls = String(b.cls ?? "obj");
      const conf = Math.max(0, Math.min(1, Number(b.conf) || 0));

      ctx.strokeStyle = color;
      ctx.lineWidth = ident ? 2.5 : 2;
      ctx.strokeRect(x, y, w, h);

      // etiqueta con fondo — Variante A badge si hay identidad
      let label;
      if (ident) {
        if (ident.estado === "confirmado") label = `Hola ${ident.nombre} ✓ ${(1 - ident.cosine).toFixed(2)}`;
        else if (ident.estado === "posible") label = `posible ${ident.nombre}? ${ident.cosine.toFixed(2)}`;
        else label = `desconocido ${ident.cosine.toFixed(2)}`;
      } else {
        label = `${cls} ${(conf * 100).toFixed(0)}%`;
      }
      ctx.font = "11px ui-monospace, monospace";
      const tw = ctx.measureText(label).width + 8;
      const th = 16;
      // evitar salir por arriba
      const ly = y - th < 0 ? y : y - th;
      ctx.fillStyle = color;
      ctx.fillRect(x, ly, tw, th);
      ctx.fillStyle = ident ? "#020617" : "#0b0f14";
      ctx.fillText(label, x + 4, ly + 11);

      // trayectoria si existe
      const traj = ident ? trajMap.get(ident.id) : null;
      if (traj && traj.length > 1) {
        ctx.strokeStyle = color + "99";
        ctx.lineWidth = 2;
        ctx.beginPath();
        for (let ti = 0; ti < traj.length; ti++) {
          const px = traj[ti].x * W;
          const py = traj[ti].y * H;
          if (ti === 0) ctx.moveTo(px, py);
          else ctx.lineTo(px, py);
        }
        ctx.stroke();
      }
    }
    if (countEl) {
      const idCount = lastIdentidades.length ? ` · ${lastIdentidades.filter((x) => x.estado === "confirmado").length} id` : "";
      countEl.textContent = `${boxes.length} obj${idCount}`;
    }
  }

  function handleIdentidades(identities) {
    if (!Array.isArray(identities)) return;
    lastIdentidades = identities;
    // actualizar trajMap con nuevas cajas; dropear ids ausentes (edad implícita)
    const seen = new Set();
    for (const it of identities) {
      const box = it.box;
      if (!box) continue;
      seen.add(it.id);
      const prev = trajMap.get(it.id);
      let traj = prev ? [...prev] : [];
      const cx = box.x + box.w / 2;
      const cy = box.y + box.h / 2;
      traj.push({ x: cx, y: cy });
      if (traj.length > 12) traj = traj.slice(-12);
      trajMap.set(it.id, traj);
    }
    for (const tid of [...trajMap.keys()]) {
      if (!seen.has(tid)) trajMap.delete(tid);
    }
    // re-dibujar con identidades
    drawBoxes(lastBoxes, identities);
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

  // handlers directos para ws-client — soporta detecciones.identities opcional (034)
  function handleDetecciones(payload) {
    if (!payload) return;
    const boxes = Array.isArray(payload.boxes) ? payload.boxes : [];
    const identities = Array.isArray(payload.identities) ? payload.identities : null;
    if (identities) lastIdentidades = identities;
    drawBoxes(boxes, identities || lastIdentidades);
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
    handleIdentidades,
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
    get lastIdentidades() {
      return lastIdentidades;
    },
    canvas,
    ctx,
  };
}
