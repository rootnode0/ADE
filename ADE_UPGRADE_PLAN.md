# ADE (Autonomous Development Engine) - System Upgrade Plan

## 1. Analysis of Current ADE Weaknesses

After reviewing the core `ai_dev_env` modules (`planner.py`, `coder.py`, `validator.py`, and `ade_agent.py`), several architectural weaknesses are apparent:

1.  **Planner Stability & Rigidity:** 
    *   The `planner.py` relies solely on regex/string scraping for JSON extraction instead of utilizing Ollama's native JSON mode (`"format": "json"`).
    *   The data structure is rigid. The fallback heavily hardcodes `app_name="core"`, missing app-aware delegation.
    *   Missing detailed procedural arrays (`actions`, `steps`) in the schema.
2.  **Lack of App-Aware Execution:** 
    *   The orchestrator ignores whether the target app actually exists before the coder runs. If the app is missing, `coder.py` blindly creates files in directories that aren't recognized by Django, relying completely on a simplistic string-replace heuristic in `validator.py` (`patch_django_settings`). 
3.  **Incomplete Django Lifecycle Automation:**
    *   `validator.py` runs `manage.py check` and `pytest`, but **completely lacks** migrations (`makemigrations`/`migrate`), which is critical for model changes. 
    *   There is no mechanism to auto-wire `urls.py` for new apps or ViewSets.
4.  **No Test Generation Workflow:**
    *   Test validation expects tests to exist (`pytest` runs), but there's no step dedicated to TDD writing or generating tests if they don't exist.
