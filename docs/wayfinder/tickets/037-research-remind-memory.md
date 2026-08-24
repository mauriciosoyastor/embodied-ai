# Ticket 037 — Research: REMIND internals dual-bank + part/background + update gating

> Parent: `007-map-memoria-objetos.md` · Label: `wayfinder:research` · Estado: **cerrado 2026-08-24** · Tipo: AFK (research subagent) · Claim: `mauri`

## Question

¿Cómo funciona la banca dual `multi-prototype` de REMIND (`memory/`, `features/`, `REMIND_METHOD.md`, `config/default_config.yaml` en `cvar-vision-dl/remind-reid-tracker`) — `appearance + part (K-means/attention) + background` descriptors desde `DINOv3` frozen, `insert vs EMA` con `alpha`, y gating `confident (insert/merge/promote/EMA) vs AMBIGUOUS (EMA-only alpha reducido) vs WEAK (no update)` que previene corrupción de memoria? Extraer thresholds, `num_prototypes`, y si `part/background` son reinicializables per-object sin `DINOv3`.

Salida esperada: tabla de parámetros + diagrama flujo `per-frame: evidence → context → Hungarian → guards → update` y qué es portable a `mobilefacenet 128-d` sin DINOv3.

## Notes

- Consultar `arXiv:2607.09267 §3 Methodology E. Association` y `REMIND_METHOD.md`.
- Verificar `memory/` estructura `dual-bank` y `update/` gating.
- No tocar código proyecto; solo lectura externa + registro findings en branch `research/037-remind-memory`.

---

## Findings — Anexo research AFK (2026-08-24)

> Estado: **cerrado** — findings verificados. Fuentes primarias: `arXiv:2607.09267 §3`, `REMIND_METHOD.md §1-3`, `config/default_config.yaml` raw GitHub `cvar-vision-dl/remind-reid-tracker@main`, `memory/`, `features/`, `association/`, `update/`.

### 1) Respuesta corta

REMIND guarda **por objeto** 3 memorias dual-bank `work/stable` (appearance, parts, background lingual) con `max 20/20` prototipos cada canal, update `dup_thr 0.92 → EMA alpha 0.02-0.08` vs `insert novel_thr 0.78 → merge 0.90` y `promote_hits 5`. Gating robusto `STRONG full (insert/merge/promote/EMA) | AMBIGUOUS EMA-only alpha*0.2 | WEAK no update` — pero **desactivado por defecto** (`update.robust_updates.enabled:false`). Sin DINOv3 los 3 canales son reinicializables: basta sustituir `DINOv3 384-d` por `mobilefacenet 128-d` como `phi_gl` y desactivar `part attention` manteniendo `kmeans k=4`.

Flujo per-frame: `Perception (YOLO seg → DINOv3 F + parts kmeans + bg rings) → Association (sim reports → anchors → neighbor Δ+0.20 → ambiguity diagnosis → Hungarian per-class + locks 0.90/0.10 + guards) → Update (lifecycle hits/misses + dual-bank insert/EMA + neighbor graphs)`.

### 2) Arquitectura MemoryStore

```
MemoryStore
 ├─ dict[object_id → TrackedObject]
 ├─ class_index: dict[class → set[object_id]]
 ├─ pools temporales: AmbiguousTrack (TTL 6), ProvisionalNewTrack (TTL 6)
 └─ TrackedObject
     ├─ ObjectAppearanceModel  (global, global_trimmed, patch[off])
     ├─ PartModel              (kmeans, attention[off])
     ├─ LocalBackgroundModel   (inner_global, outer_global, inner_partials, outer_partials)
     ├─ NeighborGraph          (co-occurrence kernel α=0.5)
     └─ NeighborDistanceGraph  (center/contact/containment/scale)
```

Cada sub-model es `dual-bank`: `work` = observaciones recientes activas, `stable` = copia consolidada tras `promote_hits` 5 observaciones. Matching consulta ambas bancas con `proto_source_mode: default` y `object_mode: max` (max cosine).

### 3) Parámetros extraídos — `config/default_config.yaml`

