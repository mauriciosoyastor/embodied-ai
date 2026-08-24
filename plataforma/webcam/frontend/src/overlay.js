/**
 * overlay.js — Overlay de percepcion para S2-D (#53).
 * - Renderiza boxes normalizadas [0,1] sobre <canvas> overlay (no Three.js).
 * - Muestra gesto.label + conf, estado FSM, telemetria fps/infer_ms.
 * - Consume callbacks de ws-client.js.
 */

const COLORES = ["#58a6ff", "#3fb950", "#d29922", "#f85149", "#bc8cff", "#39c5cf"];
const GESTO_LITERALS = ["open_palm", "fist", "thumbs_up", "none"];

// v2 postura: 17 keypoints COCO, edges para esqueleto
const POSE_EDGES = [
  [0, 1],
  [0, 2],
  [1, 3],
  [2, 4],
  [5, 6],
  [5, 7],
  [7, 9],
  [6, 8],
  [8, 10],
  [5, 11],
  [6, 12],
  [11, 12],
  [11, 13],
  [13, 15],
  [12, 14],
  [14, 16],
  [0, 5],
  [0, 6],
];
const POSE_CONF_THR = 0.5;
const POSE_COLOR = "#22c55e";

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
  let lastPoses = [];
  let lastDepths = [];
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

  // v2: dibuja esqueleto 17 keypoints COCO verde si conf>0.5 — solo render, no inferencia, <5ms
  function drawPoses(poses) {
    if (!Array.isArray(poses) || !poses.length) return;
    const W = canvas.width;
    const H = canvas.height;
    ctx.save();
    ctx.strokeStyle = POSE_COLOR;
    ctx.lineWidth = 1.8;
    ctx.fillStyle = POSE_COLOR;
    for (const pose of poses) {
      if (!pose) continue;
      const rawKps = pose.keypoints || pose.kps || [];
      if (!Array.isArray(rawKps) || rawKps.length !== 17) continue;
      const confGlobal = Number(pose.conf ?? pose.conf_global ?? 1);
      if (confGlobal < POSE_CONF_THR) continue;
      // normalizar kps a [{x,y,conf}]
      const kps = rawKps.map((k) => {
        if (Array.isArray(k)) return { x: Number(k[0]) || 0, y: Number(k[1]) || 0, conf: Number(k[2] ?? 1) || 0 };
        return { x: Number(k.x) || 0, y: Number(k.y) || 0, conf: Number(k.conf ?? 1) || 0 };
      });
      // lineas COCO si ambos extremos conf>0.5
      for (const [a, b] of POSE_EDGES) {
        const ka = kps[a];
        const kb = kps[b];
        if (!ka || !kb) continue;
        if ((ka.conf || 0) < POSE_CONF_THR || (kb.conf || 0) < POSE_CONF_THR) continue;
        const ax = Math.max(0, Math.min(1, ka.x)) * W;
        const ay = Math.max(0, Math.min(1, ka.y)) * H;
        const bx = Math.max(0, Math.min(1, kb.x)) * W;
        const by = Math.max(0, Math.min(1, kb.y)) * H;
        ctx.beginPath();
        ctx.moveTo(ax, ay);
        ctx.lineTo(bx, by);
        ctx.stroke();
      }
      // puntos
      for (const kp of kps) {
        if ((kp.conf || 0) < POSE_CONF_THR) continue;
        const px = Math.max(0, Math.min(1, kp.x)) * W;
        const py = Math.max(0, Math.min(1, kp.y)) * H;
        ctx.beginPath();
        ctx.arc(px, py, 2.2, 0, Math.PI * 2);
        ctx.fill();
      }
    }
    ctx.restore();
  }

  // v2: badge z_rel en esquina bbox por depths — overlay-only, no lógica control
  function drawDepthBadges(depths, boxes) {
    if (!Array.isArray(depths) || !depths.length) return;
    if (!Array.isArray(boxes) || !boxes.length) return;
    const W = canvas.width;
    const H = canvas.height;
    ctx.save();
    ctx.font = "10px ui-monospace, monospace";
    for (let di = 0; di < depths.length; di++) {
      const d = depths[di];
      if (!d) continue;
      let z = d.z_rel ?? d.z ?? d.depth ?? null;
      if (z === null || z === undefined) continue;
      z = Number(z);
      if (!Number.isFinite(z)) continue;
      // encontrar bbox más cercana por centro
      let targetIdx = di < boxes.length ? di : -1;
      let bestDist = Infinity;
      let cxD = d.box_center?.x ?? d.cx ?? d.x ?? null;
      let cyD = d.box_center?.y ?? d.cy ?? d.y ?? null;
      if (cxD !== null && cyD !== null) {
        cxD = Number(cxD);
        cyD = Number(cyD);
        for (let bi = 0; bi < boxes.length; bi++) {
          const b = boxes[bi];
          const cxB = Number(b.x) + Number(b.w) / 2;
          const cyB = Number(b.y) + Number(b.h) / 2;
          const dist = Math.hypot(cxD - cxB, cyD - cyB);
          if (dist < bestDist) {
            bestDist = dist;
            targetIdx = bi;
          }
        }
      }
      if (targetIdx < 0 || targetIdx >= boxes.length) continue;
      if (bestDist !== Infinity && bestDist > 0.12) continue; // far, skip
      const b = boxes[targetIdx];
      const x = Math.max(0, Math.min(1, Number(b.x) || 0)) * W;
      const y = Math.max(0, Math.min(1, Number(b.y) || 0)) * H;
      const w = Math.max(0, Math.min(1, Number(b.w) || 0)) * W;
      const label = `z ${z.toFixed(2)}`;
      const tw = ctx.measureText(label).width + 8;
      const th = 14;
      const bx = x + w - tw - 2;
      const by = y + 2;
      // clamp dentro bbox si sale
      const rx = Math.max(x, Math.min(bx, x + w - tw));
      const ry = Math.max(y, Math.min(by, y + 20));
      ctx.fillStyle = "rgba(11,18,32,0.88)";
      ctx.fillRect(rx, ry, tw, th);
      ctx.strokeStyle = "#334155";
      ctx.lineWidth = 1;
      ctx.strokeRect(rx, ry, tw, th);
      ctx.fillStyle = "#e2e8f0";
      ctx.fillText(label, rx + 4, ry + 10);
    }
    ctx.restore();
  }

  /**
   * Dibuja boxes normalizadas [0,1] → pixeles.
   * + v2: overlay-only posturas/profundidades si existen (ABORTED también pinta)
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
    // v2 overlay-only: posturas y profundidades piggyback — siempre pintar incluso ABORTED, solo render <5ms
    if (lastPoses.length) drawPoses(lastPoses);
    if (lastDepths.length) drawDepthBadges(lastDepths, boxes);
  }

  // v2 helpers expuestos para test/secuencia
  function setPoses(poses) {
    if (Array.isArray(poses)) lastPoses = poses;
  }
  function setDepths(depths) {
    if (Array.isArray(depths)) lastDepths = depths;
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

  // handlers directos para ws-client — soporta detecciones.identities opcional (034) + v2 poses/depths piggyback
  function handleDetecciones(payload) {
    if (!payload) return;
    const boxes = Array.isArray(payload.boxes) ? payload.boxes : [];
    const identities = Array.isArray(payload.identities) ? payload.identities : null;
    if (identities) lastIdentidades = identities;
    // v2 piggyback: detecciones.poses / posturas y depths / profundidades — solo render, no recálcula inferencia
    const poses = payload.poses ?? payload.posturas ?? payload.postures ?? null;
    if (Array.isArray(poses)) lastPoses = poses;
    else if (poses === null || poses === undefined) {
      // mantener última si no viene (TTL 1s en backend), pero no forzar clear
    }
    const depths = payload.depths ?? payload.profundidades ?? payload.depth ?? null;
    if (Array.isArray(depths)) lastDepths = depths;
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

  // v2: scene_caption separado no pinta canvas, pero overlay expone handler por completitud
  function handleSceneCaption(_payload) {
    // no-op canvas; main.js consume leyenda dom — overlay solo mantiene contrato
  }

  function handleGesto(payload) {
    setGesto(payload);
  }

  function handleEstado(payload) {
    setEstado(payload);
  }

  return {
    drawBoxes,
    drawPoses,
    drawDepthBadges,
    setPoses,
    setDepths,
    setGesto,
    setEstado,
    setTelemetry,
    handleDetecciones,
    handleSceneCaption,
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
    get lastPoses() {
      return lastPoses;
    },
    get lastDepths() {
      return lastDepths;
    },
    canvas,
    ctx,
  };
}
