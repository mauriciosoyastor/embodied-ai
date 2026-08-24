/**
 * objeto-memory.js — Ticket 040/041/042 memoria objetos destilada REMIND.
 * Dual-bank work/stable 8/8 + dup0.92 merge0.90 promote5 α0.02-0.08 (AMBIGUOUS*0.2)
 * Bancas separadas: person (thr 0.42) vs objetos (thr 0.92).
 * NeighborGraph co-visible D5 debounce3 α0.5 Δ+0.20/Δ-0.10 veto≤3 TTL10 episodios.
 * Sin parts/BG v1 solo appearance global. ABORTED overlay-only.
 */

const MAX_WORK = 8;
const MAX_STABLE = 8;
const DUP_THR = 0.92;
const NOVEL_THR = 0.78;
const MERGE_THR = 0.90;
const PROMOTE_HITS = 5;
const COUNT_CAP = 10;
const ALPHA_MIN = 0.02;
const ALPHA_MAX = 0.08;
const SAFE_ALPHA_SCALE = 0.2;
const NEIGHBOR_MAX = 20;
const NEIGHBOR_SMOOTH_ALPHA = 0.5;
const NEIGHBOR_DEBOUNCE = 3;
const DELTA_POS = 0.20;
const DELTA_NEG = 0.10;
const TTL_EPISODES = 10;

function cosineSimilarity(a, b) {
  let dot = 0, na = 0, nb = 0;
  for (let i = 0; i < a.length; i++) { dot += a[i]*b[i]; na += a[i]*a[i]; nb += b[i]*b[i]; }
  const d = Math.sqrt(na)*Math.sqrt(nb);
  return d < 1e-12 ? 0 : dot/d;
}
function l2Normalize(v) {
  let n = 0; for (let i=0;i<v.length;i++) n+=v[i]*v[i]; n=Math.sqrt(n);
  if (n<1e-12) return v;
  const out = new Float32Array(v.length); for(let i=0;i<v.length;i++) out[i]=v[i]/n; return out;
}
function emaUpdate(prev, obs, alpha) {
  const out = new Float32Array(prev.length);
  for(let i=0;i<prev.length;i++) out[i]=(1-alpha)*prev[i]+alpha*obs[i];
  return l2Normalize(out);
}

