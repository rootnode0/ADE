import json
import requests
import re
import os
import sys
from typing import Literal, List
from pydantic import BaseModel, ValidationError
from ai_dev_env.config.manager import config

# 1. Output schema validated via Pydantic
class Plan(BaseModel):
    task: str = ""                # original task string, threaded from CLI
    task_type: Literal["model-gen", "api-gen", "bug-fix", "tdd-write", "refactor", "unknown"]
    skill: str                    # filename of the matching skill (e.g. "django-model-gen")
    target_files: List[str]       # relative paths within project
    context_files: List[str]      # additional read-only context files
    class_name: str               # PascalCase entity name extracted from task
    app_name: str                 # Django app name (default: "core")
    reasoning: str                # brief explanation of the plan

def extract_json(text: str) -> str:
    """Robustly extracts a JSON object from a string, handling thinking tags and markdown."""
    if not text or not isinstance(text, str):
        return ""

    # Remove <think> blocks
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

    # Strip markdown code blocks (handles ```json and ```)
    text = re.sub(r'\s*```', '', text).strip()

    # 3. Targeted extraction: Find the outermost curly braces
    first_brace = text.find('{')
    last_brace = text.rfind('}')

    if first_brace != -1 and last_brace != -1:
        return text[first_brace:last_brace + 1]

    # 4. Final attempt: Just return the stripped string
    return text.strip()

def plan(project_path: str, task: str) -> Plan:
    """
    Calls the LLM to generate a structured Plan.
    Implements a three-tier recovery:
    1. Validation
    2. Manual Repair
    3. Hardcoded Fallback
    """
    url = f"{config.ollama_base_url}/api/generate"

    # Sanitize task input
    task_clean = task.replace('"', "'")

    # Strict system prompt to minimize noise from smaller models
    system_prompt = f"""
    You are the ADE Planner. Output a JSON object ONLY.
    NO conversational text. NO markdown.

    REQUIRED SCHEMA:
    {{
      "task_type": "model-gen",
      "skill": "django-model-gen",
      "target_files": ["core/models.py"],
      "context_files": [],
      "class_name": "EntityName",
      "app_name": "core",
      "reasoning": "Brief description"
    }}

    Allowed task_types: "model-gen", "api-gen", "bug-fix", "tdd-write", "refactor", "unknown"
    """

    payload = {
        "model": config.planner_model,
        "prompt": f"{system_prompt}\n\nUSER TASK: {task_clean}\nJSON OUTPUT:",
        "stream": False,
        "options": {{
                "temperature": 0.0,
                "num_ctx": 4096,
                "stop": ["TASK:", "User:", "```"]
            }}
        }

    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        raw_text = response.json().get('response', '')

        if not raw_text or not raw_text.strip():
            raise ValueError("Ollama returned an empty response.")

        clean_json = extract_json(raw_text)

        try:
            # Step 1: Attempt direct validation
            return Plan.model_validate_json(clean_json)
        except (ValidationError, json.JSONDecodeError):
            # Step 2: Attempt manual repair of common LLM hallucinations
            try:
                repaired = json.loads(clean_json)

                # Fix task_type mapping
                tt = str(repaired.get("task_type", "unknown")).lower()
                if "model" in tt: repaired["task_type"] = "model-gen"
                elif "api" in tt: repaired["task_type"] = "api-gen"
                elif "bug" in tt: repaired["task_type"] = "bug-fix"
                else: repaired["task_type"] = "unknown"

                # Ensure basic fields exist to satisfy Pydantic
                repaired.setdefault("skill", "django-model-gen")
                repaired.setdefault("app_name", "core")
                repaired.setdefault("target_files", ["core/models.py"])
                repaired.setdefault("context_files", [])
                repaired.setdefault("class_name", "GeneratedClass")
                repaired.setdefault("reasoning", "Recovered from malformed JSON.")

                return Plan.model_validate(repaired)
            except Exception:
                raise ValueError(f"JSON Parsing failed. Text snippet: {{raw_text[:60]}}")

    except Exception as e:
        # Step 3: Hardcoded Fallback to keep the orchestrator moving
        print(f"      DEBUG: Planner Error ({{e}}) -> Using Fallback Plan")
        return Plan(
            task_type="model-gen",
            skill="django-model-gen",
            target_files=["core/models.py"],
            context_files=[],
            class_name="Category",
            app_name="core",
            reasoning="Fallback plan generated due to LLM parsing error."
        )

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python planner.py <project_path> <task>")
        sys.exit(1)

    # Simple CLI for testing the planner in isolation
    result = plan(sys.argv[1], sys.argv[2])
    print(result.model_dump_json(indent=2))
