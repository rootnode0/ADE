# ⚙️ ADE Internal Documentation

> Technical overview of ADE internals.
> See root README for usage.

---

# 🧠 System Overview

ADE is a script-driven orchestration system combining:

- Aider (editing engine)
- Ollama (LLM backend)
- Bash scripts (control layer)

---

# 🧱 Components

```
ai-dev-env/
├── config/
├── memory/
├── scripts/
└── router/
```

---

# 📁 Projects Directory

## Location

```
ADE/projects/
```

---

## Purpose

Stores all **generated and managed applications**.

Each project is:

```
✔ isolated
✔ self-contained
✔ AI-managed
```

---

## Structure Example

```
projects/
└── my_api/
    ├── config/
    ├── core/
    ├── orders/
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

- No cross-project interaction
- Independent lifecycle per project

---

## Git Behavior

```
projects/ is ignored
```

Reason:

- generated code
- virtual environments
- local state

---

## Safety Rules

```
✔ project must exist before runai
✔ no modification outside project
✔ no implicit project creation
```

---

# ⚙️ Execution Flow

```
runai → run_aider.sh → aider → code → pytest → fix loop
```

---

# 📂 File Selection

- global_rules.md
- project source files
- detected apps
- root configs
- tests

---

# 🔁 Smart Loop

```
run → test → fail → fix → repeat (max 3)
```

---

# 🔐 Permissions

Controlled via:

```
env.sh
```

Example:

```
ADE_ALLOW_TEST_GEN
ADE_ALLOW_FILE_CREATE
ADE_ALLOW_BUG_FIX
```

---

# 🧠 Rules Engine

File:

```
memory/global_rules.md
```

Prevents:

- duplicate AppConfig
- duplicate models
- broken URLs

---

# 📦 Project Creation

Handled by:

```
scripts/create_project.sh
```

Supports:

```
newproj my_api --type django
```

---

# 🔀 Router (Optional)

```
scripts/start_router.sh
```

Used for multi-model routing.

---

# ⚠️ Constraints

- no global rewrites
- no hardcoded paths
- no cross-app edits

---

# 🔮 Future

- precision mode
- AST validation
- multi-agent system

---

# 🧠 Philosophy

LLM output is **constrained, validated, and test-driven** — not blindly trusted.
