# GLOBAL AI RULES (STRICT)

## General Behavior

- Make minimal necessary changes
- Never rewrite entire project unless explicitly asked
- Prefer incremental edits

## Scope Control

- **Strict Boundaries**: You are ONLY responsible for code content within the target app's directory (e.g., `<app>/models.py`).
- **Forbidden Files**: NEVER attempt to modify `config/settings.py`, `config/urls.py`, or any files in the project root. ADE handles these via system logic.
- **No App Creation**: Do NOT attempt to create apps or folders. ADE handles `manage.py startapp` before you are called.
- **No Path Assumptions**: Do NOT assume project-level folder names like `config/`. Only work with relative paths within your assigned app.

## App Creation Rules

- Each Django app must have:
  - unique AppConfig class
  - correct name matching folder
- Do NOT copy code from other apps
- Always complete feature (model, serializer, viewset, urls)

## URL Rules

- Use DRF router directly
- Avoid nested duplicate paths
- Ensure no duplicate routes

## Test Rules

- Create tests ONLY when explicitly asked
- Place all tests inside /tests folder
- Do NOT modify existing tests unless fixing failure
- **Zero Assumptions**: NEVER use hardcoded IDs (e.g., `id=1`). Always create required data within the test or fixture.
- **Self-Sufficiency**: Every test file using `api_client` must include or import its fixture definition.

## Permission Rules

- If change affects multiple files → ask or limit scope
- Prefer safest change
- If unsure → suggest instead of modifying

## Stability Rules

- Do NOT break working code
- Do NOT modify unrelated files
- Preserve project structure

## Fix Mode Rules

- Fix only failing issue
- Do not regenerate entire project
- Prefer smallest fix

## Validation Rules

- Avoid duplicate AppConfig
- Avoid duplicate model names
- Avoid duplicate URL patterns
