import json
import re
import requests
import ast
import os
from typing import List, Literal, Optional
from pydantic import BaseModel, ValidationError
from ai_dev_env.config.manager import config

class FileOperation(BaseModel):
    file: str
    action: Literal["create", "append", "replace_block", "full_replace"]
    content: str
    block_identifier: Optional[str] = None
    reasoning: str

class CoderInput(BaseModel):
    task: str                   # original task string from CLI
    plan: dict
    skill_instructions: str
    context_block: str
    global_rules: str
    project_path: str

class ADE_Coder:
    def __init__(self):
        self.base_url = f"{config.ollama_base_url}/api/generate"
        self.primary_model = config.coder_model
        self.fallback_model = os.getenv("ADE_MODEL_CODER_FALLBACK", "qwen2.5-coder:1.5b")

    def generate(self, coder_input: CoderInput) -> List[FileOperation]:
        """Executes the coding phase with fallback logic."""
        models_to_try = [self.primary_model, self.fallback_model]

        for model in models_to_try:
            try:
                return self._execute_generation(model, coder_input)
            except Exception as e:
                print(f"      ✗ Model {model} failed: {e}")
                if model == self.fallback_model:
                    raise RuntimeError("All coder models failed.")
                print(f"      → Switching to fallback: {self.fallback_model}")

    def _robust_json_extract(self, text: str) -> Optional[list]:
        """
        Cleans and extracts JSON arrays from noisy LLM output.
        """
        # Remove <think> tags or internal reasoning
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()

        # Try to find a JSON array [ ... ]
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if not match:
            obj_match = re.search(r'\{.*\}', text, re.DOTALL)
            if obj_match:
                try:
                    obj = json.loads(obj_match.group(0))
                    return [obj]
                except: return None
            return None

        json_str = match.group(0)
        # Clean trailing commas which break json.loads
        json_str = re.sub(r',\s*\]', ']', json_str)
        json_str = re.sub(r',\s*\}', '}', json_str)

        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            try:
                return ast.literal_eval(json_str)
            except:
                return None

    def _execute_generation(self, model: str, coder_input: CoderInput) -> List[FileOperation]:
        system_prompt = f"""
        You are ADE Coder. You MUST output a JSON array of file operation objects.
        DO NOT include markdown code blocks (```json).
        DO NOT include any text before or after the JSON array.

        Each object MUST have exactly these keys:
        - "file": relative path string (e.g. "core/models.py")
        - "action": one of "create", "append", "replace_block", "full_replace"
        - "content": string of the actual code to write
        - "reasoning": one-line explanation of this operation

        GLOBAL RULES:
        {coder_input.global_rules}

        SKILL INSTRUCTIONS:
        {coder_input.skill_instructions}
        """

        user_prompt = f"""
        TASK: {coder_input.task}
        APP: {coder_input.plan.get('app_name', 'core')}
        CLASS: {coder_input.plan.get('class_name', '')}
        TARGET FILES: {', '.join(coder_input.plan.get('target_files', []))}

        CONTEXT:
        {coder_input.context_block}

        Generate the JSON array of file operations now:
        """

        payload = {
            "model": model,
            "prompt": f"{system_prompt}\n\n{user_prompt}",
            "stream": False,
            "options": {
                "temperature": 0.0,
                "num_ctx": config.context_length,
                "num_gpu": config.gpu_layers
            }
        }

        response = requests.post(self.base_url, json=payload, timeout=120)
        response.raise_for_status()
        raw_output = response.json().get('response', '')

        ops_data = self._robust_json_extract(raw_output)
        if not ops_data or not isinstance(ops_data, list):
            raise ValueError(f"Failed to extract JSON array from {model}. Raw: {raw_output[:200]}")

        operations = []
        for op in ops_data:
            if not isinstance(op, dict): continue

            # Field normalization — handle common LLM variations
            if "operation" in op: op["action"] = op.pop("operation")
            if isinstance(op.get("content"), list): op["content"] = "\n".join(op["content"])
            if "reasoning" not in op: op["reasoning"] = "Applied by ADE Coder."

            try:
                operations.append(FileOperation(**op))
            except ValidationError as ve:
                print(f"      ! Skipping invalid operation: {ve}")
                continue

        if not operations:
            raise ValueError("No valid FileOperations extracted from LLM output.")

        # AST Validation for Python files before returning
        for op in operations:
            if op.file.endswith('.py'):
                try:
                    ast.parse(op.content)
                except SyntaxError as se:
                    raise ValueError(f"SyntaxError in generated {op.file} at line {se.lineno}: {se.msg}")

        return operations

    def apply_operations(self, operations: List[FileOperation], project_path: str) -> List[str]:
        modified_files = []
        for op in operations:
            full_path = os.path.join(project_path, op.file)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            if op.action in ["create", "full_replace"]:
                with open(full_path, 'w') as f: f.write(op.content)
            elif op.action == "append":
                with open(full_path, 'a') as f: f.write(f"\n\n{op.content}")
            elif op.action == "replace_block":
                if not os.path.exists(full_path):
                    raise FileNotFoundError(f"Cannot replace block in non-existent file: {op.file}")
                content = open(full_path).read()
                if op.block_identifier and op.block_identifier not in content:
                    raise ValueError(f"Block identifier '{op.block_identifier}' not found in {op.file}")
                new_content = content.replace(op.block_identifier or '', op.content)
                with open(full_path, 'w') as f: f.write(new_content)

            modified_files.append(op.file)
            print(f"      ✎ {op.action}: {op.file}")
        return modified_files
