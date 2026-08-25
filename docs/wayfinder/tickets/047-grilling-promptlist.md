# Ticket 047 — Grilling: PromptList estática 20 curada final + i18n

> Parent: `008-map-yolo-world-s-open-vocab` · Label: `wayfinder:grilling` · Estado: abierto · Tipo: HITL

## Question

Con `config.py:34 YOLO_WORLD_PROMPTLIST_STATIC` 20 `r2:242-268` (lista actual 22: `person, chair, couch, dining table, bed, toilet, tv, laptop, keyboard, mouse, cell phone, remote, bottle, cup, wine glass, bowl, book, backpack, handbag, potted plant, vase, clock` - recortar 2) + alternativa `r2:107` `cat, dog, bench` vs `toaster, scissors, teddy bear` y frases compuestas `red cup, yellow screwdriver, black remote control` `r2:266-268`:

¿Lista final 20? ¿Inglés puro CLIP `red cup with handle` vs español `taza roja` con mapping voz `yolo_world.py:95 extract_prompts_from_transcript` traducción `en<->es-AR`? ¿Formato `sustantivo + adjetivo color/forma` separado `.` `GroundingDINO "chair . person ."` `r2:189` vs `,`? ¿Background `""` clase `r2:189`? ¿Incluir `W30` 30 exactas vs solo 20 top frecuencia oficina `r2:115 +2-4 objetos/frame W30`? ¿Dónde vive mapeo `en->es` para `AtributoVista.color_hsv` español?

HITL `grilling` + `domain-modeling`: discutir escenarios `ws.py:_extract_atributos` `color_hsv 12 colores` + `color_vlm` VLM 1Hz `scene_caption` vs `color_hsv` <1ms; probar `YOLO_WORLD_DYNAMIC_BY_VOZ=False` default bleibt; definir término `PromptList` / `PromptList estática` en `CONTEXT.md` (glosario sin impl). Actualizar `CONTEXT.md` inline cuando `PromptList` se resuelva + proponer ADR si `en vs es` es hard-to-reverse.

## Notes

- Llamar skill `grilling` + `domain-modeling` (HITL, no responder por humano). Ver `r2:7 PromptList estática curada vs dinámica por voz` protocolo `set_classes` + `save` re-parametrizado `r2:273`.
- No modificar código; mapear con `CONTEXT.md:133 Whitelist W30` y `CONTEXT.md:134 AtributoVista`.

## Blocking

- Bloquea a 048, 049. Desbloqueado (frontera).

## Resolution

> Estado: **cerrado** — 2026-08-25 · HITL grilling + domain-modeling · Resuelto en sesión con usuario (Q1-Q5 aprobados)

### Decisión

- **Q1 Lista 20 estática — Opción A:** conservar 20 atómicas COCO `config.py:34` `person, chair, couch, dining table, bed, toilet, tv, laptop, keyboard, mouse, cell phone, remote, bottle, cup, wine glass, bowl, book, backpack, handbag, potted plant` — dimensión `20x512` liviana, frases `red cup/yellow screwdriver` reservadas para inyección dinámica por voz (evita `+5ms` fijo `r2:138`).
- **Q2 Idioma — inglés puro + mapeo capa voz:** detector estático `en` (`chair`, `red cup`) CLIP entrenado inglés corpora; diccionario `en<->es-AR` en interfaz/voz `yolo_world.py:95` (no tokenizar `es` directo que distorsiona coseno). `color_hsv` 12 colores español `CONTEXT.md:137` para voz `es-AR`.
- **Q3 Formato — `list[str]`:** `["person","cup"]` con `cleaned[:8]` `yolo_world.py:51` sanitización, abstrae librería subyacente, simplifica `pytest` unit (no string `". "` GroundingDINO `r2:189`).
- **Q4 Background `""` — no agregar:** `box_thr 0.35 text_thr 0.25` `r2:128` + `Whitelist W30` ya suprime FP sin ruido embed no estandarizado.
- **Q5 Glosario — sí:** añadidos `CONTEXT.md: PromptList Estática` (20 fijas loop continuo) + `PromptList Dinámica` (max 8 inyectados por voz) + `Mapeo en<->es-AR`.

### Escalabilidad acordada

- **Offline Text Feature Caching:** congelar `txt_feats 20x512` al boot `YoloWorldDetector` (si `is_stub False` + `warmup`) para no recalcular CLIP por frame `slow 2Hz` ni en restart.
- **Procesamiento Asíncrono:** parseo voz+traducción en `asyncio Task` secundario no bloquea `VideoCapture`/`fast_queue 10Hz`; `set_classes` debounce 500ms cooldown 2s `r2:284`.

### Artefactos

- `CONTEXT.md` actualizado: 3 términos nuevos `PromptList Estática/Dinámica, Mapeo en<->es-AR` (glosario sin impl).
- Mapa `008` → `Decisions so far` apunta a este ticket.

### Cierre

Bloqueo liberado: `048` ahora desbloqueado (faltaba solo `047`; `045`+`046` ya cerrados research). `049` sigue bloqueado por `048`.
