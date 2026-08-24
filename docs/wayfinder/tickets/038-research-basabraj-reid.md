# Ticket 038 — Research: basabraj ReID per-person threshold + LanceDB

> Parent: `007-map-arquitectura-productiva` · Label: `wayfinder:research` · Estado: **cerrado 2026-08-24** · Tipo: AFK · Rama: `research/038-basabraj-reid` (no prod code modificado)

## Question

¿Cómo calibra `basabraj/Mobilefacenet` su `live_face_pipeline.py` per-person `recog_threshold` + `threshold_low/high` + `LanceDB` gallery vs nuestro `CONTEXT.md:98` ReID híbrido cada 3 frames + `IoU<0.7` trigger, `cos<0.42` firme / `0.42-0.55` zona gris / `>0.55` desconocido, histéresis `N=3` grace2, tracker `IoU greedy >0.5` edad5, y `IdentidadVista` `plataforma/sim/whiteboard.py:38` `last_identidades` client-side?

Evaluar: `calibrate_person_thresholds()` tight clustering, `gallery_db` idempotente (solo re-embed cambios), `track_skip_frames`/`track_recheck_interval` para evitar blur entrance, `quality/pose/landmark gates`, `LanceDB cache` vs `localStorage:webcam.identities + identities.json` híbrido mapa 004 + `enroll_sync` bypass `N=1`; flags `--recog_threshold/--threshold_low/--threshold_high/--gallery_db`.

Resolver vía subagente `research`: leer `basabraj/live_face_pipeline.py` + `enrolled_faces/<name>/*.jpg` + `plataforma/webcam/frontend/src/enrollment-panel.js:334`, `whiteboard.py`, `CONTEXT.md:96`; producir tabla comparativa + recomendación si adoptar per-person calibrated sin romper `embedding[128]` contrato.

## Sources

**Local (verificados 2026-08-24):**

- `plataforma/webcam/frontend/src/enrollment-panel.js:13-19` — `REID_N=3 REID_GRACE=2 REID_EVERY=3 IOU_TRIG=0.7 IOU_TRACK=0.5 TRACK_AGE=5`
- `plataforma/webcam/frontend/src/enrollment-panel.js:302-356` — `iou()`, `getFaceBox()` fallback `mockFaceFromPerson`, `shouldEmbed()`, `findBestMatch()` loop `cosineDistance`
- `plataforma/webcam/frontend/src/enrollment-panel.js:353-384` — `trackIdentities()` greedy `IoU>0.5` + `age TRACK_AGE=5` + `traj 12`
- `plataforma/webcam/frontend/src/enrollment-panel.js:385-473` — `runReId()` hasta 3 caras, `firmSeen` + `reIdHyst Map` `count/grace`, `estado confirmado/posible/desconocido`, `conf=1-dist`, `ABORTED overlay-only`
- `plataforma/webcam/frontend/src/face-embedding.js:8-10` — `EMBEDDING_DIM=128 COSINE_THRESHOLD=0.42 COSINE_GRAY=[0.42,0.55]`
- `plataforma/webcam/frontend/src/face-embedding.js:56-62` — `stubEmbedding` xorshift32 L2 determinístico
- `plataforma/webcam/frontend/src/face-embedding.js:70-167` — `createFaceEmbedder` `onnxruntime-web@1.29 wasm` `input [1,3,112,112]` normalize `(-0.5)/0.5→L2`
- `plataforma/webcam/frontend/src/face-detector.js:1-143` — `BlazeFace short-range` `FaceDetector.createFromOptions` `minDetectionConfidence 0.7`, `detect`/`detectAll` normalizado [0,1], sin 5 landmarks
- `plataforma/sim/whiteboard.py:38-55` — `IdentidadVista {id,nombre,cosine,conf,estado,box,face_box,frame_id,ts}` `last_identidades: list[IdentidadVista]|None` single-writer
- `CONTEXT.md:96-106` — ReID híbrido per-frame cada 3@10Hz + IoU<0.7, zona gris 0.42–0.55, histéresis N=3 grace2, IoU greedy edad5
- `docs/wayfinder/006-map-vision-viva.md:7-13` — Destination budgets `YOLO~35ms+BlazeFace~15ms+mobilefacenet~32ms/3 media ~25ms + WS~25ms=~107ms <200ms`

