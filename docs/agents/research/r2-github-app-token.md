# R2 — Pipeline de GitHub Actions con token de GitHub App

## Pregunta

¿Cómo armar un pipeline de GitHub Actions que use un token de GitHub App (en vez del `GITHUB_TOKEN`), para que el CI del agente corra sobre los PRs que el propio agente abre? La pregunta cubre: la acción `actions/create-github-app-token`, los permisos exactos de la app, el mecanismo anti-bucle de eventos, cómo crear/instalar la app, cómo leer el estado de una review, cómo editar el cuerpo del PR y los labels, y las limitaciones conocidas.

## Hallazgos

### 1. La acción `actions/create-github-app-token`

- La acción crea un **installation access token** para una GitHub App usando `POST /app/installations/{installation_id}/access_tokens`. El token expira a la **hora** y es **revocado** en el step `post` de la acción (no se puede pasar a otro job salvo que se use `skip-token-revoke: true`). Se expone como output `token`, `installation-id` y `app-slug`.
  Fuente: https://github.com/actions/create-github-app-token (secciones "How it works", "Important", "Outputs")

- **Inputs**: `client-id` (obligatorio; el legacy `app-id` se acepta pero se recomienda `client-id`), `private-key` (obligatorio; los `\n` escapados se reemplazan por saltos de línea reales), `owner` (opcional; por defecto el owner del repo actual), `repositories` (opcional; lista separada por comas o saltos de línea), `enterprise`, `permission-<nombre>` (para limitar permisos del token, ej. `permission-contents: write`), `skip-token-revoke`, `github-api-url`.
  Fuente: https://github.com/actions/create-github-app-token (sección "Inputs")

- **Alcance del token según inputs**: sin `owner`/`repositories` queda acotado al repo actual; `owner` sin `repositories` da acceso a todos los repos de la instalación de ese owner; `repositories` lo acota a esos repos. Los `repositories` pueden incluir owner (`owner/repo`).
  Fuente: https://github.com/actions/create-github-app-token (sección "Inputs")

- **Permisos del token**: por defecto hereda **todos** los permisos de la instalación. Se recomienda listar explícitamente los permisos con `permission-<nombre>` (ej. `permission-pull-requests: write`). Si se pide un permiso que la instalación no tiene, la acción **falla con error**.
  Fuente: https://github.com/actions/create-github-app-token (sección "Create a token with specific permissions" y "Inputs")

- **Secrets/variables en Actions**: el README indica guardar el Client ID como **variable** del repo (ej. `APP_CLIENT_ID`) y la **private key como secret** (ej. `APP_PRIVATE_KEY`), y usarlos con `${{ vars.APP_CLIENT_ID }}` y `${{ secrets.APP_PRIVATE_KEY }}`.
  Fuente: https://github.com/actions/create-github-app-token (sección "Usage") y https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/making-authenticated-api-requests-with-a-github-app-in-a-github-actions-workflow (pasos 2 y 3)

- La documentación oficial de GitHub describe el flujo completo: (1) registrar la app con los permisos necesarios, (2) guardar el **client ID** como variable de Actions, (3) **generar private key** y guardar el archivo PEM completo (incluyendo `-----BEGIN RSA PRIVATE KEY-----` y `-----END RSA PRIVATE KEY-----`) como secret, (4) **instalar la app** en la cuenta y repos que el workflow necesite, (5) crear el token con `actions/create-github-app-token@v3` y usarlo (ej. con `gh api`).
  Fuente: https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/making-authenticated-api-requests-with-a-github-app-in-a-github-actions-workflow

- Nota: el `GITHUB_TOKEN` no alcanza cuando hay que acceder a recursos fuera del repo del workflow (org, otro repo); para eso se usa una GitHub App.
  Fuente: https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/making-authenticated-api-requests-with-a-github-app-in-a-github-actions-workflow (sección "About GitHub Actions authentication")

### 2. Permisos exactos de la GitHub App

- **`contents: write`**: "repository contents, commits, branches, downloads, releases, and merges". Es lo que habilita crear ramas, commitear y hacer push sobre el repo. También es el permiso necesario para acceso Git autenticado por HTTP (`git clone https://x-access-token:TOKEN@github.com/owner/repo.git`). Si el agente edita archivos bajo `.github/workflows/`, necesita además el permiso **`workflows`**.
  Fuente: https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/choosing-permissions-for-a-github-app (sección "Choosing permissions for Git access") y https://docs.github.com/en/rest/apps/apps?apiVersion=2022-11-28 (body de `POST /app/installations/{id}/access_tokens`)

