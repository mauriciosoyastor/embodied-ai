/**
 * face-embedding.js — Ticket 002/005 research + grilling.
 * ArcFace mobilefacenet 128-d, onnxruntime. Para prototype: stub determinístico L2-norm
 * + hook para modelo real si existe. Reuso onnxruntime 1.29 sin colisión TF Lite.
 * Umbral coseno 0.42 (grilling 005), zona gris 0.42-0.55.
 */

export const EMBEDDING_DIM = 128;
export const COSINE_THRESHOLD = 0.42;
export const COSINE_GRAY = [0.42, 0.55];

export function l2Normalize(vec) {
  let sum = 0;
  for (let i = 0; i < vec.length; i++) sum += vec[i] * vec[i];
  const n = Math.sqrt(sum) || 1;
  const out = new Float32Array(vec.length);
  for (let i = 0; i < vec.length; i++) out[i] = vec[i] / n;
  return out;
}

/** Distancia coseno 1 - dot (vectores ya L2). 0 = idéntico, 2 = opuesto. */
export function cosineDistance(a, b) {
  if (!a || !b || a.length !== b.length) return 2;
  let dot = 0;
  for (let i = 0; i < a.length; i++) dot += a[i] * b[i];
  // clamp por error float
  if (dot > 1) dot = 1;
  if (dot < -1) dot = -1;
  return 1 - dot;
}

export function cosineSimilarity(a, b) {
  return 1 - cosineDistance(a, b);
}

function xorshift32(seed) {
  let x = seed >>> 0;
  return () => {
    x ^= x << 13;
    x ^= x >>> 17;
    x ^= x << 5;
    return (x >>> 0) / 0xffffffff;
  };
}

function hashString(s) {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 16777619);
  }
  return h >>> 0;
}

/** Stub determinístico: mismo seed → mismo embedding L2. */
export function stubEmbedding(seedStr) {
  const seed = hashString(seedStr || String(Date.now()));
  const rnd = xorshift32(seed || 1);
  const v = new Float32Array(EMBEDDING_DIM);
  for (let i = 0; i < EMBEDDING_DIM; i++) v[i] = rnd() * 2 - 1;
  return l2Normalize(v);
}

/** Valida nombre: letras, espacios, 2-32 chars. */
export function isValidNombre(s) {
  const t = String(s || "").trim();
  return t.length >= 2 && t.length <= 32 && /^[A-Za-zÁÉÍÓÚáéíóúÑñ ]+$/.test(t);
}

export function createFaceEmbedder({ modelUrl } = {}) {
  const url = modelUrl || "/models/mobilefacenet.onnx";
  let session = null;
  let isStub = true;
  let ready = false;

  // ort capturado para Tensor ctor (fix session.ort)
  let ortRef = null;

  async function init() {
    if (ready) return;
    try {
      // stub si no instalado — import vía variable para que Vite no resuelva en build
      const spec = "onnxruntime-web";
      const ort = await import(spec).catch(() => null);
      if (!ort) throw new Error("onnxruntime-web no disponible");
      ortRef = ort;
      if (ort.env?.wasm) {
        // Vite: wasm en public/wasm/
        try {
          ort.env.wasm.wasmPaths = "/wasm/";
        } catch {}
      }
      // probar fetch del modelo — con fallback HEAD 405 -> GET Range
      let ok = false;
      try {
        const head = await fetch(url, { method: "HEAD" }).catch(() => null);
        ok = !!(head && head.ok);
        if (!ok && head && head.status === 405) {
          const g = await fetch(url, { headers: { Range: "bytes=0-0" } }).catch(() => null);
          ok = !!(g && (g.ok || g.status === 206));
        }
      } catch {
        ok = false;
      }
      if (!ok) throw new Error(`modelo no existe ${url}`);
      session = await ort.InferenceSession.create(url, {
        executionProviders: ["wasm"],
      });
      // guardar ort para Tensor
      session._ort = ort;
      isStub = false;
    } catch {
      session = null;
      isStub = true;
    }
    ready = true;
  }

  /** @param {HTMLCanvasElement|HTMLVideoElement} cropSource - ya recortado 112x112 */
  async function embed(cropSource, seedHint) {
    if (!ready) await init();
    if (isStub || !session) {
      return stubEmbedding(seedHint || String(Date.now()));
    }
    try {
      // pipeline real: resize 112x112, RGB, normalize (-1,1) como ArcFace
      const off = document.createElement("canvas");
      off.width = 112;
      off.height = 112;
      const ctx = off.getContext("2d");
      if (!ctx) return stubEmbedding(seedHint);
      ctx.drawImage(cropSource, 0, 0, 112, 112);
      const img = ctx.getImageData(0, 0, 112, 112);
      const data = new Float32Array(1 * 3 * 112 * 112);
      for (let i = 0; i < 112 * 112; i++) {
        const r = img.data[i * 4] / 255;
        const g = img.data[i * 4 + 1] / 255;
        const b = img.data[i * 4 + 2] / 255;
        // ArcFace: (x - 0.5)/0.5 → [-1,1]
        data[i] = (r - 0.5) / 0.5;
        data[112 * 112 + i] = (g - 0.5) / 0.5;
        data[2 * 112 * 112 + i] = (b - 0.5) / 0.5;
      }
      const ort = session._ort || ortRef;
      // @ts-ignore ort types
      const feeds = { input: new ort.Tensor("float32", data, [1, 3, 112, 112]) };
      // session puede tener input name dinámico; fallback a primer key
      const out = await session.run(feeds);
      const key = Object.keys(out)[0];
      const raw = out[key].data;
      const vec = new Float32Array(raw.slice(0, EMBEDDING_DIM));
      return l2Normalize(vec);
    } catch {
      return stubEmbedding(seedHint);
    }
  }

  return {
    get isStub() {
      return isStub;
    },
    get ready() {
      return ready;
    },
    init,
    embed,
  };
}