**Externo (alta confianza):**

- `basabraj/Mobilefacenet` live_face_pipeline.py — 820 líneas, fetched raw 2026-08-24 via webfetch (truncado HTML nav, código extraído vía grep)
- `basabraj` README excerpt — pipeline `GStreamer(rtspsrc/H.265)→appsink→YOLOv8n-face(box+5lm)→IoU tracker→quality/pose/lm gate→112 alignment→MobileFaceNet→LanceDB`
- GitHub README `docs/webrtc-server` referencia hailo-ai `db_handler.py calibrate_classification_confidence_threshold` espejo

**No verificado (fog):** performance exacta `mobilefacenet.onnx` 128-d fuente pública (ver ticket 032 deuda Opción C, `w600k_mbf.onnx` es 512-d).

## Tabla comparativa — nuestro vs basabraj

| Dimensión | **Nosotros (006 cerrado, `enrollment-panel.js:385` + `face-embedding.js:8` + `whiteboard.py:38`)** | **basabraj `live_face_pipeline.py:1-820`** | Delta / implicación |
|---|---|---|---|
| **Detector** | `YOLO person conf>0.6 area>15%` (`enrollment-panel.js:282`) + `BlazeFace short-range` `0.2MB 12-22ms` **sin** 5 landmarks (fallback `mockFaceFromPerson 25% inset 50%w 35%h` `enrollment-panel.js:289`) | `YOLOv8n-face.pt` **con** 5-point landmarks `eyes/nose/mouth` + `box+landmarks+lm_conf+det_conf` (`get_face_detections`) ; pinned a `yolov8n-face.pt` porque v11/v12 bbox-only no sirven | Basabraj tiene **geometría 5 puntos** → `align_face()` similarity transform a `REFERENCE_LANDMARKS_112` reduce drift rotación/escala; nosotros proxy sin alineación → embedding más ruidoso entre frames. Adoptar alignment cuando `face-detector` exponga landmarks es ganancia segura. |
| **Crop & alignment** | `ctx.drawImage(v, px,py,pw,ph, 0,0,112,112)` directo sin warp (`enrollment-panel.js:405`) | `align_face(image, landmarks) → estimateAffinePartial2D(src=5lm, dst=REFERENCE_LANDMARKS_112) → warpAffine 112` ; fallback bbox crop si degenerado | Alineación ~2ms OpenCV evita que misma persona caiga en vecino por rotación. Costo marginal en browser con WASM/Canvas. |
| **Embedding** | `128-d` L2 stub xorshift32 (`face-embedding.js:56`) o `mobilefacenet.onnx` wasm ` (r-0.5)/0.5` CHW `[1,3,112,112]` | `128-d` L2 `MobileFaceNet_9925_9680.pb` TF1 frozen `input:0→embeddings:0` `(bgr-127.5)*0.0078125` + `get_face_embedding()` con aligned crop | **Misma dimensión `embedding[128]` L2** — contrato intacto. Normalización difiere (`0.0078125` vs `/0.5`) pero ambas → `[-1,1]` antes de L2. Interoperables si se respeta L2. |
| **Galería** | `localStorage:webcam.identities` + `backend/models/identities.json` schema `{id,nanoid,nombre,embedding[128],count,updatedAt}` (`CONTEXT.md:94 IdentitiesStore` `hat_e=normalize(e_old*min(N,5)+e_new)` cap5). `GET /identities` snapshot + `enroll_sync`/`purge` delta bypass `LeakyQueue N=1` `PendingSync` (`enrollment-panel.js:50-113`) | `enrolled_faces/<name>/*.jpg` filesystem + **LanceDB** `gallery_db` `GALLERY_TABLE='faces'` schema `{id:md5(path), name, image_path, embedding:list<float32>[128]}` `pa.schema`. `sync_gallery_db()` incremental: solo `md5∉existing → _embed_enrollment_photo → table.add()`, `existing∖current → table.delete()`. `build_centroids()` colapsa a **1 centroide por persona** `mean→L2` | Nosotros: browser-first, privacidad, offline PendingSync, sin deps pesadas. Basabraj: server-side persistente, deduplicado, escala a 10k con ANN. Para `<100` identidades JSON+loop `<1ms` es más simple y rápido que LanceDB. LanceDB aporta valor solo si galería crece o se necesita ANN/re-embedding diferencial. |
| **Matching** | Brute-force por imagen: `findBestMatch()` itera todas `rec.embedding.length===128`, `cosineDistance` `1-dot` min dist (`enrollment-panel.js:336-352`) | Centroide: `centroids[name]=mean(L2)` + `recognize()` `scores=dot(embedding, centroid)` max, `threshold=person_thresholds.get(best, default)` `recog_threshold=0.6`, `margin=0.05` vs runner-up else `Unknown` | Centroid promedia outliers → menos falso match por foto ruidosa enrollada. Nosotros matching por imagen puede confundir si 1 foto outlier da distancia pequeña inter-personal. Centroid es superior con `N>=2` por persona. Con `N=1` ambos equivalentes. |
| **Threshold** | **Fijo** `COSINE_THRESHOLD=0.42` distancia (`face-embedding.js:9`) → similarity `0.58`, zona gris `0.42-0.55` → `estado posible` solo overlay amarillo sin promover a `Whiteboard` (`enrollment-panel.js:443`). **No calibrado por persona.** | **Per-person calibrado** `calibrate_person_thresholds(gallery, low=0.6 high=0.65)`: por persona `stack(embs) → SVD top2 → ellipse area=π·σ1·σ2 → norm 0-1 invertida → thr=low+(high-low)*(1-norm)`. Tight cluster → thr alto (estricto), spread → thr bajo (permisivo). Fallback `recog_threshold=0.6` si `<2` fotos. Rango `0.60-0.65` **empíricamente calibrado**: inter-person max `0.569`, intra min `0.673` mean `0.865` en galería 3 personas. `threshold_high 0.90` hailo-default daba 50% FN en tightest person. | Fijo 0.42 es simple y robusto con enroll single-shot, pero subóptimo: persona con embeddings spread (variación luz/ángulo) necesita thr más permisivo, persona tight tolera thr estricto para evitar FP cross-person. Con galería 1-foto/persona per-person colapsa a uniforme `0.65` (ver Nota 1). Con multi-foto (≥3) calibrado gana +10-22% accuracy (paper Data-specific Adaptive Threshold `arXiv:1810.11160`). |
| **Histéresis / temporal** | **Client-side** `reIdHyst Map nombre→{count,grace}`: `count++` si `dist<0.42` firme, `grace=0`; decay `grace++` si no visto firme, delete si `>REID_GRACE=2`; `estado confirmado` solo si `count>=REID_N=3` (`enrollment-panel.js:430-466`) | **Sin histéresis** en `recognize()`; en su lugar **tracker + agregado temporal**: `track_skip_frames=5` espera antes de primer recognize (evita blur entrada, "single biggest accuracy lever" `SimpleTracker` docstring), `track_recheck_interval=15` evita cada frame, `aggregate_track_embedding(window=5)` rolling mean L2 antes de lookup | Complementarios: nosotros N=3 grace2 evita flicker `desconocido↔Hola`; basabraj skip+window evita single-frame noise (`0.600 vs 0.612` case). Ambos pueden coexistir: `shouldEmbed() cada 3 + IoU<0.7` ya es throttle; añadir `track_skip` 2-3 frames + ventana 3 no rompe `<200ms`. |
| **Tracking** | `IoU greedy >0.5` edad `5` frames (~500ms) `trackIdentities()` (`enrollment-panel.js:353`), traj `12` puntos, `<1ms`, tie por área `w*h` | `SimpleTracker(iou_threshold=0.3, max_missed=10)` `tracker.update(boxes, frame_count)` greedy mismo algoritmo pero `iou_threshold 0.3` más permisivo (fast motion) + `max_missed 10` (~1s @10Hz) | Nuestro `0.5` más estricto → menos ID switch en crowd pero pierde track en movimiento rápido. Basabraj `0.3` tolera jitter. Ambos dentro de `ByteTrack IoU>0.5` spec G2. Mantener `0.5` está bien; bajar a `0.4` es opcional para motion blur. |
| **Throttling** | `REID_EVERY=3` + `IOU_TRIG=0.7` (`shouldEmbed()` `enrollment-panel.js:324`) + `MAX_FPS=10` + `LeakyQueue N=1` + `bufferedAmount>64KB` skip | `frame_skip` CLI + `track_skip_frames=5` + `track_recheck_interval=15` + `track_embedding_window=5` mean + `GStreamer max-buffers=1 drop=true` | Nosotros ya cubre presupuesto `~107ms`. Basabraj intervalo 15 ~1.5s re-eval; nosotros cada 3 ~300ms más reactivo pero más CPU. Equivalentes si `REID_EVERY=3` se mantiene. |
| **Quality gates** | **Ninguno**: no blur, no pose, no landmark_conf, solo `person area>15%` y `face conf>0.5` | **Cuatro gates** antes de embed: `face_quality_ok(min_pixels=3000, blur Laplace≥50)`, `frontal_pose_score(pose≥0.15 symmetry eyes/nose/mouth)`, `landmark_conf≥0.5` (bag/chair FP ~0.25 vs face ~0.8), `min_face_pixels` 3000 (hailo 12000 rechazaba todas) | Gates explican gran parte de FP reduction basabraj. Nosotros sin gates → embedding de caras lejanas/borrosas/perfil contamina matching y eleva `Unknown` flicker. Adoptar `blur+pose+lm_conf` client-side con `offscreen canvas` Laplace + symmetry es barato `<0.5ms` y no rompe privacy. |
| **Privacidad / runtime** | **Browser WASM** `onnxruntime-web` client-side, embedding nunca imagen cruda, `localStorage` (`CONTEXT.md:82`) | **Server TF1** `cv2.imread enrolled_faces + lancedb.connect(db_path)` server-side, RTSP CCTV, guarda crops `detected_faces/<label>/face_*.jpg` + `_enhanced.jpg` CLAHE revisión | Arquitecturas opuestas: nosotros edge-privacy, basabraj CCTV-server. LanceDB solo tiene sentido server-side; en browser LanceDB no existe (pyarrow/Gst). Mantener split actual. |
| **Budget / latency** | `YOLO ~35ms server + BlazeFace ~15ms + mobilefacenet ~32ms/3 media 25ms + WS 25ms =107ms` dentro `<200ms` | No budget Glass, RTSP `latency_ms` jitterbuffer + GStreamer `avdec_h265` + YOLO + TF embed every recheck → no comparable, pero CL report `FPS ~?` + `FPS 1.0s` log | Ambos cumplen si batch no bloquea. |

