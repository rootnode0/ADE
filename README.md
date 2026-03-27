# 🚀 ADE (AI Dev Environment)

![Status](https://img.shields.io/badge/status-active-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue)
![Platform](https://img.shields.io/badge/platform-linux%20%7C%20windows-lightgrey)

A **controlled, test-driven AI development environment** for safe, scalable, and reliable code generation.

Built with:

- 🧠 Aider (AI code editing engine)
- 🤖 Ollama (local LLM runtime)
- ⚙️ Custom orchestration scripts

---

# ⚡ Why ADE?

Unlike typical AI coding tools:

| Tool              | Behavior               |
| ----------------- | ---------------------- |
| Copilot / ChatGPT | Suggest code           |
| ADE               | Builds + tests + fixes |

ADE focuses on:

- ✔ Deterministic behavior
- ✔ Minimal, scoped changes
- ✔ Test-driven corrections
- ✔ Safe automation loop

---

# 🧪 Quick Demo

```bash
newproj demo_api
runai demo_api "create Item API"
```

Result:

- API created
- Tests generated
- Tests passing ✅

---

# 📦 Requirements

## 🧠 Core

- Python 3.10+
- Git
- Aider
- Ollama

Install:

```bash
pip install aider-chat
```

Install Ollama:
👉 https://ollama.com

---

## 🧠 Model Setup

ADE is **model-agnostic**.

```bash
ollama pull <model_name>
```

Example:

```bash
ollama pull qwen2.5-coder:7b
```

---

# 🛠 Setup

## 🐧 Linux / macOS

```bash
git clone https://github.com/albin732/ADE.git
cd ADE
./setup.sh
```

---

## 🪟 Windows (PowerShell)

```powershell
git clone https://github.com/albin732/ADE.git
cd ADE
.\setup.ps1
```

> 💡 Recommended: Use **WSL** for full compatibility.

---

# 🚀 Usage

## 📦 Create Project

```bash
newproj my_api
newproj my_api --type django
```

> ⚠️ Current support: **Django (DRF-based backend)**
> Multi-framework support is planned.

---

## 🤖 Run AI

```bash
runai my_api
```

---

## 🎯 Run Task

```bash
runai my_api "create Order API in orders app"
```

---

## 💬 Interactive Mode

```bash
runai my_api chat
```

---

## 🧠 Advanced Usage (Optional)

```bash
runai my_api "fix failing tests in core app"
runai my_api "optimize serializers without changing API response"
runai my_api "add authentication in users app"
```

### Tips

- Mention target app (`core`, `orders`, etc.)
- Use clear intent: _create_, _fix_, _optimize_
- Avoid vague instructions like “improve everything”

---

## 🧪 Run Tests

```bash
cd projects/my_api
source .venv/bin/activate
pytest -v
```

---

# 🧠 Execution Flow

```
runai
  ↓
Aider
  ↓
Code change
  ↓
pytest
  ↓
Fix loop
  ↓
Stable output
```

---

# 🔐 Behavior Control

Configured in:

```
ai-dev-env/config/env.sh
```

Example:

```bash
ADE_ALLOW_TEST_GEN=true
ADE_ALLOW_FILE_CREATE=true
ADE_ALLOW_BUG_FIX=true
```

---

# 📁 Project Structure

```
ADE/
├── ai-dev-env/
├── projects/        # generated apps (ignored)
├── setup.sh
├── setup.ps1
├── CONTRIBUTING.md
└── README.md
```

---

# 🛠 Troubleshooting

### ❌ Commands not working

```bash
source ~/.bashrc
```

---

### ❌ Ollama not running

```bash
ollama serve
```

---

### ❌ Tests failing repeatedly

```bash
runai my_api chat
```

---

### ❌ Windows issues

Use WSL or Git Bash

---

# 📚 Documentation

Internal docs:

```
ai-dev-env/README.md
```

---

# 🤝 Contributing

See:

```
CONTRIBUTING.md
```

---

# 🔮 Roadmap

- Precision mode (targeted fixes)
- Multi-framework support (FastAPI, Node)
- Task templates
- Multi-agent system
- LiteLLM routing

---

# 🚀 Status

```
LEVEL 10: Plug-and-play AI Dev System
```

---

# 💡 Philosophy

> ADE is not just AI coding.
> It is **controlled AI-assisted development** — focused on reliability, not randomness.
