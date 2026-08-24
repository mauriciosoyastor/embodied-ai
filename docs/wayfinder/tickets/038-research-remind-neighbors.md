# Ticket 038 — Research: Neighbor context + geometry-aware disambiguation

> Parent: `007-map-memoria-objetos.md` · Label: `wayfinder:research` · Estado: **cerrado 2026-08-24** · Tipo: AFK (research subagent) · Claim: `mauri`

## Question

¿Cómo diseña REMIND el `Co-occurrence Neighbor Graph` (kernel exponencialmente pesado por `co-visible IDs` por objeto `o`) + `Distance Neighbor Graph` y el `context veto` con bonos `delta+` / penal `delta-` (Table VIII paper) escalados por cobertura/madurez/densidad/pruning, integrados al `cost matrix` pre-Hungarian `association/`? Mapear `perception/` + `§3D-E` y si requiere `depth/pose/3D` o solo RGB co-visibilidad (motivación cognición humana del paper).

Salida: esquema grafo + fórmula bonus/penalidad + condiciones `veto` + qué es aplicable a `Whitelist v2 13 clases` sin pose.

## Notes

- Leer `association/*`, `REMIND_METHOD.md` y `arXiv §3D`.
- Validar que REMIND opera `entirely from monocular RGB without camera pose nor depth`.
- Branch `research/038-remind-neighbors`.

---

## Findings — Anexo research AFK (2026-08-24)

> Estado: **cerrado** — anexo verificado y promovido a decisión. Parent `007-map-memoria-objetos.md`.
> Fuentes primarias: `arXiv:2607.09267 §3D (§3-D1..D3) + §3E (§3-E1..E5) + §3F + Appendix Table VIII` · `REMIND_METHOD.md §2.4–2.7 + §3.6` · `cvar-vision-dl/remind-reid-tracker` (`memory/neighbor_graph.py`, `memory/neighbor_distance_graph.py`, `association/scores/sets/neighbor_sets_score.py`, `association/context/neighbor_sets_influence.py`, `association/context/sets_context_builder.py`, `association/resolver/hungarian_resolver.py`, `association/score_aggregator.py`, `config/default_config.yaml`).

### 1) Respuesta corta — ¿requiere depth/pose/3D?

**No.** REMIND opera *entirely from monocular RGB without camera pose nor depth*.

- Paper lo declara explícito: Abstract: *"requiring neither camera pose nor depth"*; §I párr. 6: *"This motivates a system that operates entirely from monocular RGB, without camera pose, depth sensing, or 3D reconstruction, relying on appearance memory and contextual reasoning"* (motivación cognición humana §I: humanos reconocen por familiaridad + relaciones espaciales sin auto-localización, ref [15]); §III-A System Overview: *"without camera pose information"*; §II-E contrasta con métodos RGB-D que sí requieren depth/3D y los descarta para deployment monocular.
- `REMIND_METHOD.md:1` y `config/default_config.yaml` no exponen ningún canal depth/pose; `memory/neighbor_distance_graph.py:1-80` deriva todo de `bbox`/`mask` 2D en `patch space`.
- Implicación Whitelist v2: todo el módulo neighbor es portable a `plataforma/webcam` sin MiDaS ni pose — co-visibilidad = "co-visible en mismo frame D5 `ws.py:197` boxes Whitelist", puramente RGB 2D. MiDaS 256 42ms (`CONTEXT.md:113`) queda como complemento opcional geométrico (fog post-memoria, `007-map:Not yet specified`), no requerido por REMIND.

### 2) Esquema de los dos grafos

#### 2.1 Co-occurrence Neighbor Graph — `memory/neighbor_graph.py:12-120`

```
Objeto o  ──directed edge o→o'──►  NeighborEdge{ cooc_count, weight, first/last_seen_ts, last_seen_episode }
         │
         ├── episode_count (veces que o fue visible)
         ├── stable_context / pending_context (debounce)
         └── episode_idx / last_episode_frame_id
```