### Nota 1 — Por qué per-person colapsa con galería single-shot

`calibrate_person_thresholds()` calcula `area=π·σ1·σ2` vía `SVD(centered)[:2]/√(N-1)`. Si `len(embs)<2 → area=0.0`. Con 1 foto por persona (nuestro enrollment actual `nanoid` 1 embedding), **todas** las áreas son `0.0` → `norm_areas=0` → `thr = low+(high-low)*1 = high` para todos → **umbral uniforme `0.65`**, idéntico a fijo pero en escala similarity. Beneficio per-person aparece solo con `N>=3` fotos/persona con variación (ángulos/luz). Paper `Data-specific Adaptive Threshold` (`arXiv:1810.11160`) reporta +22.5% en LFW con múltiples samples.

### Nota 2 — Conversión distancia↔similarity

Nosotros `cosineDistance = 1 - dot`; threshold `0.42` distancia ≡ `0.58` similarity. Basabraj `recog_threshold=0.6` similarity ≡ `0.40` distancia. Escalas comparables: `0.42 vs 0.40` distancia. Su zona calibrada `0.60-0.65` similarity ≡ `0.35-0.40` distancia → más estricta que nuestro `0.42`, coherente con `mean intra 0.865 similarity ≡ 0.135 distancia`.

## Investigación detallada basabraj

