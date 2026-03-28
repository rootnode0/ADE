# ⚙️ ADE Internal Documentation

> Technical reference for ADE internals
> See root README for usage and onboarding

---

# 🧠 System Overview

ADE is a **controlled AI orchestration system** combining:

- Aider → structured code editing engine
- Ollama → local LLM backend
- Bash scripts → execution & control layer

---

# 🧱 Core Components

```
ai-dev-env/
├── config/      # environment + permissions
├── memory/      # rules + constraints
├── scripts/     # execution logic
└── router/      # optional model routing
```

---

# 📁 Projects Directory

## Location

```
ADE/projects/
```

## Purpose

Stores all **AI-managed applications**

Each project is:

- isolated
- self-contained
- independently executable

---

## Example Structure

```
projects/
└── my_api/
    ├── config/
    ├── core/
    ├── tests/
    ├── manage.py
    ├── requirements.txt
    └── .venv/
```

---

## Behavior

```
runai → operates ONLY inside selected project
```

- no cross-project access
- no global mutations

---

## ⚠️ Git Behavior

```
projects/ is ignored by default
```

Reason:

- generated code
- local environments
- non-deterministic outputs

👉 If treating a project as production code, manage Git inside that project separately.

---

# ⚙️ Execution Flow

```
runai
  ↓
run_aider.sh
  ↓
aider (LLM edit)
  ↓
code changes
  ↓
pytest
  ↓
fix loop (max 3)
```

---

# 📂 Context Selection

Aider receives:

- global_rules.md
- project source files
- detected Django apps
- configs + tests

---

# 🔁 Smart Loop

```
run → test → fail → fix → repeat
```

Constraints:

- max 3 iterations
- scoped edits only

---

# 🔐 Permissions System

Controlled via:

```
config/env.sh
```

Examples:

```
ADE_ALLOW_TEST_GEN
ADE_ALLOW_FILE_CREATE
ADE_ALLOW_BUG_FIX
```

---

# 🧠 Rules Engine

```
memory/global_rules.md
```

Prevents:

- duplicate AppConfig
- invalid Django structure
- unsafe modifications

---

# 📦 Project Creation

Handled by:

```
scripts/create_project.sh
```

Example:

```
newproj my_api --type django
```

---

# 🔀 Router (Optional)

```
scripts/start_router.sh
```

Used for:

- multi-model routing
- cost/performance optimization

---

# ⚠️ System Constraints

- no global rewrites
- no hardcoded paths
- no cross-app edits
- no uncontrolled file creation

---

# 🔮 Roadmap

- precision edit mode
- AST-based validation
- multi-agent orchestration

---

# 🧠 Philosophy

LLM output is:

> constrained → validated → tested

Not blindly executed.
