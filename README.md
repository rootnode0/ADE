# 🚀 ADE (AI Dev Environment)

A **controlled, test-driven AI development system** for building reliable applications with local LLMs.

---

# ⚡ What Makes ADE Different?

| Tool              | Behavior           |
| ----------------- | ------------------ |
| Copilot / ChatGPT | Suggest code       |
| ADE               | Build → Test → Fix |

ADE ensures:

- deterministic changes
- scoped edits only
- automated test validation
- safe iterative improvements

---

# 🧠 Stack

- Aider → code editing engine
- Ollama → local LLM runtime
- Bash → orchestration

---

# 🧪 Quick Example

```bash
newproj demo_api --type django
runai demo_api "create Item API"
```

Result:

- API generated
- tests created
- tests passing ✅

---

# 📦 Requirements

- Python 3.10+
- Git
- Ollama
- Aider

Install:

```bash
pip install aider-chat
```

Install Ollama:

👉 https://ollama.com

---

# 🧠 Model Setup

```bash
ollama pull deepseek-coder:6.7b
```

---

# 🛠 Setup

## Linux / macOS

```bash
git clone https://github.com/albin732/ADE.git
cd ADE
./setup.sh
```

## Windows

```powershell
git clone https://github.com/albin732/ADE.git
cd ADE
.\setup.ps1
```

👉 Recommended: use WSL

---

# 🚀 Usage

## Create Project

```bash
newproj my_api --type django
```

---

## Run AI

```bash
runai my_api
```

---

## Run Task

```bash
runai my_api "create Order API in orders app"
```

---

## Interactive Mode

```bash
runai my_api chat
```

---

# 🧪 Run Tests

```bash
cd projects/my_api
source .venv/bin/activate
pytest -v
```

---

# 🧠 Execution Flow

```
runai → aider → code → pytest → fix loop
```

---

# 🔐 Behavior Control

Configured via:

```
ai-dev-env/config/env.sh
```

---

# 📁 Project Structure

```
ADE/
├── ai-dev-env/
├── projects/        # generated apps (ignored)
├── setup.sh
├── setup.ps1
```

---

# ⚠️ Important Notes

- ADE uses local LLMs → output depends on model quality
- Always use scoped prompts
- Avoid large multi-step instructions

---

# 🛠 Troubleshooting

### Ollama not running

```bash
ollama serve
```

---

### Commands not working

```bash
source ~/.bashrc
```

---

### Repeated failures

```bash
runai my_api chat
```

---

# 📚 Internal Docs

```
ai-dev-env/README.md
```

---

# 🔮 Roadmap

- precision mode
- multi-framework support
- multi-agent system
- routing optimization

---

# 💡 Philosophy

> ADE is not AI coding.
> It is **controlled AI-assisted development** focused on reliability.