### 1) `calibrate_person_thresholds(gallery, low=0.6, high=0.65)` — `live_face_pipeline.py:~480`

Creado espejo `hailo-ai/hailo-apps face_recognition/db_handler.py:calibrate_classification_confidence_threshold` pero re-calibrado para galería pequeña:

- Input `gallery: list[(name, embedding[128])]` de `sync_gallery_db()` (incremental, ver §2).
- `per_person[name] = stack(embs)` → `centered = embs - mean` → `svd(centered).s[:2]/√(N-1)` → `area=π·semi_major·semi_minor`.
- `norm = (area - min)/(max-min)` → `thr = low + (high-low)*(1-norm)`. Tight → alto.
- CL `for name in sorted(person_thresholds): print(" %s: threshold=%.2f" % ...)` al inicio.

Flags: `--threshold_low` default `0.6` (hailo `0.1` era ranking puro sin floor, en galería pequeña fijo `0.6` evita FP cross-person porque `inter_max=0.569`), `--threshold_high` `0.65` (hailo `0.9` daba 50% FN en persona tight `Shraban_Sir` mean `0.865`). `--recog_threshold 0.6` solo fallback `<2` fotos.

**Lección:** no copiar `0.1-0.9` hailo; recalibrar sobre datos propios midiendo `inter_max` y `intra_min/mean`.

