#!/usr/bin/env bash
# ============================================================
# runai — ADE Task Execution CLI
# Usage: runai <project_name> "<task>" [--max-retries N]
# ============================================================
set -euo pipefail

# ── Colours ─────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; RESET='\033[0m'

info()    { echo -e "${CYAN}[ADE]${RESET} $*"; }
success() { echo -e "${GREEN}✅${RESET} $*"; }
warn()    { echo -e "${YELLOW}⚠${RESET}  $*"; }
error()   { echo -e "${RED}✗${RESET}  $*" >&2; exit 1; }

# ── Args ─────────────────────────────────────────────────────
if [[ $# -lt 2 ]]; then
    echo "Usage: runai <project_name> \"<task>\" [--max-retries N]"
    echo ""
    echo "Examples:"
    echo "  runai my_api \"create a Product model with name and price\""
    echo "  runai my_api \"add DELETE endpoint for Product\" --max-retries 5"
    exit 1
fi

PROJECT_NAME="$1"
TASK="$2"
shift 2
MAX_RETRIES=3

while [[ $# -gt 0 ]]; do
    case "$1" in
        --max-retries) MAX_RETRIES="$2"; shift 2 ;;
        *) error "Unknown argument: $1" ;;
    esac
done

# ── Validate env ─────────────────────────────────────────────
ADE_BASE="${ADE_BASE:-$HOME/hub/00_own/ADE}"
ADE_PROJECTS="${ADE_PROJECTS:-$ADE_BASE/projects}"
PROJECT_PATH="$ADE_PROJECTS/$PROJECT_NAME"

if [[ ! -d "$PROJECT_PATH" ]]; then
    error "Project '$PROJECT_NAME' not found at $PROJECT_PATH\n   Run: newproj $PROJECT_NAME --type django"
fi

# ── Check Ollama ─────────────────────────────────────────────
if ! curl -sf "$OLLAMA_API_BASE/api/tags" > /dev/null 2>&1; then
    warn "Ollama does not appear to be running at $OLLAMA_API_BASE"
    warn "Start it with: ollama serve"
    error "Cannot proceed without Ollama."
fi

# ── Banner ───────────────────────────────────────────────────
echo ""
echo -e "${BOLD}🤖 ADE — Running Task${RESET}"
echo -e "   Project : ${CYAN}${PROJECT_NAME}${RESET}"
echo -e "   Task    : ${CYAN}${TASK}${RESET}"
echo -e "   Retries : ${CYAN}${MAX_RETRIES}${RESET}"
echo ""

# ── Execute ──────────────────────────────────────────────────
ADE_PYTHON="${ADE_BASE}/.venv/bin/python"
if [[ ! -x "$ADE_PYTHON" ]]; then
    ADE_PYTHON="python3"
fi

"$ADE_PYTHON" "$ADE_BASE/ade_agent.py" "$PROJECT_NAME" "$TASK" --max-retries "$MAX_RETRIES"
EXIT_CODE=$?

echo ""
if [[ $EXIT_CODE -eq 0 ]]; then
    success "Task complete."
else
    echo -e "${RED}❌ Task failed (exit $EXIT_CODE)${RESET}"
    echo -e "   Check the output above for details."
fi
exit $EXIT_CODE
