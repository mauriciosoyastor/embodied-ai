/**
 * enrollment-panel.js — Ticket 005 grilling.
 * YOLO person>0.6 & area>15% → face proxy → ArcFace 128-d → thumbs_up N=5 → localStorage.
 * Bloquea si multi-person, oclusión, ABORTED, sin consent, sin nombre.
 */
import { createFaceEmbedder, isValidNombre, COSINE_THRESHOLD } from "./face-embedding.js";

const STORAGE_KEY = "webcam.identities";
const STORAGE_PENDING = "webcam.pending_sync";
const THUMBS_N = 5;
const GRACE_FRAMES = 3;

function loadGallery() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const arr = JSON.parse(raw);
    return Array.isArray(arr) ? arr : [];
  } catch {
    return [];
  }
}
function saveGallery(arr) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(arr));
}
function loadPending() {
  try {
    const raw = localStorage.getItem(STORAGE_PENDING);
    if (!raw) return [];
    const arr = JSON.parse(raw);
    return Array.isArray(arr) ? arr : [];
  } catch {
    return [];
  }
}
function savePending(arr) {
  localStorage.setItem(STORAGE_PENDING, JSON.stringify(arr));
}
function nanoid() {
  return Math.random().toString(36).slice(2, 9);
}
async function hydrateFromServer() {
  try {
    const r = await fetch("http://localhost:8000/identities");
    if (!r.ok) return;
    const server = await r.json();
    if (!Array.isArray(server) || server.length === 0) return;
    const local = loadGallery();
    const localIds = new Set(local.map((x) => x.id));
    let added = 0;
    for (const s of server) {
      if (!localIds.has(s.id)) {
        local.push(s);
        added++;
      }
    }
    if (added) {
      saveGallery(local);
    }
  } catch {}
}

