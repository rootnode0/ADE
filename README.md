# 🚀 ADE (AI Dev Environment)

Build apps with AI — **but safely**

> Generate → Test → Fix → Stabilize

---

## ⚡ What is ADE?

ADE is a tool where AI:

- writes code
- runs tests
- fixes errors automatically

👉 Like a **junior developer that keeps fixing its own code**

---

# 🧠 Before You Start

ADE needs:

- Python (3.10+)
- Git
- Ollama (for AI)
- Aider (for code editing)

---

# 🐧 Ubuntu / Linux Setup

## 1. Install system dependencies

```bash
sudo apt update
sudo apt install python3 python3-pip git -y
```

---

## 2. Install Aider

```bash
pip install aider-chat
```

---

## 3. Install Ollama

Download from: https://ollama.com

Then start it:

```bash
ollama serve
```

---

## 4. Download a model

```bash
ollama pull deepseek-coder:6.7b
```

---

## 5. Clone ADE

```bash
git clone git@github.com:rootnode0/ADE.git
cd ADE
```

---

## 6. Run setup

```bash
./setup.sh
```

---

## 7. Load environment

```bash
source ai-dev-env/config/env.sh
```

---

# 🪟 Windows Setup (Recommended: WSL)

👉 ADE works best inside Linux environment

---

## 1. Install WSL

Open PowerShell:

```powershell
wsl --install
```

Restart your PC.

---

## 2. Open Ubuntu (WSL)

Then run:

```bash
sudo apt update
sudo apt install python3 python3-pip git -y
```

---

## 3. Install Aider

```bash
pip install aider-chat
```

---

## 4. Install Ollama (Windows)

Download: https://ollama.com/download

Then in WSL:

```bash
ollama serve
```

---

## 5. Setup ADE

```bash
git clone git@github.com:rootnode0/ADE.git
cd ADE
./setup.sh
source ai-dev-env/config/env.sh
```

---

## ⚠️ Important for Windows

- Always use **WSL terminal**
- Do NOT use PowerShell for ADE commands
- Keep projects inside WSL filesystem

---

# 🧪 First Run (IMPORTANT)

Before running ADE, make sure:

```bash
ollama serve
```

and:

```bash
source ai-dev-env/config/env.sh
```

---

## Now try:

```bash
newproj demo_api --type django
runai demo_api "create Item API"
```

---

## ✅ Expected result

- Django API created
- Tests generated
- Errors fixed automatically

---

## ❗ If it fails

Check:

- Ollama is running
- Model is installed
- env.sh is loaded

---

# 🚀 Basic Usage

### Create project

```bash
newproj my_api --type django
```

---

### Run AI

```bash
runai my_api
```

---

### Give task

```bash
runai my_api "create Order API in orders app"
```

---

# 🧠 How it works

```text
runai → AI edits code → tests run → AI fixes → repeat
```

---

# ⚠️ Tips (IMPORTANT)

✔ Good:

- “create Order API in orders app”
- “fix failing tests in core app”

❌ Bad:

- “build full system”
- “improve everything”

👉 Keep tasks small

---

# 📁 Project Structure

```
ADE/
├── ai-dev-env/
├── projects/
```

---

# 💡 Summary

ADE is:

> AI that writes code
> and keeps fixing it until tests pass

---

# 👨‍💻 Author

albingeo

---