| Grupo | Parámetro | Valor | Notas |
|---|---|---|---|
| **DINOv3** | `dino.model_label S / patch 16 / D 384` | `facebook/dinov3-vits16-pretrain-lvd1689m` | Frozen, `normalize_embeddings:true`, `patch_threshold 0.0` |
| **Perception object** | `global weighted true, global_trimmed keep_frac 0.50 min_patches 8` | — | `trimmed-mean` descarta outliers borde máscara |
| **Parts kmeans** | `k 4 iters 5 n_init 2 min_cluster_patches 6 merge sim_thr 0.8 keep_best` | `enabled:true` | Cluster sobre `ℓ2 patch features` → greedy merge `cos>0.8` |
| **Parts attention** | `max_seeds 3 region_frac 0.25 min_region 6 seed_score in_degree` | `enabled:false` | Requiere attention maps DINOv3, desactivable sin pérdida mayor |
| **BG rings** | `inner_radius 3 outer 6 ring_mode disjoint combine 0.7/0.3 adaptive min 12/24 max 10` | `sanitize convex_hull fill_holes` | Anillos concéntricos patch-space, `border_exclusion 1` |
| **BG prototypes** | `k_mode sqrt c 1.0 patches_per_cluster 15 k_min 4 k_max 24 min_pts 4 merge 0.92 top_n 3 min_mass 0.06 cohesion 2.0 proto medoid` | — | Ranking `mass × cohesion^2` |
| **Memory appearance** | `max_prototypes 20 stable 20 channels global/trimmed on, patch off` | — | Per-channel dual-bank |
| **Memory parts** | `max 80 per channel (kmeans, attention)` | — | Más prototipos que appearance (partes diversas) |
| **Memory BG** | `max_inner 20 outer 30 partials 60/80 globals stable 20/30` | `combine 0.6/0.4` | 4 sub-bancas |
| **Lifecycle** | `confirm_hits 2 max_misses 10 tentative/confirmed 10 inactive_ttl 0 remove false` | `NEW→TENTATIVE→CONFIRMED→INACTIVE` | Hit/miss por frame |
| **Appearance update** | `dup_thr 0.92 novel_thr 0.78 merge_thr 0.90 count_cap 10 promote_hits 5 stable_dup 0.95 stable_merge 0.96` | `quality min 8 full 24 min_quality 0.15` | Insert always |
| **Dup EMA** | `ema_on_dup false margin 0.02 alpha_min 0.02 alpha_max 0.08` | gated `s_max → alpha` | `alpha` escala con sim |
| **Parts update** | `dup 0.93 merge 0.92 greedy_1to1 true alpha 0.03-0.15 promote 5` | `merge_weight count_capped` | LRU eviction |
| **BG update** | `work_dup 0.93 work_merge 0.94 promote 5 stable_dup 0.95 alpha 0.02-0.10 globals min_quality 0.40` | `evict redundant` | `count_capped` |
| **Association weights** | `object 0.60 bg_global 0.25 bg_partials 0.05 parts 0.10` | `quality weight_floor bg 0.35 parts 0.0 obj 0.65` | `renormalize_missing true` |
| **Matching** | `match_thr 0.75 clear_margin 0.08 proto_source default` | — | `s_sim` final |
| **Hungarian locks** | `thr 0.90 gap_abs 0.10 gap_rel 0.10 dummies true dummy 0.05 conf_alpha 0.20 cap 0.72` | — | Pre-assign ovbio |
| **Robust gating** | `enabled false safe_alpha_scale 0.2` | **STRONG full, AMBIGUOUS EMA*0.2, WEAK none** | `update.robust_updates` |
| **Ambiguity** | `close_delta 0.03 strong_gap 0.08 strong_min 0.80 ambiguous_min 0.75` | — | Diagnosis per report |
| **Neighbor** | `smoothing_alpha 0.5 jaccard 0.85 debounce 3 max_neighbors 20` | — | Graph co-occurrence |

### 4) Flujo detallado

```
PERCEPTION t
  resize→align patch 14 + YOLO seg davis conf 0.7 iou 0.5 max 100 → masks
  DINOv3 forward → F Hp×Wp×D + attention (si kmeans off)
  per detection d: cov(i,j) = fraction foreground per patch
    g = Σ cov·F / Σ cov → ℓ2
    g_trim = keep top ρ=0.50 por cos(g0)
    per-patch ℓ2 retained max 512
    parts kmeans K=4 (6 pts min) → p_k ℓ2 + support/cohesion
    bg inner 3 / outer 6 rings (sanitize convex) → global ℓ2 + kmeans prototypes top 3

ASSOCIATION
  1 reports: s_obj = max cos(g_d, e_k^o) (work+stable max)
             s_parts = mean top3 best-match cos(p_i, p_j)
             s_bg = combined inner/outer (0.6/0.4) best-match
             s_sim = Σ w_c·q_c·s_c / Σ w_c·q_c  (q from patches/coverage)
  2 anchors: s≥0.75 gap≥0.08 → reliable
  3 neighbor Δ: hypothesis from anchors → bonus +0.20 / penal −0.10 capped per quality 0.35 (ver 038)
  4 diagnosis: STRONG/AMBIGUOUS/WEAK per gap/min_score
  5 Hungarian per class: score = s_sim+Δ → lock thr 0.90 gap 0.10 → dummy NEW 0.05→0.72 conf-aware → cost=−score → linear_sum_assignment → create vs match
  6 guards: identity_stability alt 0.05, ambiguous_tracks (max 3 gap 0.05), provisional_new (min 0.6), distance disambiguation max 4 group

UPDATE
  lifecycle: hit/miss, confirm 2, inactive 10
  per match: duplicate? s_max>0.92 → EMA normalize((1-α)e+αx) α∈[0.02,0.08] vs insert → merge si cos>0.90 → promote si hits≥5
  gating: STRONG insert/merge/promote/EMA | AMBIGUOUS EMA*0.2 only | WEAK skip
  parts/bg same policy (bg dup 0.93 merge 0.94 alpha 0.02-0.10)
  neighbor graphs: co-occurrence episodes + distance stats per pair
  ambiguous/provisional pools TTL 6 frames → re-evaluate o materializar
```

