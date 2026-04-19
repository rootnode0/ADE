import json
import time
import os
import sys
from typing import List, Optional, Dict
from pydantic import BaseModel, ValidationError
from ai_dev_env.config.manager import config
from ai_dev_env.utils import ollama_client

class EntityField(BaseModel):
    name: str
    type: str

class Entity(BaseModel):
    name: str
    fields: List[EntityField]

class Plan(BaseModel):
    intent: str
    project_name: str = ""
    type: str = "django"
    app: str = ""
    target_file: str = ""
    test_location: str = "central"
    entities: List[Entity] = []
    relations: List[str] = []
    business_rules: List[str] = []
    actions: List[str] = []
    steps: List[str] = []
    error: Optional[str] = None
    
    # Legacy fields for backward compatibility
    entity: str = ""
    fields: List[Dict[str, str]] = []

    # Internal routing fields to maintain compatibility with legacy code
    task: str = ""

    from pydantic import field_validator, model_validator
    
    @model_validator(mode='before')
    @classmethod
    def handle_legacy_fields(cls, data: Dict) -> Dict:
        if isinstance(data, dict):
            # If entities is missing but entity/fields are present, convert to entities list
            if not data.get("entities") and data.get("entity"):
                entity_name = data.get("entity")
                legacy_fields = data.get("fields", [])
                
                normalized_fields = []
                for f in legacy_fields:
                    if isinstance(f, str):
                        normalized_fields.append({"name": f, "type": "string"})
                    elif isinstance(f, dict):
                        normalized_fields.append({"name": f.get("name", "unknown"), "type": f.get("type", "string")})
                
                data["entities"] = [{"name": entity_name, "fields": normalized_fields}]
            
            # Conversely, if entities is present, populate legacy entity/fields for compatibility
            elif data.get("entities") and not data.get("entity"):
                entities = data.get("entities")
                if entities and len(entities) > 0:
                    first_entity = entities[0]
                    data["entity"] = first_entity.get("name") if isinstance(first_entity, dict) else first_entity.name
                    fields = first_entity.get("fields", []) if isinstance(first_entity, dict) else first_entity.fields
                    data["fields"] = [f if isinstance(f, dict) else f.model_dump() for f in fields]
        
        return data

    @property
    def task_type(self) -> str:
        return self.intent

    @property
    def skill(self) -> str:
        if self.intent == "create_project": return "project-gen"
        if "model" in self.intent: return "django-model-gen"
        if "api" in self.intent: return "django-api-gen"
        if "test" in self.intent: return "tests-gen"
        return "bug-fix"
        
    @property
    def app_name(self) -> str:
        return self.app
        
    @property
    def target_files(self) -> List[str]:
        if self.intent == "create_project": return []
        if not self.app and not self.target_file: return []
        
        app_path = self.app
        if self.intent in ["generate_tests", "fix_tests"]:
            if self.target_file:
                filename = os.path.basename(self.target_file).replace(".py", "")
                if self.test_location == "in-app":
                    return [f"{app_path}/tests/test_{filename}.py"]
                else:
                    return [f"tests/{app_path}/test_{filename}.py"]
            
            if self.test_location == "in-app":
                return [f"{app_path}/tests/test_{self.entity.lower() if self.entity else 'views'}.py"]
            else:
                return [f"tests/{app_path}/test_{self.entity.lower() if self.entity else 'views'}.py"]
        elif "model" in self.intent:
            return [f"{app_path}/models.py", f"{app_path}/admin.py"]
        elif "api" in self.intent:
            return [f"{app_path}/models.py", f"{app_path}/serializers.py", f"{app_path}/views.py", f"{app_path}/urls.py"]
        return []

    @property
    def class_name(self) -> str:
        return self.entity

def get_installed_apps(project_path: str) -> List[str]:
    """Scans the project directory for Django apps (folders containing apps.py, models.py, or urls.py)."""
    apps = []
    if not os.path.exists(project_path):
        return apps
        
    for d in os.listdir(project_path):
        app_dir = os.path.join(project_path, d)
        if os.path.isdir(app_dir) and d not in ["config", "tests", ".venv", ".git", "__pycache__"]:
            # Check for standard Django app signatures
            if any(os.path.exists(os.path.join(app_dir, f)) for f in ["apps.py", "models.py", "urls.py", "views.py"]):
                apps.append(d)
    return apps

def _robust_json_extract(text: str) -> Optional[dict]:
    """
    Locates the first valid JSON object in the text and parses it.
    """
    # Find first '{'
    start_idx = text.find('{')
    if start_idx == -1:
        return None
    
    # Try parsing from start_idx to each possible closing '}' in reverse
    for end_idx in range(len(text) - 1, start_idx, -1):
        if text[end_idx] == '}':
            candidate = text[start_idx:end_idx+1]
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue
    return None

