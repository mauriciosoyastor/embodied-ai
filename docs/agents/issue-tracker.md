# Issue tracker: Local Markdown

Issues, specs, y mapas de wayfinder para el proyecto **Embodied AI** viven como archivos markdown dentro de esta carpeta del proyecto.

## Convenciones

- Un feature por directorio: `.scratch/<feature-slug>/`
- El spec es `.scratch/<feature-slug>/spec.md`
- Los tickets son un archivo por ticket en `.scratch/<feature-slug>/issues/<NN>-<slug>.md`, numerados desde `01` — nunca un solo archivo combinado
- El estado de triage se registra en una línea `Status:` cerca del inicio (ver `triage-labels.md` para los roles)
- Los comentarios e historial de conversación se agregan al final bajo un encabezado `## Comments`

## Cuando una skill dice "publicar al issue tracker"

Crea un archivo nuevo bajo `.scratch/<feature-slug>/` (creando el directorio si hace falta).

## Cuando una skill dice "traer el ticket relevante"

Lee el archivo en la ruta referenciada. El usuario normalmente pasa la ruta o el número directamente.

## Operaciones de wayfinding

Usadas por `/wayfinder`. El **mapa** es un archivo con un **archivo hijo** por ticket.

- **Mapa**: `.scratch/<effort>/map.md` — el cuerpo con Notes / Decisions-so-far / Fog.
- **Ticket hijo**: `.scratch/<effort>/issues/NN-<slug>.md`, numerado desde `01`, con la pregunta en el cuerpo. Una línea `Type:` registra el tipo de ticket (`research`/`prototype`/`grilling`/`task`); una línea `Status:` registra `claimed`/`resolved`.
- **Bloqueos**: línea `Blocked by: NN, NN` cerca del inicio. Un ticket está desbloqueado cuando todos los archivos que lista están `resolved`.
- **Frontier**: escanear `.scratch/<effort>/issues/` por archivos que estén abiertos, desbloqueados y sin reclamar; primero por número gana.
- **Claim**: setear `Status: claimed` y guardar antes de cualquier trabajo.
- **Resolve**: agregar la respuesta bajo `## Answer`, setear `Status: resolved`, y agregar un context pointer (gist + link) a Decisions-so-far del mapa en `map.md`.