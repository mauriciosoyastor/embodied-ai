# Issue tracker: GitHub Issues

Issues, specs, y mapas de wayfinder para el proyecto **Embodied AI** viven como issues de GitHub en `mauriciosoyastor/embodied-ai`.

## Convenciones

- **Spec**: el spec de un esfuerzo se publica como issue en el repo (label `ready-for-agent` si aplica). Para mapas wayfinder, el **mapa** es un issue con label `wayfinder:map` y sus **tickets** son issues hijos con labels `wayfinder:<tipo>`.
- **Labels por tipo de ticket**: `wayfinder:research` (AFK), `wayfinder:prototype` (HITL), `wayfinder:grilling` (HITL), `wayfinder:task` (HITL/AFK).
- **Bloqueos**: relación nativa de sub-issues de GitHub. Un ticket está desbloqueado cuando todos sus sub-issues están cerrados.
- **Resolución**: la respuesta se postea como **comentario** en la issue (`## Answer`), luego se cierra la issue y se agrega un context pointer al mapa.

## Operaciones de wayfinding

Usadas por `/wayfinder`.

- **Mapa**: issue con label `wayfinder:map` — el cuerpo lleva Destination / Notes / Decisions-so-far / Not-yet-specified / Out-of-scope.
- **Ticket hijo**: issue con label `wayfinder:<tipo>`; la pregunta va en el cuerpo. Un sesión reclama un ticket asignándoselo (`gh issue edit N --add-assignee @me`).
- **Bloqueos**: `gh api -X POST repos/OWNER/REPO/issues/{parent}/sub_issues --input -` con body `{"sub_issue_id": <id numérico de la issue hija>}`. Nota: `sub_issue_id` es el **id numérico** de la issue (obtenible con `gh api repos/.../issues/N --jq .id`), no el número de issue.
- **Frontier**: `gh issue list` filtrando por `label:"wayfinder:research"`/etc., abiertas, sin asignar y sin sub-issues abiertos.
- **Claim**: `gh issue edit N --add-assignee @me` antes de trabajar.
- **Resolve**: comentario con `## Answer`, cerrar la issue (`gh issue close N`), y actualizar Decisions-so-far del mapa.

## Espejo local (Capa 1, no fuente de verdad)

GitHub sigue mandando. `.opencode/issues/` (gitignorado) es bandeja local:

- `active/<numero>-<slug>.md` — ticket en curso con brief + `Blocked by` + rama `feat/<slug-ticket>`.
- `archive/` — destino al cerrar (tras `## Answer` + close en GitHub).
- Ramas: default `feat/<slug-ticket>` vinculada a ticket; spikes <1 sesión pueden usar rama libre anotándolo antes del merge. `main` y `agent/*` prohibidos para trabajo manual.

## Comandos útiles

- Listar issues por label: `gh issue list --label "wayfinder:grilling"`
- Ver sub-issues de un ticket: `gh api repos/mauriciosoyastor/embodied-ai/issues/N/sub_issues`
- Crear issue: `gh issue create --title "..." --label "..." --body-file <archivo>`
