import json
import re
import ast
import os
from typing import List, Literal, Optional
from pydantic import BaseModel, ValidationError
from ai_dev_env.config.manager import config
from ai_dev_env.utils import ollama_client

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
        self.fallback_model = "mistral:latest"

    def generate(self, coder_input: CoderInput) -> List[FileOperation]:
        """Executes the coding phase with fallback logic."""
        models_to_try = [self.primary_model, self.fallback_model, "qwen2.5-coder:1.5b"]

        for model in models_to_try:
            try:
                return self._execute_generation(model, coder_input)
            except Exception as e:
                print(f"      ✗ Model {model} failed: {e}")
                if model == "qwen2.5-coder:1.5b":
                    raise RuntimeError(f"All coder models failed (including ultra-light fallback). Last error: {e}")
                print(f"      → Switching to fallback: {models_to_try[models_to_try.index(model)+1]}")

    def _robust_json_extract(self, text: str) -> Optional[list]:
        """
        Cleans and extracts JSON arrays from noisy LLM output.
        """
        # Remove <think> tags or internal reasoning
        text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL).strip()
        
        # Remove markdown code block fences if present
        text = re.sub(r'```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```', '', text)
        text = text.strip().lstrip('```json').lstrip('```').rstrip('```').strip()

        # Try to find a JSON array [ ... ]
        # We look for the LAST opening bracket and FIRST closing bracket to avoid 
        # picking up reasoning if it contains brackets? No, usually it's [ ... ]
        
        match = re.search(r'\[.*\]', text, re.DOTALL)
        if not match:
            # Try to find a JSON object { ... }
            obj_match = re.search(r'\{.*\}', text, re.DOTALL)
            if obj_match:
                try:
                    obj = json.loads(obj_match.group(0))
                    return [obj]
                except: return None
            return None

        json_str = match.group(0)
        
        # Hallucination Prevention: If json_str is suspiciously long (> 100KB), it's probably garbage
        if len(json_str) > 100_000:
             print("      ! Warning: Extracted JSON is suspiciously large (>100KB). Truncating.")
             json_str = json_str[:100000] + ']' # Try to close it
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
        strict_contract = """
        You MUST output ONLY valid FileOperation JSON.

        STRICT ARCHITECTURE CONTROL:
        - You are ONLY responsible for code content inside the target app's directory.
        - You MUST NOT modify `settings.py`, root `urls.py`, or any file outside the target app.

        CODE QUALITY REQUIREMENTS:
        - Output CLEAN Python code only.
        - Do NOT include escape characters (like stray backslashes) in your code content.
        - NEVER include leading backslashes (\\) at the start of files or lines.
        - No stray "\\ " patterns.
        - If your code contains syntax errors, it will be REJECTED.

        Allowed actions:
        - create
        - append
        - replace_block
        - full_replace

        Output format:
        [
          {
            "action": "create",
            "file": "core/views.py",
            "content": "<full valid code>",
            "reasoning": "..."
          }
        ]

        STRICT LIMITS:
        - NEVER output more than 300 lines per file.
        - If you generate more than 1000 lines total, your output will be TRUNCATED and REJECTED.
        - NEVER repeat the same line or block infinitely.
        - Be concise. Only generate necessary code.

        DO NOT include explanations.
        DO NOT include markdown.
        ONLY return JSON.
        """

        system_prompt = f"""
        You are ADE Coder.
        {strict_contract}

        GLOBAL RULES:
        {coder_input.global_rules}

        SKILL INSTRUCTIONS:
        {coder_input.skill_instructions}
        """

        # Prepare entity block for prompt
        entities_desc = ""
        entities = coder_input.plan.get('entities', [])
        if entities:
            for ent in entities:
                fields_str = ", ".join([f"{f['name']}({f['type']})" for f in ent.get('fields', [])])
                entities_desc += f"- {ent['name']}: {fields_str}\n"
        else:
            entities_desc = coder_input.plan.get('entity', 'None')

        user_prompt = f"""
        TASK: {coder_input.task}
        APP: {coder_input.plan.get('app', 'core')}
        ENTITIES:
        {entities_desc}
        TARGET FILES: {', '.join(coder_input.plan.get('target_files', []))}

        CONTEXT:
        {coder_input.context_block}

        IMPLEMENTATION STRATEGY:
        1. Iterate through all entities listed above.
        2. Generate models sequentially in `models.py`.
        3. Ensure ForeignKeys are handled correctly by ordering models based on dependencies.
        4. If API is requested, generate Serializers, Views, and URLs for ALL entities.

        Generate the JSON array of file operations now:
        """

        raw_output = ollama_client.generate(
            model=model,
            prompt=f"{system_prompt}\n\n{user_prompt}",
            options={
                "temperature": 0.0,
                "num_ctx": config.context_length,
                "num_gpu": config.gpu_layers
            }
        )

        ops_data = self._robust_json_extract(raw_output)
        if not ops_data or not isinstance(ops_data, list):
            raise ValueError(f"Failed to extract JSON array from {model}. Raw output was invalid JSON.")

        ACTION_MAP = {
            "create_block": "create",
            "modify": "replace_block",
            "update": "replace_block",
            "add": "create",
            "new": "create",
            "write": "create",
            "insert": "create",
            "replace": "full_replace",
            "overwrite": "full_replace"
        }

        operations = []
        for op in ops_data:
            if not isinstance(op, dict): 
                raise ValueError(f"Operation must be a dictionary, got {type(op)}")

            # 1. Normalize Action
            original_action = op.get("action", "unknown")
            if original_action in ACTION_MAP:
                corrected = ACTION_MAP[original_action]
                print(f"      ℹ Corrected invalid action: '{original_action}' → '{corrected}'")
                op["action"] = corrected
            
            # Handle common field name variations
            if "operation" in op: op["action"] = op.pop("operation")
            if "file_path" in op: op["file"] = op.pop("file_path")
                
            if isinstance(op.get("content"), list): op["content"] = "\n".join(op["content"])
            if "reasoning" not in op: op["reasoning"] = "Applied by ADE Coder."

            try:
                # 2. Scope Validation
                app_name = coder_input.plan.get("app", "")
                if app_name and not op["file"].startswith(f"{app_name}/") and "tests/" not in op["file"]:
                    raise ValueError(f"CRITICAL ARCHITECTURE VIOLATION: AI attempted to modify file outside of app scope: {op['file']}. You are ONLY allowed to modify files inside {app_name}/.")

                # 3. Hallucination Check (Total Length)
                content_len = len(op["content"])
                if content_len > 20000: # ~400 lines
                    raise ValueError(f"HALLUCINATION DETECTED: Content for {op['file']} is suspiciously long ({content_len} chars). Please be more concise.")

                # 3. Code Sanitization
                op["content"] = self._sanitize_content(op["content"])

                # 4. Repetition Check
                lines = op["content"].split('\n')
                if len(lines) > 20:
                    for i in range(len(lines) - 10):
                        if len(set(lines[i:i+10])) == 1 and len(lines[i].strip()) > 0:
                            raise ValueError(f"HALLUCINATION DETECTED: Content for {op['file']} contains excessive repetition. Please rewrite concisely.")

                # 5. Syntax Validation
                if op["file"].endswith(".py"):
                    self._validate_syntax(op["file"], op["content"])

                operations.append(FileOperation(**op))
            except ValidationError as ve:
                raise ValueError(f"Previous attempt failed due to invalid FileOperation action. Error: {ve}. You MUST use ONLY allowed actions.")
            except (SyntaxError, ValueError) as e:
                # Wrap and re-raise for retry logic
                raise ValueError(f"Code Quality Violation in {op['file']}: {str(e)}")

        if not operations:
            raise ValueError("No valid file operations applied. You MUST return at least one operation.")

        return operations

    def _sanitize_content(self, content: str) -> str:
        """Removes common LLM escape artifacts and normalizes code."""
        # 1. Strip leading backslashes (hallucinated line continuations)
        lines = content.split('\n')
        sanitized_lines = []
        for line in lines:
            # Strip leading \ followed by whitespace
            line = re.sub(r'^\s*\\\s*', '', line)
            sanitized_lines.append(line)
        
        content = '\n'.join(sanitized_lines)
        
        # 2. Fix stray \ patterns
        content = content.replace('\\ ', ' ')
        
        return content.strip()

    def _validate_syntax(self, filename: str, content: str):
        """Ensures generated Python code is syntactically valid."""
        try:
            ast.parse(content)
        except SyntaxError as e:
            raise SyntaxError(f"Generated code for {filename} contains a SyntaxError at line {e.lineno}: {e.msg}. Do NOT include escape characters or stray backslashes.")

    def apply_operations(self, operations: List[FileOperation], project_path: str) -> List[str]:
        modified_files = []
        applied_count = 0
        
        for op in operations:
            full_path = os.path.join(project_path, op.file)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)

            if op.action in ["create", "full_replace"]:
                with open(full_path, 'w') as f: f.write(op.content)
                applied_count += 1
            elif op.action == "append":
                with open(full_path, 'a') as f: f.write(f"\n\n{op.content}")
                applied_count += 1
            elif op.action == "replace_block":
                if not os.path.exists(full_path):
                    print(f"      ℹ File {op.file} missing for replace_block. Falling back to 'create'.")
                    with open(full_path, 'w') as f: f.write(op.content)
                    applied_count += 1
                else:
                    content = open(full_path).read()
                    # CRITICAL: Prevent empty identifier from exploding file size
                    identifier = (op.block_identifier or '').strip()
                    if not identifier or identifier not in content:
                         print(f"      ℹ Valid block identifier not found in {op.file}. Performing full write to prevent corruption.")
                         with open(full_path, 'w') as f: f.write(op.content)
                    else:
                        new_content = content.replace(identifier, op.content)
                        with open(full_path, 'w') as f: f.write(new_content)
                    applied_count += 1

            if op.file not in modified_files:
                modified_files.append(op.file)
            print(f"      ✎ {op.action}: {op.file}")

        if applied_count == 0:
            raise RuntimeError("No valid file operations applied. Previous attempt failed due to invalid FileOperation action or no changes applied.")

        print(f"      ℹ Total operations applied: {applied_count}")
        print(f"      ℹ Files modified: {', '.join(modified_files)}")
        return modified_files