### 5) Qué es portable sin DINOv3 a `mobilefacenet 128-d`

| REMIND | En webcam sin DINOv3 | Portable? |
|---|---|---|
| `DINOv3 patch F 384-d` | `mobilefacenet 128-d` crop 112×112 CHW `(x-0.5)/0.5` L2 (`face-embedding.js:70 session.run [1,3,112,112]`) | Sí — pero OOD para objetos (ver 039 §3 OOD cosine 0.9) → usar como stub tipado `stubEmbedding(seed=cls+x)` hasta embedder genérico |
| `global weighted mean` | `g = ℓ2 mean` sobre 1 crop (no patches) — trivializa `cov` | Sí — `g_d = embed(crop)` directo |
| `trimmed-mean 0.5` | Sin patches, descartar: 1 proto = 1 observación | Omitir hasta DINOv3 real |
| `parts kmeans K=4 sim 0.8` | No patches → no parts; si se quiere, `part= quarter crops` 4 splits 56×56 → 4× embed (32ms×4=128ms no cabe) | Omitir — grill 040 debe decidir `parts.enabled false` para objetos, solo `appearance` |
| `bg rings inner 3 outer 6` | Requiere patch map → sustituir por `bg = crop dilated bbox 1.3×` outer ring (1 embed extra 32ms) | Omitir v1, solo `appearance` (weight bg 0.25→0) |
| `dual-bank 20/20 promote 5` | Portátil 1:1: `Map<objId, {work:[emb], stable:[emb], hits}>` `max 20/20` `JSON` `localStorage:webcam.identities` + `identities.json` `count_cap 5` (`CONTEXT.md:94`) | Sí — reusa `enrollment-panel.js:16-19` + `whiteboard.py:70 last_identidades` |
| `dup_thr 0.92 novel 0.78 merge 0.90 alpha 0.02-0.08` | Portátil directo: `cosineDistance <0.08` dup → EMA `normalize((1-α)e+αx)` `α` gated `s_max` | Sí — thresholds facial 0.42 no transfieren, usar `0.92` REMIND para objetos |
| `robust gating STRONG/AMBIGUOUS/WEAK` | Portátil a `Histéresis N=3 grace2` (`CONTEXT.md:100`): `confirmado (<0.42 N=3) → STRONG`, `posible 0.42-0.55 → AMBIGUOUS EMA*0.2`, `desconocido>0.55 → WEAK skip` + lane `ambiguous/provisional` blanca | Sí — mapea directo a 042 |
| `neighbor graphs` | Ver 038 — sí, solo `co-visible IDs` sin pose | Sí |
| `lifecycle confirm 2 max_misses 10` | Portátil a `TRACK_AGE 5` `500ms` (`CONTEXT.md:101`) — subir a 10 frames `1000ms` si objetos estáticos | Sí con ajuste |

### 6) Recomendación para grillings 040-042

- **040 dual-bank:** Activar solo `appearance global` `max 20/20` con `dup 0.92 merge 0.90 promote 5`, `parts.enabled false`, `bg.enabled false` v1. `α 0.02-0.08` EMA dup, `insert` si `s<0.78`. Banca separada `person` (facial 0.42 thr) vs genéricos (0.92 thr) — no mezclar cosines.
- **Lifecycle:** `confirm_hits 2` (ya `REID_N 3` cubre), `max_misses` subir de 5→10 para objetos estáticos indoor (1s) sin OOM.
- **Robust gating:** Activar `robust_updates.enabled true safe_alpha_scale 0.2` solo si `mobilefacenet` aporta señal; si stub OOD, mantener `enabled false` y dejar `ambiguous` blanco compensar.
- **Persistencia:** `localStorage:webcam.identities` hoy guarda `embedding[128] count updatedAt` con `count_cap 5` (`CONTEXT.md:94` `hat_e = normalize(e_old*min(N,5)+e_new)`) — extendible a `work/stable` como `work:[5] stable:[5] hits`.

### 7) Evidencia

1. `REMIND_METHOD.md §1-3` — `https://raw.githubusercontent.com/cvar-vision-dl/remind-reid-tracker/main/REMIND_METHOD.md`
2. `config/default_config.yaml` — `https://raw.githubusercontent.com/cvar-vision-dl/remind-reid-tracker/main/config/default_config.yaml` (medido 2026-08-24: `max_prototypes 20`, `dup_thr 0.92`, `robust_updates false`)
3. `arXiv:2607.09267 §3` — pipeline 3-stage + `AMBI/WEAK guards` description
4. Local: `plataforma/webcam/frontend/src/face-embedding.js:70,56`, `enrollment-panel.js:16-19,468`, `plataforma/sim/whiteboard.py:70`, `CONTEXT.md:94,100,101,104`

*Fin research 037. Listo para grilling 040 y 041.*