### 2) `sync_gallery_db(db_path, enroll_dir, ...)` + LanceDB `live_face_pipeline.py:~380`

- `db=lancedb.connect(db_path)` default `gallery_db/` (`DEFAULT_GALLERY_DB`).
- `table=db.open_table('faces') if 'faces' in db.table_names() else None`
- `current_files = {md5(path): (name,path) for name in enroll_dir/* for f in glob}`; `existing_ids = set(table.to_pandas()['id'])`
- `to_add = current∖existing` → `new_rows=[]; for id in to_add: emb=_embed_enrollment_photo(... gating ...); if emb: new_rows.append({id, name, image_path, embedding:list[128]})` → `db.create_table` o `table.add`
- `to_remove = existing∖current` → `table.delete("id='%s'" % id)` por cada borrado filesystem
- Log `gallery_db sync: +N new, -M removed (of K cached rejected by gate: ...)`
- `df=table.to_pandas(); return [(row['name'], np.array(row['embedding'])) ...]`

Ventaja: idempotente, solo re-embed fotos nuevas/cambiadas ( `md5` ), no re-procesa toda la galería en cada restart. Schema `pa.list_(pa.float32(),128)` indexable para vector search (aunque `recognize()` es brute centroid, no ANN). Dependencias: `lancedb + pyarrow + pandas`.

### 3) `SimpleTracker + track_skip_frames + recheck + aggregate` `live_face_pipeline.py:~520-760`

- `SimpleTracker(iou_threshold=0.3, max_missed=10).update(boxes, frame_count)` greedy IoU sin lib externa; `tracks{ bbox, first_frame, last_seen, name, score, last_recog_frame, embeddings:[] }`
- En main loop: `frames_tracked = frame_count - track['first_frame']`; `due = last_recog is None or frame-last_recog >= track_recheck_interval(15)`; `if frames_tracked < track_skip_frames(5): name='Tracking...' else if due: quality/pose gates → emb → agg=aggregate_track_embedding(embeddings, emb, window=5) → recognize(...)`
- `aggregate_track_embedding` rolling mean `np.mean(window)` L2 → damps single-frame noise (`0.600 vs 0.612` observed).

Docstring: "(a) skip first few frames avoids blurry entrance (single biggest accuracy lever in hailo reference), (b) avoid re-running every frame".

### 4) Gates + alignment

- `get_face_detections(yolo, img, conf=0.5)` extrae `box, landmarks(5×2), landmark_conf, det_conf` de `yolov8n-face.pt`
- `align_face(img, landmarks, 112)` `REFERENCE_LANDMARKS_112 = [[38,51],[73,51],[56,71],[41,92],[70,92]]` `estimateAffinePartial2D(LMEDS) → warpAffine`
- Gates post-`update` pre-`recognize`: `landmark_conf <0.5 → NotAFace`, `quality_ok → LowQuality`, `pose <0.15 → OffAngle`, cada branch guarda crop en `detected_faces/<label>/` para review + `_enhanced.jpg` `CLAHE+sharpen` (no usado para embed).