export function createObjetoMemory({ banca = "objetos" } = {}) {
  // thr separado
  const DUP = banca === "person" ? 0.58 : DUP_THR; // cos 0.42 thr facial → dup 1-0.42=0.58
  // store por objId: { work: [{emb,hits}], stable: [], neighbor: Map<dstId, edge>, episodeCount, episodeIdx, lastFrameId }
  const store = new Map();

  function getOrCreate(objId) {
    if (!store.has(objId)) store.set(objId, { work:[], stable:[], hits:0, misses:0, neighbor:new Map(), episodeCount:0, episodeIdx:-1, lastFrameId:null, stableContext:null, pendingContext:null, pendingHits:0, state:"NEW" });
    return store.get(objId);
  }

  function alphaFor(sMax) {
    // gated por s_max: linear 0.02→0.08
    const t = Math.max(0, Math.min(1, (sMax - 0.5)/0.5));
    return ALPHA_MIN + t*(ALPHA_MAX-ALPHA_MIN);
  }

  function updateEmbedding(objId, embedding, gating) {
    // gating: STRONG | AMBIGUOUS | WEAK
    if (gating === "WEAK") return { action:"skip" };
    const scale = gating === "AMBIGUOUS" ? SAFE_ALPHA_SCALE : 1.0;
    const rec = getOrCreate(objId);
    const emb = l2Normalize(embedding);
    // duplicate check
    let bestIdx = -1, bestSim = -1;
    for(let i=0;i<rec.work.length;i++){ const s=cosineSimilarity(emb, rec.work[i].emb); if(s>bestSim){bestSim=s; bestIdx=i;}}
    if (bestSim > DUP && bestIdx>=0) {
      const alpha = alphaFor(bestSim)*scale;
      rec.work[bestIdx].emb = emaUpdate(rec.work[bestIdx].emb, emb, alpha);
      rec.work[bestIdx].hits = Math.min(COUNT_CAP, rec.work[bestIdx].hits+1);
      // merge maintenance
      for(let i=0;i<rec.work.length;i++) for(let j=i+1;j<rec.work.length;j++){
        if(cosineSimilarity(rec.work[i].emb, rec.work[j].emb) > MERGE_THR){
          // keep best hits
          const keep = rec.work[i].hits >= rec.work[j].hits ? i : j;
          const drop = keep===i? j : i;
          const a=rec.work[keep], b=rec.work[drop];
          a.emb = l2Normalize(new Float32Array(a.emb.map((v,k)=> (v*a.hits + b.emb[k]*b.hits)/(a.hits+b.hits))));
          a.hits = Math.min(COUNT_CAP, a.hits+b.hits);
          rec.work.splice(drop,1);
          break;
        }
      }
      // promote
      if(rec.work[bestIdx].hits >= PROMOTE_HITS && rec.stable.length < MAX_STABLE){
        if(!rec.stable.some(s=> cosineSimilarity(s.emb, rec.work[bestIdx].emb) > 0.95)){
          rec.stable.push({ emb: new Float32Array(rec.work[bestIdx].emb), hits: rec.work[bestIdx].hits });
          if(rec.stable.length> MAX_STABLE) rec.stable.shift();
        }
      }
      return { action:"ema", alpha: alphaFor(bestSim)*scale, sim:bestSim };
    }
    // insert
    if (gating === "AMBIGUOUS") return { action:"skip_ambiguous_insert" };
    if (rec.work.length >= MAX_WORK) {
      // evict most redundant (max sim to others) or LRU
      let worst=-1, worstSim=-1;
      for(let i=0;i<rec.work.length;i++){ let m=-1; for(let j=0;j<rec.work.length;j++) if(i!==j) m=Math.max(m, cosineSimilarity(rec.work[i].emb, rec.work[j].emb)); if(m>worstSim){worstSim=m; worst=i;}}
      rec.work.splice(worst>=0?worst:0,1);
    }
    rec.work.push({ emb, hits:1 });
    return { action:"insert", sim: bestSim };
  }

  // lifecycle
  function hit(objId){ const r=getOrCreate(objId); r.hits++; r.misses=0; if(r.hits>=2 && r.state==="NEW") r.state="TENTATIVE"; if(r.hits>=PROMOTE_HITS && r.state==="TENTATIVE") r.state="CONFIRMED"; }
  function miss(objId){ const r=store.get(objId); if(!r) return; r.misses++; r.hits=0; if(r.misses>=10) r.state="INACTIVE"; }
  function getState(objId){ return store.get(objId)?.state || "UNKNOWN"; }

  // neighbor graph
  let globalEpisodeIdx = 0;
  function bumpNeighbors(objIds, frameId) {
    // objIds = array co-visible en este frame D5 Whitelist 12 (sin person)
    // debounce: episode racha 3 frames mismos sets
    // simplificado: si mismos objIds que last, pendingHits++ hasta 3 → episodio
    const key = objIds.slice().sort().join(",");
    // por cada objId, mantener pendingContext
    for(const oid of objIds){
      const rec=getOrCreate(oid);
      const ctx = new Set(objIds.filter(id=> id!==oid));
      const same = rec.pendingContext && [...rec.pendingContext].sort().join(",") === [...ctx].sort().join(",");
      if(same) rec.pendingHits++; else { rec.pendingContext=ctx; rec.pendingHits=1; }
      // force episode every 3 frames ya cubierto por pendingHits 3
    }
    // si pendingHits >= NEIGHBOR_DEBOUNCE → commit episode
    const commitIds = objIds.filter(oid=> (store.get(oid)?.pendingHits||0) >= NEIGHBOR_DEBOUNCE);
    if(commitIds.length===0) return;
    globalEpisodeIdx++;
    for(const oid of commitIds){
      const rec=getOrCreate(oid);
      rec.episodeCount++;
      globalEpisodeIdx = Math.max(globalEpisodeIdx, rec.episodeCount);
      const ctx = rec.pendingContext || new Set();
      for(const dst of ctx){
        if(!rec.neighbor.has(dst)) rec.neighbor.set(dst, { coocCount:1, weight:1, lastEpisode: globalEpisodeIdx, firstTs: Date.now(), lastTs: Date.now() });
        else { const e=rec.neighbor.get(dst); e.coocCount++; e.weight+=1; e.lastEpisode=globalEpisodeIdx; e.lastTs=Date.now(); }
      }
      // trim max 20 por weight
      if(rec.neighbor.size> NEIGHBOR_MAX){
        const sorted=[...rec.neighbor.entries()].sort((a,b)=> b[1].weight - a[1].weight);
        rec.neighbor = new Map(sorted.slice(0, NEIGHBOR_MAX));
      }
      rec.pendingHits=0;
    }
  }
  function pConditional(srcId, dstId, vocabSize) {
    const rec=store.get(srcId); if(!rec) return 0;
    const cA=rec.episodeCount;
    const e=rec.neighbor.get(dstId);
    const cAB=e? e.coocCount:0;
    // TTL: ignorar si lastEpisode muy viejo
    if(e && (globalEpisodeIdx - e.lastEpisode > TTL_EPISODES)) return NEIGHBOR_SMOOTH_ALPHA / (cA + NEIGHBOR_SMOOTH_ALPHA*(vocabSize||rec.neighbor.size||1));
    const a=NEIGHBOR_SMOOTH_ALPHA, V=Math.max(1, vocabSize||rec.neighbor.size||1);
    const denom=cA + a*V;
    if(denom<1e-12) return 0;
    return (cAB + a)/denom;
  }
  function neighborBonus(srcId, candidateId, quality) {
    // simplificado Δ+0.20 * quality si pConditional > threshold, Δ-0.10 si veto
    const q=Math.max(0,Math.min(1, quality||0.5));
    const p=pConditional(srcId, candidateId);
    // si p > 0.25 y quality>0.35 → bonus
    if(p>0.25 && q>0.35) return Math.min(DELTA_POS, 0.4*q);
    if(p<0.05 && q>0.6) return -Math.min(DELTA_NEG, 0.2*q);
    return 0;
  }

  return { store, updateEmbedding, hit, miss, getState, bumpNeighbors, pConditional, neighborBonus, _alphaFor: alphaFor, TTL_EPISODES };
}
