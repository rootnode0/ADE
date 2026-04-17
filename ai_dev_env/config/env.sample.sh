# =========================================================
# ADE ENV SAMPLE CONFIGURATION
# =========================================================
# Copy this file to:
#   env.sh
#
# Then update values where required.
# =========================================================


# =========================================================
# 🤖 MODEL CONFIGURATION
# =========================================================

# --- Ollama base ---
export OLLAMA_API_BASE="http://localhost:11434"

# Aider uses same base
export AIDER_API_BASE="$OLLAMA_API_BASE"

# Dummy key for Ollama (required by aider)
export AIDER_API_KEY="ollama=dummy"


# =========================================================
# 🧠 LOCAL MODEL CHAIN (EDIT MODELS ONLY)
# =========================================================
# IMPORTANT:
# - ONLY use coding models here
# - These models MUST support strict diff editing
#
# Recommended order:
# 1. Best coder
# 2. Strong fallback
# 3. Stable fallback
# 4. Fast fallback

export ADE_MODELS_LOCAL="\
ollama/qwen2.5-coder:7b,\
ollama/deepseek-coder:6.7b,\
ollama/codellama:7b,\
ollama/qwen2.5-coder:1.5b"


# =========================================================
# ⚡ FAST MODEL (OPTIONAL)
# =========================================================
# Used for quick operations (not main editing)

export ADE_MODEL_FAST="ollama/qwen2.5-coder:1.5b"


# =========================================================
# 🧠 REASONING MODELS (FUTURE USE)
# =========================================================
# These models are NOT used for code editing
# Will be used for:
# - file targeting
# - planning
# - debugging logic

export ADE_MODELS_REASON="\
ollama/qwen3:8b"


# =========================================================
# 🌐 CLOUD MODELS (OPTIONAL)
# =========================================================
# ⚠️ Requires API key
# ⚠️ Use carefully (token limits / cost)

# Replace with your OpenRouter key
export OPENROUTER_API_KEY="your-openrouter-api-key"

export ADE_MODELS_CLOUD="\
openrouter/qwen/qwen-2.5-coder-32b-instruct,\
openrouter/deepseek/deepseek-chat"


# =========================================================
# ⚙️ AIDER SETTINGS
# =========================================================

# Token budget for repo mapping
export AIDER_MAP_TOKENS=1024

# Required for ADE
export AIDER_EDIT_FORMAT=diff

# Prevent unwanted commits
export AIDER_AUTO_COMMITS=false


# =========================================================
# 🧪 PYTHON / RUNTIME
# =========================================================

# Preferred Python version
export ADE_PYTHON_VERSION="3.12"

# Runtime modes:
# auto     → use project .venv
# system   → use system python
# managed  → (future use)

export ADE_RUNTIME_MODE="auto"


# =========================================================
# 📂 ADE PATHS
# =========================================================

# Root ADE directory
export ADE_BASE="$HOME/hub/00_own/ADE"

# Projects directory
export ADE_PROJECTS="$ADE_BASE/projects"

# Scripts directory
export ADE_SCRIPTS="$ADE_BASE/ai_dev_env/scripts"


# =========================================================
# 🔐 PERMISSIONS / BEHAVIOR
# =========================================================

export ADE_ALLOW_TEST_GEN=true
export ADE_ALLOW_BUG_FIX=true
export ADE_ALLOW_LINT=true
export ADE_ALLOW_FILE_CREATE=true


# =========================================================
# 🧪 DEBUG (OPTIONAL)
# =========================================================
# Uncomment for debugging
# export ADE_DEBUG=true


# =========================================================
# 🚨 IMPORTANT NOTES
# =========================================================

# ❌ DO NOT put reasoning models (like qwen3) inside ADE_MODELS_LOCAL
#    → causes "did not conform" errors

# ❌ DO NOT hardcode model in scripts
#    → always use env variables

# ❌ DO NOT commit real API keys

# ✅ Always run:
#    source env.sh
# after updating configuration