- **`pull_requests: write`**: "pull requests and related comments, assignees, labels, milestones, and merges". Habilita abrir/actualizar/mergear PRs y asignar labels/milestones en PRs.
  Fuente: https://docs.github.com/en/rest/apps/apps?apiVersion=2022-11-28 (body de `POST /app/installations/{id}/access_tokens`)

- **`issues: write`**: "issues and related comments, assignees, labels, and milestones". Habilita gestionar issues y sus labels (los labels de un PR se gestionan por la API de issues, ver sección 6).
  Fuente: https://docs.github.com/en/rest/apps/apps?apiVersion=2022-11-28 (body de `POST /app/installations/{id}/access_tokens`) y https://docs.github.com/en/rest/issues/labels?apiVersion=2022-11-28 (sección "About labels")

- **`checks: read`**: permite leer checks ("checks on code"). Con `write` además se crean/actualizan check runs. Un app necesita al menos **read** de `Checks` para suscribirse a los webhooks `check_run`/`check_suite`.
  Fuente: https://docs.github.com/en/rest/apps/apps?apiVersion=2022-11-28 (body de `POST /app/installations/{id}/access_tokens`) y https://docs.github.com/en/webhooks/webhook-events-and-payloads (secciones `check_run` y `check_suite`)

- Un token de instalación **no puede pedir permisos que la app no tenga**, ni acceder a repos fuera de la instalación. Si la API recibe un request con permisos insuficientes, responde `403` (o `404` por razones de seguridad, ver sección 7), y el header `X-Accepted-GitHub-Permissions` indica qué permisos se necesitan.
  Fuente: https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/choosing-permissions-for-a-github-app (sección "Choosing permissions for REST API access") y https://docs.github.com/en/rest/apps/apps?apiVersion=2022-11-28 (endpoint `POST /app/installations/{id}/access_tokens`)

### 3. Mecanismo anti-bucle (por qué el GITHUB_TOKEN no re-dispara y el de la app sí)

- Cuando un workflow usa el `GITHUB_TOKEN` del repo, **los eventos que ese token dispara NO crean un nuevo workflow run**, con estas excepciones: `workflow_dispatch` y `repository_dispatch` siempre corren; y un `pull_request` `opened`/`synchronize`/`reopened` creado con `GITHUB_TOKEN` crea runs en estado **"approval-required"** (un humano con write debe aprobar). Ejemplo textual de la doc: "if a workflow run pushes code using the repository's GITHUB_TOKEN, a new workflow will not run even when the repository contains a workflow configured to run when push events occur". Esto previene loops recursivos.
  Fuente: https://docs.github.com/en/actions/concepts/security/github_token (sección "When GITHUB_TOKEN triggers workflow runs")

- Para que el CI corra **sin aprobación** sobre PRs creados por automatización, la doc dice explícitamente: "use a GitHub App installation access token or a personal access token instead of GITHUB_TOKEN when creating or updating the pull request".
  Fuente: https://docs.github.com/en/actions/concepts/security/github_token (nota en "When GITHUB_TOKEN triggers workflow runs")

- Consecuencia para el pipeline del agente: si el agente abre/actualiza el PR con un **token de GitHub App**, los eventos `pull_request`/`push` que eso genere sí disparan los workflows normalmente, permitiendo el CI en el PR del agente. (Esto es lo que hace viable "CI en el PR del agente": el commit debe hacerse con el token de la app, no con `GITHUB_TOKEN`.)

### 4. Cómo crear e instalar una GitHub App

- **UI**: Settings → Developer settings → GitHub Apps → New GitHub App. En la pantalla se configuran nombre (máx. 34 chars, único en GitHub), Homepage URL, **Permissions** (read-only / read & write / no access por permiso), "Subscribe to events", y "Where can this GitHub App be installed?" (Only on this account / Any account).
  Fuente: https://docs.github.com/en/apps/creating-github-apps/setting-up-a-github-app/creating-a-github-app