- **Unidad de conteo: episodio, no frame.** `association/context` + `memory/neighbors: debounce_frames: 3, force_episode_every_frames: 3` (`config: neighbors`). Un episodio = racha de co-visibilidad contigua con hysteresis 3 frames; evita inflar conteos por jitter YOLO a 5–10 Hz. `NeighborEdge.cooc_count` y `weight` se incrementan con `bump(ts, episode_idx, inc=1.0)` por episodio (`neighbor_graph.py:22-38`).
- **Kernel exponencialmente pesado:** `weight` es acumulador de episodios (inc=1.0 constante); `decay_per_episode: 1.0` en config indica sin decaimiento por defecto, pero el modelo está preparado para pesado exponencial via `smoothing_alpha` + `trim_strategy: "weight"` (ordena neighbors por `weight` descendente). La probabilidad suavizada expone el kernel:
  `p_conditional(B|A) = (cAB + α) / (cA + α·V)` con `α = smoothing_alpha = 0.5` (`neighbor_graph.py:58-71`, `config: memory.neighbors.smoothing_alpha`), `V = vocab_size`. `pmi(A,B) = log(P(A,B)/(P(A)P(B)))` también disponible (`:72-92`).
- **Persistencia dual-bank compatible:** cada `TrackedObject` agrega `NeighborGraph` + `NeighborDistanceGraph` (`REMIND_METHOD.md §4.2`); Inactive conserva ambos bancos intactos para re-identificación tras gaps de cientos de frames (§III-C1, §III-F).
- **Cap:** `max_neighbors: 20`, `trim_strategy: weight|recent`, `jaccard_thr: 0.85` para deduplicación.

#### 2.2 Distance Neighbor Graph — `memory/neighbor_distance_graph.py:1-250+`