5.  **Lack of Observability:**
    *   Logging uses simple Python `print()` statements.
    *   Token usage metric tracking is ignored (Ollama returns `eval_count` and `prompt_eval_count` which aren't recorded).
    *   There's no structured log history to analyze Agent success/failure rates over time.
6.  **Fragmented & Embedded Prompting:**
    *   Critical system prompts are hardcoded inside `planner.py` and `coder.py`. This fragmentation makes systemic tuning of the agent's behavior extremely difficult.

---

## 2. Improved Architecture Design

To achieve deep system-improvement, ADE must transition from a simple string-parsing orchestrator into an event-driven, app-aware system:

### Enhanced Modules
*   `AgentOrchestrator` (`ade_agent.py`): Re-engineered to explicitly route commands and handle a context pipeline using dedicated modules.
*   `ProjectIntrospector`: New component that scans the active Django project to load all installed apps, existing URLs, and registered models into context.
*   `PromptLibrary`: Centralized loader that injects `memory/prompts/*.md` templates dynamically.
*   `DjangoAutomator`: Dedicated to scaffolding (`startapp`), URL wiring, and executing `makemigrations` and `migrate`.
*   `ObservabilityEngine`: Structured JSON logger capturing time, tokens, phase progression, and retry telemetry.

### Unified Command Syntax
The orchestrator will interpret standard CLI intent before planning:
*   `create model [model_name] in [app_name]`
*   `generate tests for [app_name]`
*   `create api for [model_name] in [app_name]`

---

## 3. Planner Improvements

**Code & Execution Fixes (`ai_dev_env/agents/planner.py`):**
1.  **Enable JSON Mode:** Update the `requests.post` call payload to explicitly request JSON format from the LLM, vastly reducing parsing errors:
    ```python
    payload = {
        "model": config.planner_model,
        "format": "json", # Forces deterministic JSON output
        "prompt": ...,
    }
    ```
2.  **Schema Expansion:** Upgrade `Plan` to map exactly to the new requirements:
    ```json
    {
      "task": "original task string",
      "task_type": "model-gen",
      "skill": "django-model-gen",
      "app_name": "inventory",
      "class_name": "Product",
      "target_files": ["inventory/models.py", "inventory/admin.py"],
      "context_files": ["config/settings.py"],
      "actions": ["Create Product model", "Register to admin"],
      "steps": ["Define fields", "Add meta class"],
      "reasoning": "Standard Django model workflow"
    }
    ```

---

## 4. App-Aware Execution & Django Automation Fixes

**Pre-Flight App Validation:**
Before generating code, ADE should examine the `plan.app_name`. If `os.path.exists(f"{project_path}/{app_name}")` is `False`, the `DjangoAutomator` triggers a safe auto-creation:
```bash
python manage.py startapp {app_name}
```
*   The automator then automatically updates `settings.py` (replacing the current rudimentary regex implementation in `validator.py`).

**Post-Code Django Lifecycle (Run inside `val_instance.validate`):**
Add deterministic lifecycle evaluations based on modified files:
1.  **Models:** If `models.py` is in `modified_files`:
    *   Command: `python manage.py makemigrations {app}`
    *   Command: `python manage.py migrate`
2.  **URLs:** If `views.py` is created/modified, auto-inject `path('{app}/', include('{app}.urls'))` into `project/config/urls.py` via an AST-based modifier, mitigating regex breakages.

---

## 5. Test Generation Workflow

**Structure Standards:**
Tests will strictly adhere to the external test directory pattern (as opposed to intra-app `tests.py`):
```text
projects/<project>/tests/<app>/
    __init__.py
    test_models.py
    test_views.py
    test_urls.py
```

**New Agent Pipeline - `tests-gen`:**
When the orchestrator encounters a "generate tests" command or task type:
1.  **Planner:** Generates target files (`tests/inventory/test_models.py`).
2.  **Indexer:** Pulls the implementation context (`inventory/models.py`).
3.  **Coder:** Executes against the **NEW** `test_generation.md` skill prompt.
4.  **Validator:** Runs exactly `python -m pytest tests/{app}/ --tb=short`.

---

## 6. Execution Observability

Provide timing and resource logging by intercepting standard metrics. 

**Model Resource Hook:**
Extract `eval_count` (generation tokens) and `prompt_eval_count` (context tokens) from the Ollama response inside `planner.py` and `coder.py`.

Create an `ObservabilityEngine` that writes to `.ade_metadata/runs.jsonl`, and updates the CLI stdout to be more informative:
```text
===================================================
ADE EXECUTION RUN 
===================================================
[PLAN] deepseek-r1    → 1.3s  (Tokens: 450 in / 120 out)
[PREP] django hooks   → 0.8s  (Ran startapp 'orders')
[CODE] qwen2.5-coder  → 4.5s  (Tokens: 1200 in / 450 out)
[MIGRATE] makemigrations → 1.2s
[TEST] pytest         → 2.1s
===================================================
✅ SUCCESS (Total: 9.9s)
```

---

## 7. Prompt Organization Restructure

Move all hardcoded Python string prompts into centralized Markdown files for easier iteration:

*   **`ai_dev_env/memory/prompts/planner_prompt.md`**: Dedicated instructions specifically mapping task language to JSON variables and actions/steps arrays.
*   **`ai_dev_env/memory/prompts/test_generation.md`**: Specialized system rules focusing wholly on `pytest`, fixture generation, DB mocking, and assertions.
*   **`ai_dev_env/memory/prompts/django_rules.md`**: Rules prohibiting recursive imports, enforcing `related_name` conventions, demanding `admin.py` registrations on model creation, and dictating `urls.py` structures.

The `ade_agent.py` will read these files and inject them into `system_prompt` variables during initialization.

---

## 8. Self-Healing Execution Revisions

*   **Syntax Self-Recovery:** If `validator.py` catches syntax errors via AST (`ast.parse`), ADE should capture the `se.msg` and `se.lineno` and trigger a targeted `Debugger` attempt, passing *only* the specific file back to the `Coder` for localized fixing, rather than regenerating everything.
*   **Missing Imports:** Hook into Django's `check` command. If it yields an `ImportError` or `ModuleNotFoundError`, pass the stack trace to the debugging context and append a `python -m pip install` step to the tool chain if missing dependencies are identified.
*   **Rollback Safety:** Rollbacks (current `git checkout`) must also support reverting database changes (`migrate {app} {previous_migration_name}`) to leave the environment clean upon failure.