- **REST API**: NO existe un endpoint para crear una GitHub App directamente. La única vía programática es el **manifest flow**: se genera un código con el manifest y se completa con `POST /app-manifests/{code}/conversions`, que devuelve `id` (app id), `pem` (private key) y `webhook_secret` en la respuesta. La creación normal es por la UI.
  Fuente: https://docs.github.com/en/rest/apps/apps?apiVersion=2022-11-28 (endpoint "Create a GitHub App from a manifest")

- **Private key**: se genera desde la página de la app (Edit → Private keys → Generate a private key). Se descarga un PEM `PKCS#1 RSAPrivateKey`; GitHub solo guarda la parte pública. Se pueden tener hasta 25 keys por app, no expiran (se revocan manualmente). El **App ID** (numérico) se ve en la página de la app; el **client ID** está en la misma página de settings y es distinto del app id.
  Fuente: https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/managing-private-keys-for-github-apps

- **Instalación**: en la página de la app → Edit → Install App → elegir "All repositories" o "Only select repositories" y seleccionar los repos. La instalación queda asociada a la cuenta (usuario u org); los permisos que el token pueda usar son los **otorgados a la instalación**.
  Fuente: https://docs.github.com/en/apps/using-github-apps/installing-your-own-github-app

- **Obtener el app-id**: vía REST se puede leer la app autenticada con `GET /app` (requiere JWT), o simplemente copiarlo de la página de settings de la app. La acción acepta `app-id` (legacy) o `client-id` (recomendado).
  Fuente: https://docs.github.com/en/rest/apps/apps?apiVersion=2022-11-28 (endpoint "Get the authenticated app") y https://github.com/actions/create-github-app-token (input `client-id`/`app-id`)

### 5. Estado de una review de PR

- **Lectura**: `GET /repos/{owner}/{repo}/pulls/{pull_number}/reviews` lista las reviews en orden cronológico. Cada review tiene un campo `state`, más `body`, `user`, `submitted_at`, `commit_id`.
  Fuente: https://docs.github.com/en/rest/pulls/reviews?apiVersion=2022-11-28 (endpoint "List reviews for a pull request")

- **Valores de `state` en la respuesta**: `APPROVED`, `CHANGES_REQUESTED`, `COMMENTED`, `DISMISSED`, `PENDING` (GraphQL enum `PullRequestReviewState` y ejemplos de respuesta REST con `"state": "CHANGES_REQUESTED"`). Ojo: el ticket menciona `REQUEST_CHANGES`, pero ese valor es el **event** que se envía al crear/subir una review (`event`: `APPROVE`, `REQUEST_CHANGES`, `COMMENT`); al **leer**, el estado de cambios pedidos se reporta como `CHANGES_REQUESTED`.
  Fuente: https://docs.github.com/en/rest/pulls/reviews?apiVersion=2022-11-28 (endpoints "Create a review" y "Submit a review": enum de `event`) y https://docs.github.com/en/enterprise-server@3.6/rest/pulls/reviews (respuesta de ejemplo con `state: CHANGES_REQUESTED`)

- **Webhook `pull_request_review`**: se dispara con actions `submitted`, `edited`, `dismissed`; el payload lleva `pull_request` (objeto) y `review` (objeto con el estado de la review). Una app necesita al menos **read** del permiso "Pull requests" para suscribirse.
  Fuente: https://docs.github.com/en/webhooks/webhook-events-and-payloads (sección `pull_request_review`)

- **Crear/subir review** (útil si el agente responde con un approve): `POST /repos/{owner}/{repo}/pulls/{pull_number}/reviews` con `event: APPROVE | REQUEST_CHANGES | COMMENT` y `body` obligatorio para `REQUEST_CHANGES` y `COMMENT`. Reviews en `PENDING` no se cuentan como submitidas (hay que submitir con `POST .../reviews/{review_id}/events`).
  Fuente: https://docs.github.com/en/rest/pulls/reviews?apiVersion=2022-11-28 (endpoints "Create a review for a pull request" y "Submit a review for a pull request")

### 6. Editar el cuerpo del PR y los labels

- **Leer/actualizar PR**: `PATCH /repos/{owner}/{repo}/pulls/{pull_number}` con body `{ "title": ..., "body": ... }` actualiza el PR (devuelve el PR completo). Para actualizar el **cuerpo** del PR (contador de iteraciones) alcanza con el permiso de "Pull requests" (write) y/o "Contents" sobre la rama head.
  Fuente: https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28 (endpoint "Update a pull request")

