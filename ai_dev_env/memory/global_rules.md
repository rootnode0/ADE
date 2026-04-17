# GLOBAL AI RULES (STRICT)

## General Behavior

- Make minimal necessary changes
- Never rewrite entire project unless explicitly asked
- Prefer incremental edits

## Scope Control

- If task targets a specific app → ONLY modify that app
- Do NOT modify other apps unless required

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