## Recomendación — ¿adoptar LanceDB y per-person sin romper `embedding[128]`?

**Respuesta corta:** **No adoptar LanceDB ahora; sí adoptar per-person calibrada en dos fases + `track_skip`/`aggregate` ligero, manteniendo `embedding[128]` L2 intacto.** Razón: LanceDB añade deps pesadas server-side para ganancia nula con galería `<100`; per-person solo rinde con galería multi-foto y requiere recalibrado empírico.

### Fase 0 — Mantener (no tocar)

- `embedding[128]` L2 `float32` sin cambio (`face-embedding.js:12 l2Normalize`, `whiteboard.py:38 IdentidadVista` `cosine 0..2`). Cualquier threshold calibrado o centroid sigue siendo `dot(L2,L2)`. No migrar a 512-d.
- `localStorage:webcam.identities` + `identities.json` + `enroll_sync`/`purge`/`PendingSync`/`GET /identities` + bypass `N=1` (`enrollment-panel.js:50`). No reemplazar por LanceDB en browser.
- `REID_N=3 grace2` + `IoU>0.5 edad5` + `REID_EVERY=3 + IOU_TRIG=0.7` (`CONTEXT.md:100-101`). Probado 73 tests `Task 036`.

### Fase 1 — Adoptar ya (sin LanceDB, sin multi-foto, costo <2h)

1. **Centroid por persona**: en `findBestMatch()` y `IdentitiesStore` exponer `centroids[name]=mean(L2)` además de lista. Matching `max dot(emb, centroid)` en lugar de `min cosineDistance` por imagen. Con `N=1` fallback idéntico; con `N>=2` (promedio móvil cap5 `CONTEXT.md:94` ya produce 2-5 embeddings implícitos) mejora robustez. No rompe `embedding[128]`.

2. **`track_skip_frames` ligero + `aggregate_track_embedding(window=3)`**: en `runReId()` añadir `firstSeen Map trackId→frame` y `embeddingsWindow Map trackId→Float32Array[3]`. Skip `2-3` frames tras `tracker Map` creación antes de `cosineDistance`, ventana mean L2 antes de threshold. Mitiga `Tracking...` blur entrada sin pasar a `5` basabraj (que en `@10Hz` son 500ms de latencia percibida). Mantener `REID_EVERY=3` throttle; recheck cada `9-15` frames vía `shouldEmbed` ya cubre.

3. **Gates cheap client-side** (previo a `embed()`): `blur_score` Laplacian variance via offscreen 32×32 canvas `<0.3ms`, `pose symmetry` si `face-detector` algún día expone landmarks (hoy BlazeFace no → skip), `min_face_pixels` `0.08*0.18` ya en `mockFaceFromPerson:292` pero elevar a `>3% area` para re-id. Si gate falla → `estado posible` sin consumir `reIdHyst`. No guardar crops (privacidad).

4. **Margin 0.05**: en `findBestMatch()` tras `bestDist`/`secondDist`, si `1-bestDist - (1-secondDist) <0.05` → `desconocido` (runner-up cercano). Replica `recognize(..., margin)` basabraj sin threshold per-person.

### Fase 2 — Adoptar cuando galería multi-foto (requiere UX enroll + medición)

Solo si se implementa enroll multi-foto (3-5 fotos por nombre, ángulos/luz, como `enrolled_faces/<name>/*.jpg`), entonces:

5. **Per-person calibrated** `calibrate_person_thresholds(gallery, low=0.60, high=0.65)` JS port: `svd` via `ml-matrix` o aproximación `std dev` simple `area ≈ σ_x·σ_y`. Ejecutar en `loadGallery()` cada `hydrateFromServer` o en `backend/models/identities.json` al `lifespan`. Fallback `recog_threshold 0.42 distancia` si `len<2`. **Recalibrar empíricamente**: medir `inter_max` y `intra_min/mean` propias (basabraj midió `0.569 / 0.673-0.865`) antes de fijar `low/high`; no usar `0.1-0.9` hailo.