- **Labels**: los labels de issues y PRs se manejan con la API de issues porque "every pull request is an issue". Endpoints:
  - Añadir: `POST /repos/{owner}/{repo}/issues/{issue_number}/labels` con `{ "labels": ["name"] }`.
  - Reemplazar todos: `PUT /repos/{owner}/{repo}/issues/{issue_number}/labels` (pasando array vacío se quitan todos).
  - Quitar uno: `DELETE /repos/{owner}/{repo}/issues/{issue_number}/labels/{name}` (404 si no existe).
  - Quitar todos: `DELETE /repos/{owner}/{repo}/issues/{issue_number}/labels`.
  - Crear label en el repo (si no existe): `POST /repos/{owner}/{repo}/labels` con `name` y `color`.
  Fuente: https://docs.github.com/en/rest/issues/labels?apiVersion=2022-11-28 (endpoints "Add labels to an issue", "Set labels for an issue", "Remove a label from an issue", "Remove all labels from an issue", "Create a label")

- El ciclo propuesto (labels `ready-for-agent` / `agent:in-progress` / `needs-human-attention` + contador de iteraciones en el body del PR) es viable con los endpoints de arriba, siempre que el token tenga `issues: write` (para labels) y `pull_requests: write` (para el body del PR).

### 7. Limitaciones conocidas y gotchas

- **Rate limits**: una GitHub App autenticando con installation token tiene mínimo **5.000 requests/hora**; si la instalación está en una org de GitHub Enterprise Cloud, **15.000/hora**. Escala con repos y usuarios: +50/h por cada repo >20 y +50/h por cada usuario >20, sin superar 12.500/h. El `GITHUB_TOKEN` de Actions tiene **1.000/h por repo**.
  Fuente: https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api (secciones "Primary rate limit for GitHub App installations" y "Primary rate limit for GITHUB_TOKEN")

- **Secondary rate limits**: máximo 100 requests concurrentes; ~900 puntos/min por endpoint (GET=1 punto, POST/PATCH/PUT/DELETE=5 puntos); no más de **80 requests generadoras de contenido por minuto** y 500/h. Crear PRs/reviews demasiado rápido dispara secondary limits (los endpoints de review/merge lo advierten explícitamente). Respuesta con `403`/`429`; respetar `retry-after` o `x-ratelimit-reset`.
  Fuente: https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api (sección "About secondary rate limits") y https://docs.github.com/en/rest/pulls/reviews?apiVersion=2022-11-28 (nota en "Create a review")

- **Expiración del token**: los installation tokens expiran a la **1 hora**; con expirado se recibe `401 Unauthorized` y hay que crear uno nuevo. Además, `actions/create-github-app-token` revoca el token al terminar el job (salvo `skip-token-revoke`), así que no se puede reutilizar entre jobs.
  Fuente: https://docs.github.com/en/rest/apps/apps?apiVersion=2022-11-28 (endpoint "Create an installation access token for an app") y https://github.com/actions/create-github-app-token ("How it works")

- **"Permission denied" / gotchas**:
  - App sin permisos suficientes → `403` "Resource not accessible by integration". El header `X-Accepted-GitHub-Permissions` indica qué permisos faltan (ej. `contents=write`, `pull_requests=write`).
  - Requests no autenticados a recursos privados → **`404 Not Found`** a propósito (GitHub no confirma la existencia de repos privados). Si un endpoint conocido devuelve 404, revisar auth/permisos/URL (trailing slash, URL-encoding, método HTTP).
  - Los permisos de la **instalación** pueden diferir de los de la **app**: si después de instalar se agregan permisos a la app, el admin de la cuenta debe **aprobar** los nuevos permisos; hasta entonces la instalación sigue con los viejos. Pedir en el token un permiso que la instalación no tiene hace fallar a la acción.
  - Un installation token solo afecta recursos del **owner donde está instalada la app** y de los **repos que la instalación puede ver**; listar repos de una org devuelve solo los accesibles a la instalación.
  Fuente: https://docs.github.com/en/rest/using-the-rest-api/troubleshooting-the-rest-api (secciones "Resource not accessible", "404 Not Found", "Missing results"), https://github.com/actions/create-github-app-token (nota en "Create a token with specific permissions") y https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/choosing-permissions-for-a-github-app (sección "About changes to permissions")