def plan(project_path: str, task: str) -> Plan:
    """
    Phase 1 Planner: Robust JSON output parsing.
    Extracts signal from noisy model output.
    """
    start_time = time.time()
    
    system_prompt = """
You are the ADE Planner. Your job is to parse complex multi-entity human commands into a strict structured JSON format.
You act as a System Architect. Extract ALL mentioned entities, relationships, and business logic.

Return ONLY valid JSON. No explanation. No extra text.

SUPPORTED COMMAND VARIATIONS:
- create a <type> project named <project_name>
- create system for <domain> (Customer, Order, Product...)
- create models <entities> in <app>
- create API for <entities> in <app>
- generate tests for <app>
- generate tests for <file_path>

RULES:
- `intent` must be one of: "create_project", "create_model", "create_api", "generate_tests", "fix_tests", "unclear"
- `entities`: MUST extract all entities. Each entity MUST have a `name` and a list of `fields`.
- `fields`: Return as structured objects with `name` and `type`.
- Supported types: string, int, float, decimal, bool, datetime, foreignkey, text, email, slug.
- `relations`: List of strings describing relationships (e.g., "Order belongs to Customer").
- `business_rules`: List of logic requirements.
- `actions`: List of required API actions (e.g., "Create Order", "List Products").
- `steps`: Procedural steps for implementation.
- Extract `app` precisely. If missing, leave empty (it will be inferred).
- NEVER return a null entity or empty entities list if models are requested.
- If the command is fundamentally unclear, output {"intent": "unclear", "error": "Could not extract entities. Provide structured input."}

REQUIRED SCHEMA:
{
  "intent": "create_model",
  "app": "core",
  "entities": [
    {
      "name": "Customer",
      "fields": [
        { "name": "name", "type": "string" },
        { "name": "email", "type": "email" }
      ]
    },
    {
      "name": "Order",
      "fields": [
        { "name": "customer", "type": "foreignkey" },
        { "name": "total", "type": "decimal" }
      ]
    }
  ],
  "relations": ["Order belongs to Customer"],
  "business_rules": ["Customer must have valid email"],
  "actions": ["CRUD for Customer", "Place Order"],
  "steps": ["Create models", "Run migrations"],
  "error": null
}

STRICT RULE: Return ONLY the JSON object. Do not include markdown code blocks.
"""

    try:
        raw_text = ollama_client.generate(
            model=config.planner_model,
            prompt=f"{system_prompt}\n\nUSER COMMAND: {task}",
            options={"temperature": 0.0, "num_ctx": 4096}
        )

        parsed = _robust_json_extract(raw_text)
        if not parsed:
            print(f"      ! Raw planner output was: {raw_text[:200]}...")
            return Plan(intent="unclear", app="", entities=[], error="Could not extract entities. Provide structured input.")
            
        try:
            validated_plan = Plan.model_validate(parsed)
        except ValidationError as ve:
            return Plan(intent="unclear", app="", entities=[], error=f"Planner produced invalid JSON structure: {str(ve)}")

        # Validation checks
        if validated_plan.intent in ["create_model", "create_api"]:
            if not validated_plan.entities:
                validated_plan.intent = "unclear"
                validated_plan.error = "Could not extract entities. Provide structured input."
            else:
                for ent in validated_plan.entities:
                    if not ent.name:
                        validated_plan.intent = "unclear"
                        validated_plan.error = "One or more entities missing name. Provide structured input."
                        break

        # Infer App if missing
        if validated_plan.intent not in ["unclear", "create_project"] and not validated_plan.app:
            installed_apps = get_installed_apps(project_path)
            if len(installed_apps) == 1:
                validated_plan.app = installed_apps[0]
            elif len(installed_apps) > 1:
                if validated_plan.target_file:
                    parts = validated_plan.target_file.split('/')
                    if parts[0] in installed_apps:
                        validated_plan.app = parts[0]
                
                if not validated_plan.app:
                    validated_plan.error = f"Multiple apps detected ({', '.join(installed_apps)}). Please specify target app."
                    validated_plan.intent = "unclear"
            else:
                if validated_plan.intent != "generate_tests":
                    validated_plan.error = "Command is missing required 'app' parameter and no apps found in project to infer from."
                    validated_plan.intent = "unclear"
                
        # Final safety check
        if validated_plan.intent == "unclear" and not validated_plan.error:
            validated_plan.error = "Could not extract entities. Provide structured input."

        # Basic Observability Hook
        elapsed = time.time() - start_time
        print(f"      [OBSERVABILITY] Planner used model: {config.planner_model} in {elapsed:.2f}s")
        
        return validated_plan

    except Exception as e:
        elapsed = time.time() - start_time
        print(f"      [OBSERVABILITY] Planner failed after {elapsed:.2f}s")
        return Plan(
            intent="unclear", 
            app="", 
            entity="", 
            fields=[], 
            steps=[], 
            error=f"Planner system error: {str(e)}"
        )

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python planner.py <project_path> <task>")
        sys.exit(1)

    result = plan(sys.argv[1], sys.argv[2])
    print(result.model_dump_json(indent=2))