- **Arista dirigida (o,o')** acumula *resumen estadístico* de relaciones 2D por episodio:
  - `normalized center distance` (dist euclídea entre centroides / escala),
  - `contact` (toca vs. gap, `contact_margin_px: 2.0`),
  - `containment` (uno contiene al otro, `_bbox_contains_point`, `_bbox_intersection_area`),
  - `relative scale` y `projected gaps` eje X/Y (`_bbox_gap_px`, `_bbox_axis_gap_px`),
  - `var_floor: 0.0225, scale_min: 40.0, near_thresh_n: 1.25, exact_gap_max_n: 1.75` (`config: memory.neighbors_distance`).
- **Sin geometría 3D:** todo se computa desde `mask/bbox` 2D en `prepare_relation_mask_runtime` + helpers `_bbox_*`; `touches_border` corrige truncamiento por borde de frame. Es *"geometry-aware"* solo en sentido 2D layout relativo.
- **Rol:** no entra al cost matrix directamente; alimenta **Known-set distance disambiguation** post-Hungarian (§III-E5 / `REMIND_METHOD.md §2.7`): cuando un grupo de detecciones mapea ambiguamente a un closed set de IDs, compara distancias observadas vs. histórico por par `(o,o')` para romper empates; también `anchor-based scoring` triangula con objetos ancla confiables.

```
Co-occurrence Graph ──► NeighborSets (context bonus/penal pre-Hungarian)
Distance Graph    ──► Known-set disambiguation (post-Hungarian, geometry-aware)
```

### 3) Neighbor-Sets Context Layer — integración al cost matrix pre-Hungarian

**Pipeline por frame** (`REMIND_METHOD.md §2.4-2.7`, `association/score_aggregator.py:8-20`, paper Fig.2 `Perception → Association → Update`):

```
1. Similarity reports  s_sim(d,o) = Σ w_c·q_c_eff·s_c / Σ w_c·q_c_eff   (§III-E2, eq.7, config association.similarity/weights)
       c ∈ {object(0.60), bg_global(0.25), bg_partials(0.05), parts(0.10)} + quality q_c_eff por coverage/madurez
2. Reliable anchors   Strong + margin ≥ δ_confirm (§III-E3, confirm_thr_strong 0.75, clear_margin 0.08)
3. NeighborSetsScore  genera hipótesis de conjuntos (detecciones ↔ IDs) vía beam search sobre grafo ONLINE (§2.4)
       → outputs: best_score, coverage_eff, k_best, n_hypotheses, shortlist, prior_by_oid, support_sum_by_oid, maturity, density
4. SetsContextBuilder + NeighborSetsInfluence → bonus/penal + quality gate
5. Cost matrix  score_assign(d,o) = s_sim(d,o) + Δ_context(d,o)  (capped)
   Hungarian minimiza  cost = -score_assign  + dummy columns  (§III-E4, hungarian_resolver.py:18-45)
6. Guards post-Hungarian: AmbiguousTracks / ProvisionalNewTracks / Known-set distance disambiguation
7. Update: robust gating + NeighborGraph/DistanceGraph bump por co-visible set confirmado (§III-F, §3.6)
```

#### 3.1 Fórmula bonus / penalidad — `association/context/neighbor_sets_influence.py:1-155` + `config: matching.neighbor_sets_influence`

**Quality gate global** (`sets_context_builder.py:45-110`):

```
quality_terms = {best, coverage_eff, maturity, density, size, pruning}  cada uno ∈[0,1]
quality = weighted_mean( best*0.25 + coverage_eff*0.20 + maturity*0.15 + density*0.10 + size*0.15 + pruning*0.15 )
global_ok ⇔ n_hypotheses>0 ∧ k_best ≥ min_size(2) ∧ best ≥ 0.45 ∧ coverage_eff ≥ 0.35 ∧ quality ≥ min_quality(0.35)
```

Pesos y umbrales en `config: matching.neighbor_sets_influence.quality` (best_score 0.25, coverage_eff 0.20, maturity 0.15, density 0.10, size 0.15, pruning 0.15; min_best_score 0.45, min_coverage_eff 0.35, min_size 2, size_tau 3.0).

**Soporte positivo Δ+** (si candidato `o` es compatible con hipótesis vecina esperada):

```
support = f( kernel_weight 0.75, hyp_weight 0.25, top_weight 0.65, sum_weight 0.35,
             kernel_rel_gamma 0.75, hyp_rel_gamma 0.75, neutral_rel 0.20,
             band_rel 0.80, soft_band_rel 0.65, ... )  // compresión gamma evita ensanchar gap histórico
Δ+ = clamp( support · quality_factor , 0 , δ+ )   con δ+ = positive_cap = 0.20  (Table VIII)
Condiciones soporte válido: min_kernel_abs_for_support 0.10, min_kernel_hits_for_support 2,
                            min_kernel_hit_ratio_for_support 0.25 (local y global idem), pruning_weight 0.55, rank 0.30, selectivity 0.15
```

Solo aplica si `status ∈ {WEAK, AMBIGUOUS}` (no refuerza STRONG ya decidido) y `s_sim ≥ rescue_min_sim 0.60` para rescatar matches débiles ocluidos (§III-D3: "can rescue matches too weak on appearance alone").

**Penalidad Δ−** (si candidato contradice vecindad esperada):

```
Δ− = clamp( contradiction · quality_factor , -δ− , 0 )  con δ− = negative_cap = 0.10
contradiction ≈ f( pruning, class_strength )  requiere min_pruning 0.35, min_class_strength 0.35, max_rel 0.10
```

Penalidad acotada — REMIND enfatiza *"bounded contextual bonus or penalty"* (§III-D3).

**Scaling por cobertura/madurez/densidad/pruning:** ya incluido en `quality` (punto 3.1) y en `quality_factor` que multiplica Δ. Además `SetsScoring` combina en `score_sets` (`sets_scoring.py`): `coverage (0.40) + size (0.20) + density (0.20) + class_info (0.10) + class_support (0.10) + class_stability (0.10) + exclusivity (0.05)` con `coverage_gamma 1.0, coverage_size_tau 3.0, density_gamma 2.0, maturity_gamma 0.85`, etc. (`config: scores.neighbor_sets`).

**Dónde se aplica:** `ScoreAggregator.neigh_sets` produce `neighbor_sets_out` → `NeighborSetsInfluence` convierte a `Δ(d,o)` → `association/similarity_computer.py` + `score_aggregator.py` suman a `table_assign` antes de construir `cost_matrix` en `hungarian_resolver.py:18-35` (`cost[i][j] = -score_assign`).

#### 3.2 Context veto — `config: matching.neighbor_sets_context_veto`

Veto conservador que **anula candidatos MATCH fuera del subconjunto soportado** cuando la evidencia contextual es fuerte; no es una penalidad suave sino supresión (`score 0 / cost ∞`).

```
veto_enabled ⇔ enabled true (default true)
global veto:  if |supported| ≤ supported_max(3) ∧ quality ≥ 0.60 ∧ pruning ≥ 0.35 ∧ class_strength ≥ 0.50
              ∧ max_compat_rel ≤ 0.10 ∧ max_score_sets ≤ 0.05
              ⇒ candidatos o ∉ supported  vetados (score_assign → -∞ en cost matrix)

local veto (por objeto): enabled true, min_quality 0.45, min_episodes 4, min_kernel_size 3,
                         min_expected_neighbors 3, max_hit_ratio 0.10,
                         expected_mass_target 0.75, expected_topk_scale 2.0
```

Semántica paper §III-D3: *"when contextual evidence strongly contradicts a candidate identity, a context veto mechanism suppresses that candidate entirely, preventing erroneous assignments driven by misleading appearance similarity."* Es el complemento del Δ−: Δ− desincentiva, veto elimina.

`REMIND_METHOD.md §2.6` y `association/context/sets_context_builder.py` distinguen *veto* de *soft penalty*: veto solo si `quality_ok` y `supported` pequeño y maduro, evitando falsos vetos con poca evidencia.

#### 3.3 Known-set distance disambiguation — post-Hungarian geometry-aware

Cuando `AmbiguousTracks` detecta que un grupo de detecciones compite por un closed set de IDs (ej. 2×`chair` idénticas lado a lado), `association/disambiguation` + `config: ambiguous_tracks.known_set_distance_disambiguation` entra:

```
enabled true, max_passes 2, max_group_size 4, max_candidate_union 5, max_anchors 4
anchor_weight 0.55, visual_weight 0.10, gap_sigma 0.20, center_sigma 0.35, rank_sigma 1.0
min_edge_reliability 0.15, min_total_evidence 0.20, min_assignment_score 0.20, min_gap 0.08
```

Compara `observed pairwise relations (center distances, containment, contact)` vs. `historical distance graph` por par, combinado con `anchor-based scoring` (objetos confiables como landmarks) — `REMIND_METHOD.md §2.7`, paper §III-E5 último párrafo. No requiere depth; usa distancias 2D normalizadas del `neighbor_distance_graph`.

### 4) Tabla de parámetros relevantes (mapeo Table VIII paper ↔ config)

| Concepto paper | Param config | Valor default |
|---|---|---|
| `δ+` positive_cap | `matching.neighbor_sets_influence.positive_cap` | **0.20** |
| `δ−` negative_cap | `matching.neighbor_sets_influence.negative_cap` | **0.10** |
| `min_quality` global | `neighbor_sets_influence.min_quality` | 0.35 |
| `rescue_min_sim` | `neighbor_sets_influence.rescue_min_sim` | 0.60 |
| quality weights | `neighbor_sets_influence.quality.weights` | best 0.25, cov 0.20, maturity 0.15, density 0.10, size 0.15, pruning 0.15 |
| veto supported_max | `neighbor_sets_context_veto.supported_max` | 3 |
| veto min_quality | `neighbor_sets_context_veto.min_quality` | 0.60 |
| `confirm_hits` (lifecycle) | `update.confirm_hits` | 2 |
| `max_misses` | `update.max_misses` | 10 |
| Co-occurrence smoothing α | `memory.neighbors.smoothing_alpha` | 0.5 |
| Distance var_floor | `memory.neighbors_distance.var_floor` | 0.0225 |
| Hungarian lock thr | `matching.hungarian.locks.thr` | 0.90, gap 0.10 |

### 5) Aplicabilidad a Whitelist v2 13 clases sin pose

**Aplicable 100% sin cambios de principio; adaptación es de presupuesto, no de geometría.**

- **Co-visibilidad RGB:** Definir co-ocurrencia como `co-visible en mismo frame D5` (`ws.py:197` boxes filtradas por Whitelist `person, chair, couch, bottle, cup, cell phone, laptop, keyboard, mouse, book, backpack, handbag, remote`). Cada clase CON su propio Hungarian per-class (`hungarian_resolver.py` es per `class_id`), pero **NeighborGraph es cross-class**: vecinos pueden ser de clases distintas (ej. `laptop` cerca de `chair`), lo cual aumenta densidad — paper no restringe a misma clase para contexto, solo Hungarian es per-class.
- **Umbrales a calibrar:** Con `YOLO conf>0.50 area>3%` para genéricas (`CONTEXT.md:109`) hay más ruido que en REMIND (conf 0.7). Recomendación: activar influencia solo con `quality ≥0.35` y veto solo con `quality ≥0.60` (defaults ya conservadores), y exigir `min_kernel_hits 2` + `min_kernel_hit_ratio 0.25` — tal cual config — evita falsos vecinos por detecciones espurias. No incluir `wall/floor/ceiling` (ya en `ignored_classes` REMIND).
- **Person como ancla:** REMIND incluye `person` como cualquier clase; para indoor estático, `person` es vecino ruidoso (móvil). Decisión para grilling 041: excluir `person` del NeighborGraph para objetos estáticos o peso reducido; REMIND no lo excluye pero nuestro `Whitelist v2` puede tratar `person` como ancla opcional (útil si persona siempre lleva `backpack/handbag`).
- **Madurez / pruning:** Con pocas revisitas (robot entra/sale de habitación), madurez baja al inicio — Δ+ será ≈0 hasta `k_best ≥2` y `min_episodes 4` (veto local). Comportamiento deseado: sistema arranca solo por apariencia (`s_sim` con DINOv3/mobilefacenet) y gradualmente activa contexto, tal como REMIND describe *"maturity"*.
- **Sin pose/depth:** Confirmado portable; la única geometría usada es bbox 2D. MiDaS (`CONTEXT.md:113`) puede alimentar Distance Graph como señal extra (z_rel mediana 3×3 centro bbox) pero no requerido — fog post-spec.
- **Costo Hungarian:** `O(n³)` por clase, con `n ≤13` Whitelist total y per-class `n ≤4` (ej. 4×chairs) → <1ms en JS/WASM, compatible con `Glass-to-Glass <200ms` y `LeakyQueue N=1` (ver ticket 039 research budget). REMIND corre Hungarian por clase, no global, lo que reduce costo.
- **Privacidad / dónde vive:** Estado neighbor vive en memoria volátil asociada a `TrackedObject` (dual-bank), sin persistencia en `localStorage` — coherente con `CONTEXT.md:94` solo memoria 128-d volátil. Para `plataforma/webcam`, mantener `NeighborGraph` client-side (privacidad, sin exfiltrar grafo a `ws.py`), o server-side en `ws.py` si se quiere compartir across clients — decisión para grilling 041 (`CONTEXT.md` ya define `WhiteboardState` single-writer memoria).

### 6) Esquema integrado final — dónde encaja en `association/` (repo real)

```
remind-reid-tracker/
├── perception/  (no usado para contexto, solo aporta masks/bboxes 2D)
├── memory/
│   ├── neighbor_graph.py            → Co-occurrence Graph (directed, episode-counted)
│   └── neighbor_distance_graph.py   → Distance Graph (pairwise stats 2D)
├── association/
│   ├── score_aggregator.py          → orquesta BaseScores + NeighborSetsScore
│   ├── scores/sets/
│   │   ├── neighbor_sets_score.py   → beam search hipótesis conjuntos (topk_sets 20, beam 64)
│   │   ├── sets_scoring.py          → coverage/size/density/class_info/exclusivity
│   │   └── sets_search.py           → SetsSearchEngine
│   ├── context/
│   │   ├── neighbor_sets_influence.py → Δ+/Δ− bounded, quality-gated
│   │   ├── sets_context_builder.py    → quality terms, class_ctx, shortlist
│   │   └── sets_provider.py
│   ├── resolver/hungarian_resolver.py → build_cost_matrix (-score) + linear_sum_assignment
│   ├── reports.py / similarity_computer.py → s_sim quality-weighted
│   └── policy/sets_rule_policy.py
├── pipeline/                        → Per-frame: Perception → Association(1..6) → Update(graph bump)
└── config/default_config.yaml       → Table VIII thresholds (ver tabla §4)
```

Flujo `pipeline/*.py` (resumen `REMIND_METHOD.md §4.3`): `detect → DINOv3 F → descriptors → similarity reports → anchors → neighbor-sets → ambiguity → Hungarian(locks+dummies) → guards(ambiguous/provisional/distance) → update(EMA + graph)`.

### 7) Qué llevar a grilling 041 + spec Whitelist

- [ ] Adoptar definición co-visibilidad = mismo frame D5 Whitelist 13 clases, episodio = racha con debounce 3 frames (copiar `memory.neighbors.debounce_frames`).
- [ ] Inicialmente mapear REMIND defaults `δ+ 0.20 / δ− 0.10 / min_quality 0.35 / rescue 0.60 / veto 0.60` sin tuning; escalar `quality_factor` ya incorpora madurez.
- [ ] Excluir `floor/wall/ceiling` (igual que REMIND `ignored_classes`), opcionalmente `person` del grafo vecinos hasta evaluar.
- [ ] Implementar Distance Graph solo con bbox 2D en `association/disambiguation` post-Hungarian, no en cost matrix.
- [ ] Validar hipótesis `REMIN D entirely RGB` citando §I+§III-A en grilling para cerrar duda depth/pose.

*Refs:* `arXiv:2607.09267 §III-D1 (eq. conditional p, PMI), §III-D2-D3, §III-E1-E5 Fig.2-3, Table VIII` · `REMIND_METHOD.md §1-2.7, §3.6-4.3` · `memory/neighbor_graph.py:12-71, neighbor_distance_graph.py:1-60, association/context/neighbor_sets_influence.py:14-80, sets_context_builder.py:30-110, association/resolver/hungarian_resolver.py:18-45, config/default_config.yaml:120-260`.