- **Workflows**: si el agente necesita tocar archivos de `.github/workflows/`, el permiso "Contents" no alcanza; se requiere el permiso **Workflows** (write).
  Fuente: https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/choosing-permissions-for-a-github-app (sección "Choosing permissions for Git access")

## Recomendación

Para el pipeline del agente en este repo (`mauriciosoyastor/embodied-ai`):

1. **Crear una GitHub App** por la UI (Settings → Developer settings → GitHub Apps → New GitHub App) con permisos: `Contents: Read & write`, `Pull requests: Read & write`, `Issues: Read & write`, `Checks: Read-only`. Instalarla en el repo del proyecto (o en la cuenta, "All repositories"/"Only select repositories").
2. **Guardar credenciales en Actions**: `APP_CLIENT_ID` como variable del repo y `APP_PRIVATE_KEY` (el PEM completo) como secret del repo.
3. **En los workflows**: primer paso `actions/create-github-app-token@v3` con `client-id: ${{ vars.APP_CLIENT_ID }}`, `private-key: ${{ secrets.APP_PRIVATE_KEY }}`, y outputs `token`/`app-slug`. Para git push usar el token con `persist-credentials: false` y armar el committer como `<app-slug>[bot] <user-id>+<app-slug>[bot]@users.noreply.github.com`; para la API usar `gh api` con `GH_TOKEN` del token.
4. **Commitear/pushear y abrir/actualizar el PR con el token de la app** (nunca con `GITHUB_TOKEN`) para que el CI corra automáticamente sobre el PR del agente sin requerir aprobación humana. El `GITHUB_TOKEN` se usa solo para leer/ejecutar el propio workflow.
5. **Estado de review**: leer `GET /repos/{owner}/{repo}/pulls/{n}/reviews` y mirar el `state` de la última review. Recordar que en lecturas el estado es `APPROVED`/`CHANGES_REQUESTED`/`COMMENTED` (y `PENDING`/`DISMISSED`); `REQUEST_CHANGES` solo se usa como `event` al **escribir** una review.
6. **Ciclo de labels/contador**: `POST/PUT/DELETE .../issues/{issue_number}/labels` para `ready-for-agent` / `agent:in-progress` / `needs-human-attention`, y `PATCH /repos/{owner}/{repo}/pulls/{n}` para incrementar el contador de iteraciones en el body.
7. **Operar bajo el límite**: mantener el número de API calls bajo el rate limit (mín. 5.000/h), espaciar la creación de PRs/reviews (80 content-requests/min) y respetar headers `retry-after`/`x-ratelimit-*`.

## Fuentes

- https://github.com/actions/create-github-app-token — README de la acción (inputs, outputs, how it works, ejemplos).
- https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/making-authenticated-api-requests-with-a-github-app-in-a-github-actions-workflow — flujo de autenticación con GitHub App en Actions.
- https://docs.github.com/en/actions/concepts/security/github_token — GITHUB_TOKEN y cuándo re-dispara workflows (anti-bucle).
- https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/choosing-permissions-for-a-github-app — elegir permisos de una GitHub App.
- https://docs.github.com/en/rest/apps/apps?apiVersion=2022-11-28 — endpoints de apps (manifest, installation access token, permisos por token).
- https://docs.github.com/en/apps/creating-github-apps/setting-up-a-github-app/creating-a-github-app — crear la app por UI.
- https://docs.github.com/en/apps/creating-github-apps/authenticating-with-a-github-app/managing-private-keys-for-github-apps — generar/almacenar private keys.
- https://docs.github.com/en/apps/using-github-apps/installing-your-own-github-app — instalar la app.
- https://docs.github.com/en/rest/pulls/reviews?apiVersion=2022-11-28 — listar/crear/submitir reviews (y enum de `event`).
- https://docs.github.com/en/enterprise-server@3.6/rest/pulls/reviews — ejemplo de respuesta con `state: CHANGES_REQUESTED`.
- https://docs.github.com/en/webhooks/webhook-events-and-payloads — payload de `pull_request_review` y requisitos de permiso de webhooks.
- https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28 — `PATCH /pulls/{pull_number}` (update).
- https://docs.github.com/en/rest/issues/labels?apiVersion=2022-11-28 — endpoints de labels.
- https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api — rate limits primarios y secundarios.
- https://docs.github.com/en/rest/using-the-rest-api/troubleshooting-the-rest-api — gotchas de 403/404, `X-Accepted-GitHub-Permissions`, alcance de la instalación.
