# 🚀 ADE (Autonomous Development Engine)

<div align="center">
  <p><strong>Build applications with AI — securely, autonomously, and with production-level discipline.</strong></p>
  <p><i>Generate → Test → Fix → Stabilize</i></p>
</div>

---

## 1. Project Overview

ADE is an intelligent dev-environment orchestration tool. It manages the entire software development lifecycle by leveraging AI (via Aider and Ollama) to:

- **Write** code automatically based on specific tasks.
- **Run** comprehensive test suites against the generated code.
- **Fix** bugs and errors autonomously.
- **Stabilize** projects to ensure production-readiness.

Think of ADE as a senior engineer who not only writes code but rigorously tests, refactors, and structures it according to best practices without breaking things.

---

## 2. Architecture Explanation

ADE operates through a defined feedback loop to guarantee high code quality:

### ⚙️ The Orchestrator (`ade_agent.py`)
1. **Planning**: Parses tasks, creates action plans, and determines the target files and required logic.
2. **Coding**: Invokes the Coder Agent (`ai_dev_env/agents/coder.py`) using models to implement features.
3. **Validation**: The Validator (`ai_dev_env/agents/validator.py`) runs syntax checks, Django standard validation, and test suites (e.g., PyTest).
4. **Debugging Loop**: If validation fails, the Debugger analyzes the tracebacks, formulates a fix, and passes it back to the coder. This repeats until tests pass.

### 🧩 Automated Architecture Features
- **Intelligent App Registration**: ADE dynamically detects local Django applications and updates `INSTALLED_APPS` safely.
- **Centralized Testing structure**: Enforces a scalable `tests/<app_name>/` layout instead of scattered tests, isolating business logic checks securely.
- **Context Awareness**: Connects tightly with Retrieval-Augmented Generation (RAG) to inject only relevant files into the prompt.

---

## 3. Setup Instructions (Step-by-Step)

### Prerequisites
- Python 3.10+
- Git
- Ollama (for offline models)
- Aider

### Linux / Ubuntu Setup

1. **Install System Dependencies**
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip python3-venv git -y
   ```

2. **Start Ollama**
   Download from [ollama.com](https://ollama.com/), start the service, and pull a local model:
   ```bash
   ollama serve &
   ollama pull deepseek-coder:6.7b
   ```

3. **Install & Setup ADE**
   ```bash
   git clone git@github.com:rootnode0/ADE.git
   cd ADE
   ./setup.sh
   source ai_dev_env/config/env.sh
   ```

### Windows (WSL) Setup

*ADE works best inside a Linux environment. It is highly recommended to use WSL.*

1. Install WSL via PowerShell: `wsl --install`
2. Once un Ubuntu, run the Linux installation steps.
3. Use the WSL Terminal strictly for managing ADE commands.

---

## 4. Running the Project

Ensure Ollama is running and your environment variables are sourced.

1. **Create a New Project**
   Create a Django project managed by ADE:
   ```bash
   newproj demo_api --type django
   ```
   *This clones the necessary templates into the `projects/` directory.*

2. **Execute an AI Task**
   Provide a scoped, actionable task:
   ```bash
   runai demo_api "create Order API in orders app"
   ```

ADE will formulate a plan, write the code, register the new apps, and output a validated result.

---

## 5. Running Tests

ADE enforces a **Zero Assumptions** testing architecture. This means:
- **Self-Contained Fixtures**: Every test file using `api_client` defines its own fixture or uses a local `conftest.py`.
- **Dynamic Data**: Tests NEVER assume existing DB state. They create their own data and use dynamic IDs.
- **Automated Configuration**: ADE automatically generates a project-local `pytest.ini` with the correct `DJANGO_SETTINGS_MODULE`, so you can run tests anywhere.

### Manual Test Execution
ADE manages PyTest alongside the Django test runner.

```bash
cd projects/demo_api
./.venv/bin/python -m pytest tests/ -v
```

### Auto Test Execution by ADE
Whenever you use `runai`, ADE runs the tests inside the containerized `.venv`. 

**Stability Features:**
- **Robust Rollbacks**: If any step fails (coding, migration, or testing), ADE performs a `git reset --hard` and `git clean -fd` to restore the project to a 100% clean state.
- **Environment Awareness**: ADE dynamically injects environment variables into the execution pipeline, preventing `ImproperlyConfigured` errors.

---

## 6. Folder Structure Explanation

```text
ADE/
├── ai_dev_env/                  # Core AI Engine (ADE logic)
│   ├── agents/                  # Planners, Coders, Validators & Debuggers
│   ├── config/                  # Environment loading scripts
│   ├── hooks/                   # Execution lifecycle hooks
│   ├── scripts/                 # CLI entry points (newproj, runai)
│   └── skills/                  # Markdowns that guide LLM behaviors
├── projects/                    # User Workspaces
│   ├── demo_api/                # Example target project
│   │   ├── config/              # Django Settings (auto-managed)
│   │   ├── core/                # Business logic views, models, URLs
│   │   └── tests/               # Centralized tests layout (tests/core/...)
│   └── test_ade_app/            # Isolated test arena
├── ade_agent.py                 # ADE Pipeline script calling the agents
└── setup.sh                     # Bootstrapper
```

---

## 7. ADE Usage Instructions

**DO:**
- Provide direct, self-contained inputs: *"Fix failing permission tests in the core app."* or *"Create a model for Invoices."*
- Trust the auto-registration: ADE handles `INSTALLED_APPS` and test setups inside its validation phase.

**DON'T:**
- Use sweeping requests: *"Rewrite the entire system"* — ADE succeeds by iterating through atomic changes.
- Put UI and code changes in the same pipeline request if they affect completely different subsystems.

---

## 8. Future Scalability Notes

- **Multi-Framework Integrations**: Right now, ADE validates Django rigorously. Fast-tracking integration for Next.js or generic pure-Python validation will unlock cross-stack developments.
- **Parallel Testing**: Moving from sequential PyTest runs to `pytest-xdist` inside the validator container to reduce iteration latency during large code generation tasks.
- **Views Refactoring Strategy**: The current structure enforces a `/views/` subdirectory pattern for complex views, preventing monolith files. As projects grow, this guarantees long-term maintainability.
