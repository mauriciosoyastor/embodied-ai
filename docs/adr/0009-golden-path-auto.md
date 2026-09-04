# 0009 — Modo `--auto` de Golden Path (auto local + pendientes remotos)

**Status**: accepted (2026-09-03, aprobado con punto de retorno).

**Nota**: el modo vive en el comando propio `/golden-auto`
(`.opencode/commands/golden-auto.md`); `/golden-path` queda paso a paso.

**Context**: el comando `/golden-path` (ADR-0008) pedía aprobación por paso
(`AGENTS.md`), unas 6 frenadas por corrida. Se propuso automatizarlo en tres
bloques: kickoff multiorigen con ráfaga sin paradas y panel único, bucle de
desarrollo autónomo con entrega automática (`push` + `gh pr create`), y
limpieza post-merge local (hook vs `sync`). La evaluación mostró dos choques:
la ráfaga sin paradas viola los gates obligatorios de las skills (`to-tickets`
reitera hasta aprobar el corte, `gitnexus-plan` pregunta profundidad,
`gitnexus-lfg` Lane 2 es bloqueante) y la entrega automática viola el
human-gate local (`harness` + `AGENTS.md`; el pipeline AFK que abre PRs corre
en GitHub Actions, no en la máquina). El hook `post-merge` no se versiona.

**Decision**: comando `/golden-auto` de doble zona
(`.opencode/commands/golden-auto.md`): invocar equivale a aprobar por
adelantado pasos locales y defaults recomendados. La máquina auto-selecciona profundidad (`Standard`), corte de
tickets y `Proceed`, investiga y construye de corrido. Auto-reparación acotada:
máximo 3 reintentos por paso (espejo del loop `N=3` → `needs-human-attention`
del pipeline AFK); reviews con un solo fix-cycle. Nunca auto: publicar tickets,
`push`, `gh pr create`, `gh issue close`, merge. Al terminar entrega panel
único con **Hecho** (todo lo local y reversible) y **Pendiente tu OK** (lista
numerada de escrituras remotas, se ejecutan solo con elección explícita).
Regla de oro: lo que `git` puede deshacer lo decide la máquina; lo que deja
huella afuera lo decide el humano. Sin `--auto`, rige el modo paso a paso.

**Considered Options**:
- **Ráfaga total sin paradas (incluye push/PR)**: descartada — viola
  `AGENTS.md` y human-gate; un corte mal publicado contamina el tracker.
- **Hook `post-merge` para limpieza**: descartado — `.git/hooks/` no se
  versiona, corre en cada `pull` aunque no toque golden-path.
- **`/golden-path sync` bajo demanda**: adoptado a futuro; el layout
  `.opencode/issues/active|archive/` ya existe como espejo local gitignorado
  (ver `.opencode/issues/README.md`); fuera de este ADR.

**Consequences**:
- `/golden-path` sin flags no cambia (6 gates). `--auto` reduce a 1 decisión.
- Punto de retorno de este cambio: HEAD `a39e85d` + patch
  `rollback-golden-path-pre-auto.patch` en temp + archivos nuevos listados en
  el reporte de sesión. Reversión: `git apply -R` del patch + borrar
  `golden-path.md` (gitignored, solo local), `0008`, `0009`, `0007` y la fila
  `0007` del índice de lessons. No toca cambios pre-existentes ajenos
  (`plataforma/…`, `.claude/`, `.scratch/`).
- Si `--auto` no funciona (cortes malos, gasto de turns), se revierte este ADR
  y el bloque `--auto` del comando, quedando el modo paso a paso intacto.
