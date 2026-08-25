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

> Estado: **abierto** — frontera. Claim antes de trabajar. Responder vía grilling round.