6. **Opcional server-side LanceDB**: solo si `#embeddings >500` o se quiere ANN `cosine` server-side desacoplado del browser. Mantener `embedding[128]` schema `pa.list_(float32,128)` idéntico; `lancedb.connect("plataforma/webcam/gallery_db")` + `sync_gallery_db` como cache de `identities.json`, no como reemplazo de `localStorage`. Coste: añade `lancedb 0.8+ + pyarrow + pandas` ~120MB wheel + `uv add` + CI slow. No justificado con <100 identidades.

### Qué NO hacer

- No cambiar `EMBEDDING_DIM` ni normalización; `mobilefacenet.onnx` 128-d entrega L2, basabraj .pb 128-d igual. Migrar a 512-d (`w600k_mbf.onnx`) rompería `IdentitiesStore` y `whiteboard.py` contrato.
- No copiar `threshold_low=0.1 high=0.9` hailo → genera FN 50% o FP cross-person medido.
- No mover embedding a server LanceDB como única fuente → rompe privacidad client-side y `PendingSync` offline.
- No reemplazar `IoU>0.5 edad5` por `IoU>0.3` sin A/B: más permisivo aumenta ID switch en multi-person (nuestro caso 3 caras simultáneas `CONTEXT.md:103`).

## Riesgos & mitigación (per-person + tracking)

| Riesgo | Prob | Impacto | Mitigación |
|---|---|---|---|
| Per-person con 1 foto → thr uniforme, falsa sensación de calibrado | Alta | Medio | Fase gate: solo calibrar si `min(len(per_person))>=3`; sino usar fijo `0.42` + log `threshold=uniform` |
| Calibrado sin medición inter_max → FP cross-person si `low < inter_max` | Media | Alto | Medir `inter_max` e `intra_min` locales antes de fijar `low/high` (script `plataforma/webcam/scripts/calibrate-thr.py` offline con embeddings reales) |
| `track_skip 5` a 10Hz → 500ms "Tracking..." sin badge útil | Media | Medio | Usar `skip=2-3` + ventana `3` en lugar de `5+15`; mantener `REID_EVERY=3` |
| Gates blur/pose en browser → false `LowQuality` en low-light legítimo | Media | Medio | Thresholds bajos (`blur 30` no `50`, `pose 0.15` no `0.4`) como basabraj recalibró; fallback `possible` no `desconocido` |
| LanceDB añade `pyarrow` binario CI pesado, `uv sync --all-packages` rompe | Alta | Alto | No adoptar hasta galería >500; si se adopta aislar en `plataforma/webcam/backend/gallery_db.py` con `optional = true` grupo `uv` |

## Próximos pasos (desbloquea Ticket 042)

- Grilling `042` decide: `WhiteboardState.last_identidades` extiende `IdentidadVista.estado` con `threshold_per_person?: number` opcional para debug, sin romper payload (compat `detecciones + identities`).
- Prototype `043` valida UX `Hola <nombre>` con nuevo centroid+skip+margin en `prototype-leaky-reid.html` throwaway.
- Medición headless `uv run pytest plataforma/webcam -q` con frames sintéticos + `stubEmbedding` seed fijo para inter/intra dist.

## Verificación

- No se modificó `plataforma/` prod — solo lectura + este ticket `docs/wayfinder/tickets/038-research-basabraj-reid.md`.
- `embedding[128]` preservado: ambas fuentes 128-d L2; `face-embedding.js:60` `new Float32Array(128)` y `live_face_pipeline.py:EMBEDDING_DIM=128` idénticos.
- Fuentes externas auditables: raw `live_face_pipeline.py` vía `webfetch Raw`, grep `calibrate_person_thresholds|threshold_low|lancedb|track_skip` reproducibles arriba.

> Estado final: **cerrado** — tabla + recomendación entregadas; desbloquea `042 Grilling Whiteboard` (per-person centroid + skip + gates, LanceDB diferido).

## Blocking

- Bloquea a 042. Desbloqueado (frontera) — este ticket lo desbloquea al cerrar.
