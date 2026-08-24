/**
 * ws-client.js — Cliente WebSocket /ws/percepcion (S2-D).
 * Contrato D5 (#43): envelope {type,seq,ts,payload}, type ∈ {frame,detecciones,gesto,estado}
 * Leaky queue N=1: cliente throttled 10 FPS + skip si ws.bufferedAmount > 64KB.
 * Reconexión exponencial 500ms → 10s cap.
 *
 * Uso:
 *   const client = createPerceptionClient({ url: "ws://localhost:8000/ws/percepcion" });
 *   client.onDetecciones = (payload, env) => overlay.draw(payload.boxes);
 *   client.onGesto = (payload) => overlay.setGesto(payload);
 *   client.onEstado = (payload) => overlay.setEstado(payload);
 *   client.connect();
 *   // en loop rAF throttled 10Hz:
 *   if (client.canSend()) client.sendFrame(canvas, frameId++);
 */

// Leaky queue N=1 — ver D5 Answer
// Cliente: si ws.bufferedAmount > 64KB se salta el frame (no encola)
// Servidor: cola capacidad 1 — descarta anterior si llega nuevo antes de inferir

export const WS_BUFFERED_LIMIT = 64 * 1024; // 64KB D5 fast
export const WS_BUFFERED_LIMIT_FAST = WS_BUFFERED_LIMIT;
export const WS_BUFFERED_LIMIT_SLOW = 64 * 1024; // v2 slow (VLM/scene_caption) mismo límite pero check diferenciado
export const MAX_FPS = 10;
export const MAX_FPS_SLOW = 1; // v2 scene_caption 1Hz
export const RECONNECT_INITIAL_MS = 500;
export const RECONNECT_MAX_MS = 10000;

export function createPerceptionClient({ url, onDetecciones, onGesto, onEstado, onEnrollAck, onPurgeAck, onSceneCaption } = {}) {
  const endpoint = url || "ws://localhost:8000/ws/percepcion";
  let ws = null;
  let seq = 0;
  let reconnectDelay = RECONNECT_INITIAL_MS;
  let reconnectTimer = null;
  let frameId = 0;
  let lastSendMs = 0;
  let closedManually = false;

  const client = {
    onDetecciones: onDetecciones || (() => {}),
    onGesto: onGesto || (() => {}),
    onEstado: onEstado || (() => {}),
    onEnrollAck: onEnrollAck || (() => {}),
    onPurgeAck: onPurgeAck || (() => {}),
    onSceneCaption: onSceneCaption || (() => {}),

    connect() {
      // evitar doble connect
      if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return;
      closedManually = false;
      ws = new WebSocket(endpoint);

      ws.onopen = () => {
        reconnectDelay = RECONNECT_INITIAL_MS;
      };

      ws.onmessage = (ev) => {
        try {
          const env = JSON.parse(ev.data);
          if (!env.type || !env.payload) return;
          // v2: detecciones piggyback poses/depths (poses/posturas, depths/profundidades) pasa directo a onDetecciones
          if (env.type === "detecciones") client.onDetecciones(env.payload, env);
          else if (env.type === "gesto") client.onGesto(env.payload, env);
          else if (env.type === "estado") client.onEstado(env.payload, env);
          else if (env.type === "scene_caption") client.onSceneCaption(env.payload, env);
          else if (env.type === "enroll_ack") client.onEnrollAck(env.payload, env);
          else if (env.type === "purge_ack") client.onPurgeAck(env.payload, env);
        } catch (e) {
          console.warn("[ws-client] parse error", e);
        }
      };

      ws.onclose = () => {
        if (closedManually) return;
        // reconexión exponencial cap 10s
        if (reconnectTimer) clearTimeout(reconnectTimer);
        reconnectTimer = setTimeout(() => client.connect(), reconnectDelay);
        reconnectDelay = Math.min(reconnectDelay * 2, RECONNECT_MAX_MS);
      };

      ws.onerror = () => {
        try {
          ws.close();
        } catch {}
      };
    },

    canSend() {
      if (!ws || ws.readyState !== WebSocket.OPEN) return false;
      if (ws.bufferedAmount > WS_BUFFERED_LIMIT_FAST) return false; // leaky N=1 cliente fast 10Hz
      const now = Date.now();
      if (now - lastSendMs < 1000 / MAX_FPS) return false; // throttled 10 FPS
      return true;
    },

    // v2: slow channel check diferenciado (scene_caption 1Hz) — mismo WS pero gate separado
    canSendSlow() {
      if (!ws || ws.readyState !== WebSocket.OPEN) return false;
      if (ws.bufferedAmount > WS_BUFFERED_LIMIT_SLOW) return false;
      return true;
    },

    sendFrame(canvasOrVideo, fid) {
      if (!client.canSend()) return false;
      const id = fid ?? frameId++;
      const jpeg_b64 = canvasOrVideoToJpegB64(canvasOrVideo);
      if (!jpeg_b64) return false;
      const width = canvasOrVideo.width || canvasOrVideo.videoWidth || 640;
      const height = canvasOrVideo.height || canvasOrVideo.videoHeight || 640;
      seq += 1;
      const envelope = {
        type: "frame",
        seq,
        ts: Date.now(),
        payload: { frame_id: id, jpeg_b64, width, height },
      };
      try {
        ws.send(JSON.stringify(envelope));
        lastSendMs = Date.now();
        return true;
      } catch {
        return false;
      }
    },

    disconnect() {
      closedManually = true;
      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }
      if (ws) {
        try {
          ws.close();
        } catch {}
      }
      ws = null;
    },

    get seq() {
      return seq;
    },
    get ws() {
      return ws;
    },
    get reconnectDelayMs() {
      return reconnectDelay;
    },
  };
  return client;
}

function canvasOrVideoToJpegB64(source) {
  try {
    if (source && typeof source.toDataURL === "function") {
      const dataUrl = source.toDataURL("image/jpeg", 0.75);
      return dataUrl.split(",")[1] || "";
    }
    if (source && source.tagName === "VIDEO") {
      const c = document.createElement("canvas");
      c.width = Math.min(source.videoWidth || 640, 640);
      c.height = Math.min(source.videoHeight || 640, 640);
      const ctx = c.getContext("2d");
      if (!ctx) return "";
      ctx.drawImage(source, 0, 0, c.width, c.height);
      return c.toDataURL("image/jpeg", 0.75).split(",")[1] || "";
    }
    return "";
  } catch {
    return "";
  }
}

// 041 Q2 C — fallback dinámico WS D5 ↔ WebRTC Jetson (040)
// Probe HEAD https://<JETSON-IP>:8554/webrtc/signal 200→webrtc else ws.
// Headless/node sin fetch → 'ws' inmediato para pytest/CI.
export async function selectTransport({
  jetsonHost,
  webrtcSignalPath = "/webrtc/signal",
  timeoutMs = 800,
} = {}) {
  const host =
    jetsonHost ||
    (typeof location !== "undefined" && location.hostname) ||
    "localhost";
  const url = `https://${host}:8554${webrtcSignalPath}`;
  if (typeof fetch !== "function") return "ws";
  try {
    const ctrl = typeof AbortController !== "undefined" ? new AbortController() : null;
    const timer = ctrl ? setTimeout(() => ctrl.abort(), timeoutMs) : null;
    const res = await fetch(url, {
      method: "HEAD",
      cache: "no-store",
      signal: ctrl ? ctrl.signal : undefined,
    });
    if (timer) clearTimeout(timer);
    return res.ok ? "webrtc" : "ws";
  } catch {
    return "ws";
  }
}
