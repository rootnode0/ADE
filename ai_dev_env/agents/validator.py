import os
import ast
import subprocess
import sys
from typing import List, Optional
from pydantic import BaseModel

# 1. Data Structures for Agent Communication
class ValidationInput(BaseModel):
    project_path: str
    modified_files: List[str]
    plan: dict

class ValidationResult(BaseModel):
    passed: bool
    stage_reached: str
    errors: List[str]
    raw_output: str
    fix_signal: Optional[str] = None

class ProjectValidator:
    def __init__(self, project_path: str):
        self.project_path = project_path

    def _run_in_project(self, cmd: List[str], timeout: int) -> tuple[str, str, int]:
        """Executes commands, falling back to sys.executable if project .venv is missing."""
        project_venv_python = os.path.join(self.project_path, ".venv/bin/python")
        python_bin = project_venv_python if os.path.exists(project_venv_python) else sys.executable

        final_cmd = []
        if cmd[0] in ["python", "python3"]:
            final_cmd = [python_bin] + cmd[1:]
        elif cmd[0] == "manage.py":
            final_cmd = [python_bin] + cmd
        else:
            final_cmd = cmd

        env = os.environ.copy()
        current_pp = env.get("PYTHONPATH", "")
        env["PYTHONPATH"] = f"{self.project_path}:{current_pp}" if current_pp else self.project_path
        
        # Determine DJANGO_SETTINGS_MODULE
        # Usually it's in a 'config' or 'project_name' folder. 
        # We'll look for settings.py and derive the module path.
        for root, dirs, files in os.walk(self.project_path):
            if "settings.py" in files:
                rel_dir = os.path.relpath(root, self.project_path)
                if rel_dir == ".":
                    env["DJANGO_SETTINGS_MODULE"] = "settings"
                else:
                    env["DJANGO_SETTINGS_MODULE"] = f"{rel_dir.replace(os.sep, '.')}.settings"
                break

        if os.path.exists(os.path.join(self.project_path, ".venv")):
            env["VIRTUAL_ENV"] = os.path.join(self.project_path, ".venv")

        try:
            process = subprocess.Popen(
                final_cmd,
                cwd=self.project_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True
            )
            stdout, stderr = process.communicate(timeout=timeout)
            return stdout, stderr, process.returncode
        except Exception as e:
            return "", str(e), 1

    def validate(self, val_input: ValidationInput) -> ValidationResult:
        # --- STAGE 1: Syntax ---
        for rel_path in val_input.modified_files:
            full_path = os.path.join(self.project_path, rel_path)
            if rel_path.endswith('.py') and os.path.exists(full_path):
                try:
                    with open(full_path, 'r') as f:
                        ast.parse(f.read())
                except SyntaxError as e:
                    msg = f"SyntaxError in {rel_path} at line {e.lineno}: {e.msg}"
                    return ValidationResult(passed=False, stage_reached="syntax", errors=[msg], raw_output=str(e), fix_signal=msg)

        # --- STAGE 2: Django Check ---
        stdout, stderr, code = self._run_in_project(["python", "manage.py", "check"], timeout=20)
        if code != 0:
            combined = (stderr + "\n" + stdout).strip()
            # Clean up traceback to show the most relevant part
            summary = combined.split('\n')[-5:]
            return ValidationResult(
                passed=False, 
                stage_reached="structure", 
                errors=[combined], 
                raw_output=combined, 
                fix_signal=f"Django check failed:\n{combined}"
            )

        # --- STAGE 3: Pytest ---
        # Exit codes: 0=Success, 1=Tests failed, 2=Interrupted, 5=No tests collected
        stdout, stderr, code = self._run_in_project(["python", "-m", "pytest", ".", "-q", "--tb=short"], timeout=60)
        
        # If the goal is to generate or fix tests, 'no tests collected' is a failure
        intent = val_input.plan.get("intent", "")
        is_test_intent = intent in ["generate_tests", "fix_tests"]
        if is_test_intent and code == 5:
            return ValidationResult(
                passed=False, 
                stage_reached="tests", 
                errors=["No tests were collected by pytest."], 
                fix_signal="Pytest failed to collect any tests. Ensure your test files are named correctly (test_*.py) and classes/methods follow pytest conventions."
            )

        if code not in [0, 5]:  
            combined = f"{stdout}\n{stderr}".strip()
            return ValidationResult(passed=False, stage_reached="tests", errors=["Pytest failure"], raw_output=combined, fix_signal=f"Tests failed:\n{combined[-500:]}")

        # --- STAGE 4: Completeness ---
        # Ensure all files that SHOULD have been created/modified actually exist and are non-empty
        app = val_input.plan.get("app", "")
        target_files = []
        if "model" in intent:
            target_files = [f"{app}/models.py"]
        elif "api" in intent:
            target_files = [f"{app}/models.py", f"{app}/serializers.py", f"{app}/views.py", f"{app}/urls.py"]
        elif "test" in intent:
             # Basic check for at least one test file
             if not any('test' in f for f in val_input.modified_files):
                 return ValidationResult(passed=False, stage_reached="completeness", errors=["No test files were created/modified."], fix_signal="The plan was to generate tests, but no test files were found in the modifications.")

        for rel_path in val_input.modified_files:
            full_path = os.path.join(self.project_path, rel_path)
            if os.path.exists(full_path):
                size = os.path.getsize(full_path)
                if size > 50000: # 50KB is huge for a generated file
                    return ValidationResult(passed=False, stage_reached="completeness", errors=[f"File too large: {rel_path} ({size} bytes)"], fix_signal=f"The file {rel_path} is suspiciously large. This is likely due to an infinite generation loop. Please rewrite the file concisely.")
                if size < 10: # Basically empty
                    msg = f"Target file is empty: {rel_path}"
                    return ValidationResult(passed=False, stage_reached="completeness", errors=[msg], fix_signal=f"The file {rel_path} is empty. Please provide the actual implementation.")

        return ValidationResult(passed=True, stage_reached="all", errors=[], raw_output=stdout)

def patch_django_settings(project_path: str):
    """Ensures all local apps are properly registered in INSTALLED_APPS."""
    settings_path = os.path.join(project_path, "config", "settings.py")
    if not os.path.exists(settings_path): return

    # Detect all valid Django apps
    local_apps = []
    for item in os.listdir(project_path):
        app_path = os.path.join(project_path, item)
        # Check if it's a directory and has an apps.py
        if os.path.isdir(app_path) and os.path.exists(os.path.join(app_path, "apps.py")):
            if item not in ["config", "tests"]:
                local_apps.append(item)
    
    local_apps.sort()

    with open(settings_path, "r") as f:
        content = f.read()

    missing_apps = [app for app in local_apps if f"'{app}'" not in content and f'"{app}"' not in content]
    if not missing_apps:
        return

    if "INSTALLED_APPS = [" in content:
        insertion = "INSTALLED_APPS = [\n" + "\n".join([f"    '{app}'," for app in missing_apps])
        new_content = content.replace("INSTALLED_APPS = [", insertion)
        with open(settings_path, "w") as f:
            f.write(new_content)
        print(f"      → Auto-patched INSTALLED_APPS in settings.py with: {', '.join(missing_apps)}")
