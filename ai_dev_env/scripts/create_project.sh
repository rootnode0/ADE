#!/bin/bash

# =========================
# 🧠 Load env safely
# =========================
if [ -z "$ADE_BASE" ]; then
  echo "❌ ADE_BASE not set. Load environment first"
  exit 1
fi

ENV_FILE="$ADE_BASE/ai_dev_env/config/env.sh"

if [ -f "$ENV_FILE" ]; then
  source "$ENV_FILE"
else
  echo "❌ env.sh not found"
  exit 1
fi

# =========================
# 📦 Parse arguments
# =========================
PROJECT_NAME="$1"
shift

TYPE="django"

while [[ "$#" -gt 0 ]]; do
  case $1 in
    --type)
      TYPE="$2"
      shift 2
      ;;
    *)
      shift
      ;;
  esac
done

# =========================
# ❌ Validate input
# =========================
if [ -z "$PROJECT_NAME" ]; then
  echo "❌ Usage: newproj <project_name> [--type <type>]"
  exit 1
fi

[ -z "$ADE_PROJECTS" ] && echo "❌ ADE_PROJECTS not set" && exit 1

PROJECT_PATH="$ADE_PROJECTS/$PROJECT_NAME"

echo "🚀 Creating project: $PROJECT_NAME"
echo "🧠 Type: $TYPE"

# =========================
# 📁 Create directory safely
# =========================
if [ -d "$PROJECT_PATH" ]; then
  echo "⚠️ Project already exists: $PROJECT_PATH"
  exit 1
fi

mkdir -p "$PROJECT_PATH"
cd "$PROJECT_PATH" || exit 1

# --- Safety check ---
if [[ "$(pwd)" == "$HOME" ]]; then
  echo "❌ Safety stop: running in HOME directory!"
  exit 1
fi

# =========================
# 🐍 Setup virtualenv
# =========================
python3 -m venv .venv
source .venv/bin/activate

pip install --upgrade pip

# =========================
# 📦 Framework switch
# =========================
case "$TYPE" in

  django)
    echo "📦 Setting up Django project..."

    pip install django djangorestframework pytest pytest-django

    django-admin startproject config .

    python manage.py startapp core

    mkdir -p tests
    touch tests/__init__.py

    rm -rf core/tests 2>/dev/null
    rm -f core/tests.py 2>/dev/null
    ;;

  *)
    echo "❌ Unknown project type: $TYPE"
    exit 1
    ;;

esac

# =========================
# 🧠 COPY GLOBAL RULES (CRITICAL FIX)
# =========================
if [ -f "$ADE_BASE/ai_dev_env/memory/global_rules.md" ]; then
  cp "$ADE_BASE/ai_dev_env/memory/global_rules.md" .ai-rules.md
fi

# =========================
# 🧠 AI CONTEXT
# =========================
cat <<EOF > .ai-context.md
# Project Context

## Type
$TYPE

## Goal
Build a clean, production-ready backend.

## Rules
- Keep code minimal and readable
- Follow best practices
- Do NOT create dummy models
- Do NOT generate placeholder code
- Always write meaningful tests
EOF

# =========================
# 📄 README FOR AI
# =========================
cat <<EOF > README_AI.md
# AI Instructions

- Work only inside project
- Modify only relevant files
- Do NOT rewrite entire project
- Do NOT create fake implementations
- Always write real test cases
EOF

# =========================
# 🧪 PYTEST CONFIG
# =========================
cat <<EOF > pytest.ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings
python_files = tests.py test_*.py *_tests.py
EOF

# =========================
# 🔧 GIT INIT
# =========================
git init

cat <<EOF > .gitignore
.venv
__pycache__
*.pyc
db.sqlite3
EOF

# =========================
# 📦 FREEZE DEPS
# =========================
pip freeze > requirements.txt

# =========================
# ✅ DONE
# =========================
echo ""
echo "✅ Project $PROJECT_NAME ready!"
echo "📂 Location: $PROJECT_PATH"
echo "👉 Run: runai $PROJECT_NAME"
