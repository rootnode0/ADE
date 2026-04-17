#!/bin/bash

# =========================
# 🧠 ENV LOAD
# =========================
if [ -z "$ADE_BASE" ]; then
  echo "❌ ADE_BASE not set"
  echo "👉 Run: source ~/.bashrc"
  exit 1
fi

source "$ADE_BASE/ai_dev_env/config/env.sh"

# =========================
# ✅ VALIDATION
# =========================
if [ -z "$ADE_BASE" ]; then
  echo "❌ ADE_BASE missing in env"
  exit 1
fi

CONFIG_FILE="$ADE_BASE/ai_dev_env/router/litellm_config.yaml"

if [ ! -f "$CONFIG_FILE" ]; then
  echo "❌ LiteLLM config not found: $CONFIG_FILE"
  exit 1
fi

# =========================
# 🚀 START ROUTER
# =========================
echo "🚀 Starting LiteLLM Router..."
echo "📄 Config: $CONFIG_FILE"

litellm --config "$CONFIG_FILE"
