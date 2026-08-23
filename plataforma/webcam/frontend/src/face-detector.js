/**
 * face-detector.js — Ticket 031 / 033 / 036.
 * BlazeFace short-range via @mediapipe/tasks-vision — fallback isStub.
 * Reusa patrón face-embedding.js: dynamic import + HEAD probe, wasm mismo que hand_landmarker.
 */

export function createFaceDetector({
  modelUrl = "/models/blaze_face_short_range.tflite",
  wasmBase = "https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@1.0.1/wasm",
} = {}) {
  let detector = null;
  let isStub = true;
  let ready = false;
  let vision = null;

  const DEFAULT_W = 640;
  const DEFAULT_H = 480;

  function toNorm(bb, W, H) {
    const x = Math.max(0, Math.min(1, (bb.originX ?? 0) / W));
    const y = Math.max(0, Math.min(1, (bb.originY ?? 0) / H));
    const w = Math.max(0, Math.min(1, (bb.width ?? 0) / W));
    const h = Math.max(0, Math.min(1, (bb.height ?? 0) / H));
    const conf = Math.max(0, Math.min(1, Number(bb.confidence ?? 0.92)));
    return { x, y, w, h, conf };
  }

  async function init() {
    if (ready) return;
    try {
      const spec = "@mediapipe/tasks-vision";
      const mp = await import(spec).catch(() => null);
      if (!mp) throw new Error("mediapipe tasks-vision no disponible");
      // probe modelo HEAD/GET Range como face-embedding.js
      let ok = false;
      try {
        const head = await fetch(modelUrl, { method: "HEAD" }).catch(() => null);
        ok = !!(head && head.ok);
        if (!ok && head && head.status === 405) {
          const g = await fetch(modelUrl, { headers: { Range: "bytes=0-0" } }).catch(() => null);
          ok = !!(g && (g.ok || g.status === 206));
        }
      } catch {
        ok = false;
      }
      if (!ok) throw new Error(`modelo no existe ${modelUrl}`);
      vision = await mp.FilesetResolver.forVisionTasks(wasmBase);
      detector = await mp.FaceDetector.createFromOptions(vision, {
        baseOptions: { modelAssetPath: modelUrl },
        runningMode: "VIDEO",
        minDetectionConfidence: 0.7,
        minSuppressionThreshold: 0.3,
      });
      isStub = false;
    } catch {
      detector = null;
      vision = null;
      isStub = true;
    }
    ready = true;
  }

  /**
   * Detecta cara más grande normalizada [0,1]. Retorna {x,y,w,h,conf} o null.
   * @param {HTMLVideoElement|HTMLCanvasElement|HTMLImageElement} source
   * @param {number} ts - performance.now()
   */
  function detect(source, ts) {
    if (isStub || !detector || !source) return null;
    try {
      const W = source.videoWidth || source.width || DEFAULT_W;
      const H = source.videoHeight || source.height || DEFAULT_H;
      const res = detector.detectForVideo(source, ts ?? performance.now());
      const dets = res?.detections;
      if (!Array.isArray(dets) || dets.length === 0) return null;
      // elegir mayor área (como enrollment-panel selectPerson)
      let best = dets[0];
      let bestArea = (best.boundingBox?.width || 0) * (best.boundingBox?.height || 0);
      for (let i = 1; i < dets.length; i++) {
        const d = dets[i];
        const area = (d.boundingBox?.width || 0) * (d.boundingBox?.height || 0);
        if (area > bestArea) {
          best = d;
          bestArea = area;
        }
      }
      const bb = best.boundingBox;
      if (!bb) return null;
      // categorías -> confidence
      const cat = Array.isArray(best.categories) && best.categories[0] ? best.categories[0] : null;
      const conf = cat ? Number(cat.score ?? cat.confidence ?? 0.92) : 0.92;
      return toNorm({ originX: bb.originX, originY: bb.originY, width: bb.width, height: bb.height, confidence: conf }, W, H);
    } catch {
      return null;
    }
  }

  /**
   * Detecta todas las caras (hasta 3) normalizadas — para re-id multi.
   */
  function detectAll(source, ts, maxFaces = 3) {
    if (isStub || !detector || !source) return [];
    try {
      const W = source.videoWidth || source.width || DEFAULT_W;
      const H = source.videoHeight || source.height || DEFAULT_H;
      const res = detector.detectForVideo(source, ts ?? performance.now());
      const dets = res?.detections;
      if (!Array.isArray(dets) || dets.length === 0) return [];
      const sorted = [...dets].sort((a, b) => {
        const aa = (a.boundingBox?.width || 0) * (a.boundingBox?.height || 0);
        const bb = (b.boundingBox?.width || 0) * (b.boundingBox?.height || 0);
        return bb - aa;
      });
      const out = [];
      for (let i = 0; i < Math.min(sorted.length, maxFaces); i++) {
        const d = sorted[i];
        const bb = d.boundingBox;
        if (!bb) continue;
        const cat = Array.isArray(d.categories) && d.categories[0] ? d.categories[0] : null;
        const conf = cat ? Number(cat.score ?? cat.confidence ?? 0.92) : 0.92;
        out.push(toNorm({ originX: bb.originX, originY: bb.originY, width: bb.width, height: bb.height, confidence: conf }, W, H));
      }
      return out;
    } catch {
      return [];
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
    detect,
    detectAll,
    get _detector() {
      return detector;
    },
  };
}