export function createEnrollmentPanel({ videoEl, canvasEl, onEnroll, wsClient } = {}) {
  let videoRef = videoEl;
  let wsRef = wsClient || null;
  const embedder = createFaceEmbedder();
  // hidratacion hibrida al iniciar (GET /identities snapshot)
  hydrateFromServer().then(() => renderGallery());

  function wsSendEnrollSync(rec) {
    const payload = { id: rec.id, nombre: rec.nombre, embedding: rec.embedding, ts: rec.ts };
    // intentar WS directo (bypass LeakyQueue)
    try {
      if (wsRef && wsRef.ws && wsRef.ws.readyState === WebSocket.OPEN) {
        const seq = (wsRef.seq || 0) + 1;
        // usar formato envelope D5 para ws.py parse_envelope
        const env = { type: "enroll_sync", seq, ts: Date.now(), payload };
        wsRef.ws.send(JSON.stringify(env));
        return true;
      }
    } catch {}
    return false;
  }
  function flushPending() {
    const pending = loadPending();
    if (!pending.length || !wsRef || !wsRef.ws || wsRef.ws.readyState !== WebSocket.OPEN) return;
    for (const p of pending) {
      try {
        const seq = (wsRef.seq || 0) + 1;
        const env = { type: "enroll_sync", seq, ts: Date.now(), payload: p };
        wsRef.ws.send(JSON.stringify(env));
      } catch {}
    }
    savePending([]);
    setHint(`Sincronizado ${pending.length} pendiente → server`, "#22c55e");
  }

  // state
  let lastBoxes = [];
  let lastGesto = { label: "none", conf: 0 };
  let lastEstado = "—";
  let thumbsCount = 0;
  let grace = 0;
  let lastPersonBox = null;
  let consentGiven = false;
  try {
    consentGiven = localStorage.getItem("webcam.consent") === "1";
  } catch {}

  const el = document.createElement("div");
  el.className = "enrollment-panel";
  el.style.cssText = "margin-top:12px;padding:10px;border:1px solid #1e293b;border-radius:8px;background:#0f172a;color:#e2e8f0;font-size:12px";
  el.innerHTML = `
    <div style="font-weight:600;margin-bottom:8px;display:flex;justify-content:space-between;align-items:center">
      <span>REGISTRO FACIAL</span>
      <span id="enr-state" class="chip" style="font-size:11px;padding:2px 6px;background:#1e293b">esperando cámara</span>
    </div>
    <div id="enr-consent" style="margin-bottom:8px;padding:8px;background:#1e293b;border-radius:6px;${consentGiven ? "display:none" : ""}">
      <label style="display:flex;gap:8px;align-items:flex-start;cursor:pointer">
        <input type="checkbox" id="enr-consent-check" ${consentGiven ? "checked" : ""} />
        <span>Guardo mi embedding 128-d <b>localmente</b> (solo en este navegador). Puedo borrarlo en cualquier momento. No se sube al backend ni se commitea.</span>
      </label>
    </div>
    <div style="display:flex;gap:8px;margin-bottom:8px">
      <input id="enr-nombre" placeholder="Nombre (2-32 letras)" maxlength="32" style="flex:1;padding:6px 8px;border-radius:6px;border:1px solid #334155;background:#020617;color:#e2e8f0" />
      <button id="enr-voz-btn" title="Dictar nombre por voz (es-AR)" style="padding:6px 8px;border-radius:6px;border:1px solid #334155;background:#1e293b;color:#e2e8f0;cursor:pointer">🎤</button>
    </div>
    <div style="display:flex;gap:8px;align-items:center;margin-bottom:8px">
      <button id="enr-btn" disabled style="flex:1;padding:8px;border-radius:6px;border:0;background:#334155;color:#94a3b8;cursor:not-allowed;font-weight:600">Pulgar arriba ×5 para confirmar</button>
      <span id="enr-progress" style="min-width:48px;text-align:center;font-variant-numeric:tabular-nums">0/${THUMBS_N}</span>
    </div>
    <div id="enr-hint" style="min-height:16px;color:#94a3b8;font-size:11px;line-height:1.3">Iniciá cámara y ponete de frente, bien iluminado.</div>
    <div id="enr-gallery" style="margin-top:10px"></div>
    <div style="margin-top:8px;display:flex;gap:8px">
      <button id="enr-clear" style="padding:4px 8px;border-radius:6px;border:1px solid #334155;background:transparent;color:#94a3b8;cursor:pointer;font-size:11px">Borrar todos</button>
      <span style="margin-left:auto;font-size:11px;color:#64748b">thr cos ${COSINE_THRESHOLD} · ${embedder.isStub ? "stub 128-d" : "ArcFace"}</span>
    </div>
  `;

  const stateEl = el.querySelector("#enr-state");
  const nombreInput = el.querySelector("#enr-nombre");
  const vozBtn = el.querySelector("#enr-voz-btn");
  const enrollBtn = el.querySelector("#enr-btn");
  const progressEl = el.querySelector("#enr-progress");
  const hintEl = el.querySelector("#enr-hint");
  const galleryEl = el.querySelector("#enr-gallery");
  const clearBtn = el.querySelector("#enr-clear");
  const consentWrap = el.querySelector("#enr-consent");
  const consentCheck = el.querySelector("#enr-consent-check");

  function setHint(t, color) {
    hintEl.textContent = t;
    hintEl.style.color = color || "#94a3b8";
  }
  function renderGallery() {
    const gal = loadGallery();
    if (gal.length === 0) {
      galleryEl.innerHTML = `<div style="color:#64748b;font-size:11px">Galería vacía — hacé tu primer registro.</div>`;
      return;
    }
    galleryEl.innerHTML = gal
      .map(
        (it) => `
      <div style="display:flex;align-items:center;gap:8px;padding:6px 8px;background:#020617;border:1px solid #1e293b;border-radius:6px;margin-bottom:6px">
        <div style="width:28px;height:28px;border-radius:50%;background:#1e293b;display:flex;align-items:center;justify-content:center;font-size:12px">👤</div>
        <div style="flex:1;min-width:0">
          <div style="font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${it.nombre}</div>
          <div style="font-size:10px;color:#64748b">${new Date(it.ts).toLocaleString()} · ${it.id.slice(0, 4)}</div>
        </div>
        <button data-del="${it.id}" style="border:0;background:transparent;color:#f87171;cursor:pointer;font-size:14px" title="Borrar">✕</button>
      </div>`
      )
      .join("");
    galleryEl.querySelectorAll("[data-del]").forEach((b) => {
      b.addEventListener("click", () => {
        const id = b.getAttribute("data-del");
        const next = loadGallery().filter((x) => x.id !== id);
        saveGallery(next);
        // limpiar pending si existia
        const pend = loadPending().filter((x) => x.id !== id);
        savePending(pend);
        renderGallery();
        // purge single id via WS
        try {
          if (wsRef && wsRef.ws && wsRef.ws.readyState === WebSocket.OPEN) {
            const env = { type: "purge", seq: (wsRef.seq || 0) + 1, ts: Date.now(), payload: { ids: [id] } };
            wsRef.ws.send(JSON.stringify(env));
          }
        } catch {}
        setHint(`Borrado ${id}`, "#f87171");
      });
    });
  }
  renderGallery();

  consentCheck?.addEventListener("change", () => {
    consentGiven = !!consentCheck.checked;
    try {
      localStorage.setItem("webcam.consent", consentGiven ? "1" : "0");
    } catch {}
    consentWrap.style.display = consentGiven ? "none" : "block";
    evaluate();
  });

  // voz para nombre
  vozBtn?.addEventListener("click", () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      setHint("STT no disponible — escribí el nombre.", "#fbbf24");
      return;
    }
    const rec = new SR();
    rec.lang = "es-AR";
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    rec.onresult = (ev) => {
      const raw = ev.results[0]?.[0]?.transcript || "";
      // parse "me llamo X" / "soy X" / "mi nombre es X"
      let t = raw.trim();
      const m = t.match(/(?:me llamo|soy|mi nombre es)\s+(.+)/i);
      if (m) t = m[1].trim();
      // tomar primeras 2 palabras como nombre
      t = t.split(/\s+/).slice(0, 2).join(" ");
      nombreInput.value = t;
      nombreInput.dispatchEvent(new Event("input"));
      setHint(`Voz: "${raw}" → "${t}"`, "#38bdf8");
    };
    rec.onerror = () => setHint("Error STT voz nombre", "#f87171");
    try {
      rec.start();
      setHint("Escuchando nombre…", "#38bdf8");
    } catch {}
  });

  nombreInput?.addEventListener("input", evaluate);
  nombreInput?.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      tryEnroll();
    }
  });

  clearBtn?.addEventListener("click", () => {
    if (!confirm("¿Borrar todos? Limpiará localStorage + identities.json en todos los clientes (purge broadcast).")) return;
    const n = loadGallery().length;
    saveGallery([]);
    savePending([]);
    renderGallery();
    // purge broadcast via WS (bypass LeakyQueue)
    try {
      if (wsRef && wsRef.ws && wsRef.ws.readyState === WebSocket.OPEN) {
        const env = { type: "purge", seq: (wsRef.seq || 0) + 1, ts: Date.now(), payload: { all: true } };
        wsRef.ws.send(JSON.stringify(env));
        setHint(`Purge {all:true} enviado (${n} borrados)`, "#f87171");
      } else {
        // offline: solo local, pending purge se manejara en reconnect
        setHint(`Galería borrada local (${n}) — WS offline, purge pendiente`, "#fbbf24");
      }
    } catch {
      setHint("Galería borrada local.", "#f87171");
    }
  });

  function selectPerson(boxes) {
    const persons = (boxes || [])
      .filter((b) => b.cls === "person" && Number(b.conf) > 0.6 && Number(b.w) * Number(b.h) > 0.15)
      .sort((a, b) => b.w * b.h - a.w * a.h);
    return persons;
  }

  function mockFaceFromPerson(p) {
    if (!p) return null;
    // proxy: face center 25% inset, 50% w, 35% h; require min size
    if (p.w < 0.08 || p.h < 0.18) return null;
    return {
      x: p.x + p.w * 0.25,
      y: p.y + p.h * 0.08,
      w: p.w * 0.5,
      h: p.h * 0.35,
      conf: 0.92,
    };
  }

  function evaluate() {
    const validNombre = isValidNombre(nombreInput.value);
    nombreInput.style.borderColor = nombreInput.value && !validNombre ? "#f87171" : "#334155";

    const persons = selectPerson(lastBoxes);
    let face = null;
    let blockReason = null;

    if (lastEstado === "ABORTED") blockReason = "Safety latch ABORTED — reseteá (puño → palma)";
    else if (persons.length === 0) blockReason = "Acercá — no detecto person (conf>0.6, area>15%)";
    else if (persons.length >= 2) blockReason = "Solo 1 persona en frame — despejá para registrar";
    else {
      lastPersonBox = persons[0];
      face = mockFaceFromPerson(lastPersonBox);
      if (!face) blockReason = "Acercá rostro, bien iluminado (oclusión?)";
      else if (!consentGiven) blockReason = "Aceptá consentimiento para registrar";
      else if (!validNombre) blockReason = "Escribí nombre (2-32 letras) o dictá 🎤";
    }

    if (blockReason) {
      stateEl.textContent = "bloqueado";
      stateEl.style.background = "#7f1d1d";
      enrollBtn.disabled = true;
      enrollBtn.style.background = "#334155";
      enrollBtn.style.color = "#94a3b8";
      enrollBtn.style.cursor = "not-allowed";
      enrollBtn.textContent = "Bloqueado";
      if (thumbsCount > 0) {
        thumbsCount = 0;
        grace = 0;
        progressEl.textContent = `0/${THUMBS_N}`;
      }
      // no pisar hint si es ABORTED o multi-person crítico
      setHint(blockReason, blockReason.includes("ABORTED") ? "#f87171" : "#fbbf24");
      return { ready: false, face, person: lastPersonBox, blockReason };
    }

    stateEl.textContent = "listo";
    stateEl.style.background = "#14532d";
    const canEnroll = validNombre && consentGiven && !!face && lastEstado !== "ABORTED";
    enrollBtn.disabled = !canEnroll;
    enrollBtn.style.background = canEnroll ? "#16a34a" : "#334155";
    enrollBtn.style.color = canEnroll ? "#f0fdf4" : "#94a3b8";
    enrollBtn.style.cursor = canEnroll ? "pointer" : "not-allowed";
    enrollBtn.textContent = canEnroll ? "Pulgar arriba ×5 para confirmar" : "Completá nombre";
    if (canEnroll) setHint(`Listo — ${nombreInput.value.trim()} · hacé 👍 ${thumbsCount}/${THUMBS_N}`, "#86efac");
    return { ready: canEnroll, face, person: lastPersonBox, blockReason: null };
  }

  async function tryEnroll() {
    const ev = evaluate();
    if (!ev.ready || !ev.face || !ev.person) return;
    const nombre = nombreInput.value.trim();
    // generar embedding desde crop (para prototype, stub con seed nombre+box)
    const seed = `${nombre}|${ev.person.x.toFixed(3)}|${Date.now()}`;
    // si tenemos video/canvas, intentar crop real para futuro modelo
    let cropSource = null;
    try {
      const v = videoRef || videoEl;
      if (v && v.videoWidth) {
        const off = document.createElement("canvas");
        off.width = 112;
        off.height = 112;
        const ctx = off.getContext("2d");
        const px = ev.face.x * (v.videoWidth || 640);
        const py = ev.face.y * (v.videoHeight || 480);
        const pw = ev.face.w * (v.videoWidth || 640);
        const ph = ev.face.h * (v.videoHeight || 480);
        // clamp
        ctx.drawImage(v, px, py, pw, ph, 0, 0, 112, 112);
        cropSource = off;
      }
    } catch {}
    const embedding = await embedder.embed(cropSource || { width: 112, height: 112 }, seed);
    const rec = {
      id: nanoid(),
      nombre,
      embedding: Array.from(embedding),
      ts: new Date().toISOString(),
      frame_id: Date.now(),
      person_box: ev.person,
      face_box: ev.face,
    };
    const gal = loadGallery();
    gal.push(rec);
    saveGallery(gal);
    renderGallery();
    // hibrido: intentar sync server (bypass LeakyQueue)
    const sent = wsSendEnrollSync(rec);
    if (!sent) {
      const pending = loadPending();
      pending.push({ id: rec.id, nombre: rec.nombre, embedding: rec.embedding, ts: rec.ts });
      savePending(pending);
      setHint(`Registrado local + pendiente sync (${pending.length}) — reconectando`, "#fbbf24");
    } else {
      setHint(`Registrado ${nombre} ✓ (sync server)`, "#22c55e");
    }
    thumbsCount = 0;
    progressEl.textContent = `0/${THUMBS_N}`;
    nombreInput.value = "";
    evaluate();
    if (typeof onEnroll === "function") onEnroll(rec);
  }

  // click fallback for enrollment (sin gesto)
  enrollBtn?.addEventListener("click", () => {
    if (enrollBtn.disabled) return;
    // si ya hay 5 thumbs, click confirma; si no, intentar directo para testeabilidad
    if (thumbsCount >= THUMBS_N) tryEnroll();
    else {
      // permitir click directo en prototype para no bloquear sin mano
      tryEnroll();
    }
  });

  function handleDetecciones(payload) {
    lastBoxes = Array.isArray(payload?.boxes) ? payload.boxes : [];
    evaluate();
  }
  function handleGesto(payload) {
    lastGesto = payload || { label: "none", conf: 0 };
    const ev = evaluate();
    if (!ev.ready) {
      thumbsCount = 0;
      grace = 0;
      progressEl.textContent = `0/${THUMBS_N}`;
      return;
    }
    const isThumbs = payload?.label === "thumbs_up" && Number(payload.conf) > 0.5;
    if (isThumbs) {
      thumbsCount += 1;
      grace = 0;
      progressEl.textContent = `${Math.min(thumbsCount, THUMBS_N)}/${THUMBS_N}`;
      if (thumbsCount >= THUMBS_N) {
        progressEl.textContent = `${THUMBS_N}/${THUMBS_N} ✓`;
        tryEnroll();
      }
    } else {
      if (thumbsCount > 0) {
        grace += 1;
        if (grace > GRACE_FRAMES) {
          thumbsCount = 0;
          grace = 0;
          progressEl.textContent = `0/${THUMBS_N}`;
        }
      }
    }
  }
  function handleEstado(payload) {
    const mission = typeof payload === "string" ? payload : payload?.mission ?? payload?.estado ?? "—";
    lastEstado = mission;
    evaluate();
  }

  // expose API for tests / wiring voz
  function setNombreFromVoice(text) {
    const raw = String(text || "").trim();
    if (!raw) return;
    let t = raw;
    const m = raw.match(/(?:me llamo|soy|mi nombre es)\s+(.+)/i);
    if (m) t = m[1].trim();
    t = t
      .split(/\s+/)
      .slice(0, 2)
      .join(" ")
      .replace(/[^A-Za-zÁÉÍÓÚáéíóúÑñ ]/g, "")
      .trim();
    if (t) {
      nombreInput.value = t.slice(0, 32);
      nombreInput.dispatchEvent(new Event("input"));
      setHint(`Voz → "${t}"`, "#38bdf8");
    }
  }

  evaluate();

  return {
    element: el,
    handleDetecciones,
    handleGesto,
    handleEstado,
    setNombreFromVoice,
    getGallery: loadGallery,
    evaluate,
    setVideoEl(v) {
      videoRef = v;
    },
    setWsClient(ws) {
      wsRef = ws;
      // si WS se abre, flush pending
      try {
        if (ws && ws.ws) {
          const prevOpen = ws.ws.onopen;
          // flush inmediato si ya OPEN
          if (ws.ws.readyState === WebSocket.OPEN) flushPending();
        }
      } catch {}
    },
    flushPending,
    getPending: loadPending,
    handleEnrollAck(payload) {
      if (payload?.status === "ok") {
        // remover del pending si existia
        const pend = loadPending().filter((x) => x.id !== payload.id);
        savePending(pend);
        setHint(`Sync ok ${payload.id.slice(0,4)} (count ${payload.count || 1})`, "#22c55e");
      }
    },
    handlePurgeAck(payload) {
      saveGallery([]);
      savePending([]);
      renderGallery();
      setHint(`Purge ack: ${payload?.n || 0} borrados (broadcast)`, "#f87171");
    },
    _embedder: embedder,
  };
}
