#!/usr/bin/env bash
# run_agent.sh — Wrapper del pipeline AFK.
# Desacopla la lógica de GitHub (contexto, ramas, labels, PRs, review) del
# execution-engine (anthropics/claude-code-action / claude -p).
# Modos: prepare | open_pr | review
set -euo pipefail

REPO="${GITHUB_REPOSITORY:-mauriciosoyastor/embodied-ai}"
ITER_MAX=3

MODE="${1:-}"
if [[ -z "$MODE" ]]; then
  echo "Uso: run_agent.sh <prepare|open_pr|review>" >&2
  exit 1
fi

require_gh() {
  if [[ -z "${GH_TOKEN:-}" ]]; then
    echo "GH_TOKEN no definido" >&2
    exit 1
  fi
}

write_output() {
  # Escribe clave=valor a GITHUB_OUTPUT si existe (GitHub Actions), si no a stdout.
  # Soporta valores multilínea usando el delimitador heredoc.
  local key="$1" value="$2"
  if [[ -n "${GITHUB_OUTPUT:-}" ]]; then
    if [[ "$value" == *$'\n'* ]]; then
      {
        echo "${key}<<_DELIM_"
        printf '%s' "$value"
        echo ""
        echo "_DELIM_"
      } >> "$GITHUB_OUTPUT"
    else
      echo "${key}=${value}" >> "$GITHUB_OUTPUT"
    fi
  else
    echo "${key}=${value}"
  fi
}

cmd_prepare() {
  require_gh
  local issue="${ISSUE_NUMBER:?ISSUE_NUMBER requerido}"
  local pull="${PULL_NUMBER:-}"
  local iter="${ITERATION:-1}"

  local issue_json title body labels slug branch
  issue_json="$(gh issue view "$issue" --repo "$REPO" --json title,body,labels -q .)"
  title="$(printf '%s' "$issue_json" | jq -r '.title')"
  body="$(printf '%s' "$issue_json" | jq -r '.body // ""')"
  labels="$(printf '%s' "$issue_json" | jq -r '[.labels[].name] | join(", ")')"

  slug="$(printf '%s' "$title" | tr '[:upper:]' '[:lower:]' \
    | sed 's/[^a-z0-9]\+/-/g' | sed 's/^-//; s/-$//' | cut -c1-40)"
  branch="agent/${issue}-${slug}"

  local bot="${APP_SLUG:-agent}"
  git config user.name "${bot}[bot]"
  git config user.email "${bot}[bot]@users.noreply.github.com"

  if [[ -n "$pull" ]]; then
    git fetch origin "$branch"
    git checkout -B "$branch" "origin/$branch"
  else
    git fetch origin main
    git checkout -B "$branch" origin/main
  fi

  # Ciclo de labels: quita el disparador, marca en progreso.
  gh issue edit "$issue" --repo "$REPO" --remove-label ready-for-agent --add-label agent:in-progress 2>/dev/null || true

  cat > .agent-prompt.md <<PROMPT
Eres un agente de software autónomo. Tu trabajo es resolver el issue completando TODAS las tareas en el repositorio usando tus herramientas (Edit, Write, Read, Glob, Grep, Bash).

REGLAS OBLIGATORIAS:
1. Implementa la solución modificando los archivos del repo con tus herramientas. NO respondas con instrucciones ni planes: actúa.
2. Corre los tests (pytest) y el linter (ruff) hasta que pasen.
3. Commitea los cambios con git (git add + git commit) y pushea la rama con git push.
4. No dejes trabajo sin commitear: el pipeline depende de que tu rama tenga commits.

Contexto del issue:

Título: ${title}
Issue: #${issue}
Labels: ${labels}

${body}

Iteración: ${iter}/${ITER_MAX}
PROMPT
  echo "Rama: ${branch}"
}

cmd_open_pr() {
  require_gh
  local issue="${ISSUE_NUMBER:?ISSUE_NUMBER requerido}"
  local pull="${PULL_NUMBER:-}"
  local iter="${ITERATION:-1}"
  local branch
  branch="$(git rev-parse --abbrev-ref HEAD)"

  local pr_title
  pr_title="$(gh issue view "$issue" --repo "$REPO" --json title -q .title)"

  local body="Closes #${issue}

**Iteración**: ${iter}/${ITER_MAX}"

  if [[ -z "$pull" ]]; then
    gh pr create --repo "$REPO" --base main --head "$branch" \
      --title "Agent: ${pr_title}" --body "$body"
  else
    gh pr edit "$pull" --repo "$REPO" --title "Agent: ${pr_title}" --body "$body" >/dev/null
  fi
}

cmd_review() {
  require_gh
  local pull="${PULL_NUMBER:?PULL_NUMBER requerido}"
  if [[ -z "${ANTHROPIC_AUTH_TOKEN:-}" ]]; then
    echo "ANTHROPIC_AUTH_TOKEN no definido" >&2
    exit 1
  fi

  local pr_body iter issue issue_title issue_body diff
  pr_body="$(gh pr view "$pull" --repo "$REPO" --json body -q .body)"
  iter="$(printf '%s' "$pr_body" | grep -oP '\*\*Iteración\*\*: \K[0-9]+' || echo 1)"
  issue="$(printf '%s' "$pr_body" | grep -oP 'Closes #\K[0-9]+' || echo '')"
  diff="$(gh pr diff "$pull" --repo "$REPO" || true)"

  if [[ -n "$issue" ]]; then
    issue_title="$(gh issue view "$issue" --repo "$REPO" --json title -q .title 2>/dev/null || true)"
    issue_body="$(gh issue view "$issue" --repo "$REPO" --json body -q .body 2>/dev/null || true)"
  else
    issue_title=""
    issue_body=""
  fi

  local prompt_file=".review-prompt.md"
  cat > "$prompt_file" <<'PROMPT'
Eres un reviewer senior de código (red-team). Revisa el PR contra los requisitos del issue.
Evalúa: adherencia al issue, seguridad, consistencia, calidad, tests.
Responde ÚNICAMENTE un objeto JSON válido sin markdown, con este esquema:
{"verdict": "approve" | "request_changes", "summary": "resumen en español", "findings": ["hallazgo 1", ...]}
PROMPT
  {
    echo ""
    echo "=== ISSUE ==="
    echo "# ${issue_title}"
    echo "${issue_body}"
    echo ""
    echo "=== DIFF ==="
    echo "${diff}"
  } >> "$prompt_file"

  local result verdict summary
  result="$(claude -p --bare --max-budget-usd 2 --output-format json < "$prompt_file" \
    || true)"
  verdict="$(printf '%s' "$result" | jq -r '.[-1].result // empty' 2>/dev/null \
    | jq -r '.verdict // empty' 2>/dev/null || true)"
  summary="$(printf '%s' "$result" | jq -r '.[-1].result // empty' 2>/dev/null \
    | jq -r '.summary // empty' 2>/dev/null || true)"
  if [[ -z "$verdict" ]]; then
    verdict="request_changes"
  fi
  if [[ -z "$summary" ]]; then
    summary="Review sin resumen (salida no parseable)."
  fi

  write_output "verdict" "$verdict"
  write_output "iteration" "$iter"
  write_output "issue" "$issue"
  write_output "summary" "$summary"
  echo "Verdict: ${verdict} (iter ${iter}/${ITER_MAX})" >&2
}

case "$MODE" in
  prepare) cmd_prepare ;;
  open_pr) cmd_open_pr ;;
  review) cmd_review ;;
  *) echo "Modo desconocido: ${MODE}" >&2; exit 1 ;;
esac
