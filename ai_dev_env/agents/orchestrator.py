import os
import sys
import time
import subprocess
from ai_dev_env.agents import planner, coder, validator
from ai_dev_env.agents.django_automator import DjangoAutomator
from ai_dev_env.agents.dependency_manager import DependencyManager
from ai_dev_env.agents.consistency_checker import ConsistencyChecker
from ai_dev_env.agents.debugger import Debugger
from ai_dev_env.rag import indexer, retriever
from ai_dev_env.hooks import post_tool_memory

class Orchestrator:
    def __init__(self, project_name: str, base_projects_dir: str = None):
        self.project_name = project_name
        self.base_projects_dir = base_projects_dir or os.getenv("ADE_PROJECTS", os.path.join(os.getcwd(), "projects"))
        self.project_path = os.path.join(self.base_projects_dir, self.project_name)

    def create_checkpoint(self, project_path, message="ADE Checkpoint"):
        if not os.path.exists(os.path.join(project_path, ".git")):
            subprocess.run(["git", "init"], cwd=project_path, capture_output=True)
        
        subprocess.run(["git", "add", "-A"], cwd=project_path, capture_output=True)
        # Check if there are changes to commit
        status = subprocess.run(["git", "status", "--porcelain"], cwd=project_path, capture_output=True, text=True).stdout.strip()
        if status:
            subprocess.run(["git", "commit", "-m", message], cwd=project_path, capture_output=True)
        
        try:
            return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=project_path, text=True).strip()
        except subprocess.CalledProcessError:
            return None

    def rollback(self, project_path, checkpoint_hash):
        subprocess.run(["git", "reset", "--hard", checkpoint_hash], cwd=project_path, capture_output=True)
        subprocess.run(["git", "clean", "-fd"], cwd=project_path, capture_output=True)
        print(f"      ↩ Rolled back to checkpoint {checkpoint_hash[:8]}")

    def run_task(self, task: str, max_retries: int = 3):
        if not os.path.exists(self.project_path):
            # Special case: if task is create_project, we might not have the path yet
            # But the planner needs to run first to know the intent.
            # We'll handle project creation separately or allow planner to run without a path.
            pass

        start_total = time.time()

        # ── Pre-flight ──────────────────────────────────────────────
        checkpoint_hash = None

        # ── PHASE 1: Planning ────────────────────────────────────────
        print(f"\n[1/3] Planning: {task}")
        start_plan = time.time()
        plan_obj = planner.plan(self.project_path, task)
        
        if plan_obj.error:
            print(f"\n❌ [PLANNER ERROR] {plan_obj.error}")
            return False
            
        plan_obj.task = task  # thread original task into the plan object

        print(f"      Intent: {plan_obj.intent}  |  App: {plan_obj.app}  |  Skill: {plan_obj.skill}")

        # ── Phase 2: Django Automator (Pre-Code) ─────────────────────
        if plan_obj.intent == "create_project":
            from ai_dev_env.agents.project_manager import handle_create
            handle_create(plan_obj.project_name, plan_obj.type, self.base_projects_dir)
            # Update path after creation
            self.project_path = os.path.join(self.base_projects_dir, plan_obj.project_name)

        automator = DjangoAutomator(self.project_path)
        if plan_obj.app and plan_obj.intent != "create_project":
            try:
                automator.ensure_app(plan_obj.app)
                if plan_obj.intent in ["generate_tests", "fix_tests"]:
                    automator.ensure_tests_dir(plan_obj.app, plan_obj.test_location)
            except Exception as e:
                print(f"❌ [DJANGO AUTOMATION ERROR] {e}")
                return False

        # ── Pre-code Checkpoint ──────────────────────────────────────
        if os.path.exists(self.project_path):
            checkpoint_hash = self.create_checkpoint(self.project_path, message=f"ADE Automation: {plan_obj.intent}")

        # ── Index + Retrieve ─────────────────────────────────────────
        if os.path.exists(self.project_path):
            indexer.index_project(self.project_path)
            context = retriever.retrieve(self.project_path, task, plan_obj.target_files)
            context_block = retriever.build_context_block(context)
        else:
            context_block = ""
            
        plan_time = time.time() - start_plan

        # ── Load skill + global rules ────────────────────────────────
        skill_base = os.path.join(os.getenv("ADE_BASE", os.getcwd()), "ai_dev_env")
        skill_file = os.path.join(skill_base, "skills", f"{plan_obj.skill}.md")
        if not os.path.exists(skill_file):
            skill_file = os.path.join(skill_base, "skills/bug-fix.md")

        with open(skill_file, 'r') as f:         skill_instructions = f.read()
        with open(os.path.join(skill_base, "memory/global_rules.md"), 'r') as f: global_rules = f.read()

        # ── PHASE 2 & 3: Code → Validate Loop ───────────────────────
        code_time_total = 0
        val_time_total = 0
        val_instance = validator.ProjectValidator(self.project_path)
        debugger = Debugger()

        for attempt in range(1, max_retries + 1):
            print(f"\n[2/3] Coding (attempt {attempt}/{max_retries})")
            start_code = time.time()
            coder_inst = coder.ADE_Coder()
            try:
                ops = coder_inst.generate(coder.CoderInput(
                    task=task,
                    plan=plan_obj.model_dump(),
                    skill_instructions=skill_instructions,
                    context_block=context_block,
                    global_rules=global_rules,
                    project_path=self.project_path
                ))
                modified_files = coder_inst.apply_operations(ops, self.project_path)
                
                # ── Phase 2: Django Automator (Post-Code Wiring) ─────────────────────
                if plan_obj.app:
                    if plan_obj.intent in ["create_model", "create_api"]:
                        automator.ensure_urls_wired(plan_obj.app)
                        root_urls = automator.find_root_urls_path()
                        if root_urls:
                            rel_urls = os.path.relpath(root_urls, self.project_path)
                            if rel_urls not in modified_files:
                                modified_files.append(rel_urls)
                            
                dep_manager = DependencyManager(self.project_path)
                dep_manager.analyze_and_install(modified_files)

                # ── Phase 2: Cross-File Consistency Layer ───────────────────
                checker = ConsistencyChecker(self.project_path)
                consistency_errors = checker.check(modified_files)
                if consistency_errors:
                    raise RuntimeError("\n".join(consistency_errors))
                
                # ── Phase 2: Migrations ─────────────────────
                is_model_task = plan_obj.intent == "create_model"
                has_model_mod = any(f.endswith('models.py') for f in modified_files)
                
                if plan_obj.app and (is_model_task or has_model_mod):
                    err = automator.run_migrations(plan_obj.app)
                    if err:
                        raise RuntimeError(f"Django Execution Pipeline Failed: {err}")
                            
                code_time_total += (time.time() - start_code)
            except Exception as e:
                print(f"      ✗ Coder execution failed: {e}")
                # Pass specific error to coder in next attempt
                error_msg = str(e)
                feedback = f"\n\n--- PREVIOUS ATTEMPT FAILED ---\nError: {error_msg}\n"
                if "SyntaxError" in error_msg or "backslash" in error_msg.lower():
                    feedback += "CRITICAL: Do NOT include escape characters like backslashes (\\) or stray '\\ ' patterns. Output CLEAN Python code only.\n"
                if "Consistency Error" in error_msg:
                    feedback += "CRITICAL: Ensure that all models referenced in serializers exist, and all serializers/models referenced in views exist and are imported correctly.\n"
                if "fixture" in error_msg.lower() and "not found" in error_msg.lower():
                    feedback += "CRITICAL: Undefined fixture detected. Use ONLY 'api_client' and 'django_db'. You MUST define 'api_client' within the test file using a @pytest.fixture.\n"
                if "ModuleNotFoundError" in error_msg or "ImportError" in error_msg:
                    feedback += "CRITICAL: Detected import failure. Tests are located OUTSIDE the app directory. Always use ABSOLUTE imports (e.g., from core.models import Entity). NEVER use relative imports (e.g., from .models).\n"
                
                context_block += feedback + "DO NOT repeat this mistake. Follow the strict frameworks rules.\n"
                if checkpoint_hash:
                    self.rollback(self.project_path, checkpoint_hash)
                
                # If it's a model task, ensure migrations/db are clean for next attempt
                if plan_obj.app and (plan_obj.intent == "create_model" or "model" in task.lower()):
                    automator.reset_migrations(plan_obj.app)
                    automator.reset_database()
                    
                continue

            print(f"[3/3] Validating")
            start_val = time.time()
            res = val_instance.validate(validator.ValidationInput(
                project_path=self.project_path,
                modified_files=modified_files,
                plan=plan_obj.model_dump()
            ))
            val_time_total += (time.time() - start_val)

            if res.passed:
                print(f"\n✅ SUCCESS — {plan_obj.intent} complete")
                
                # Help the user run the new files/tests
                if plan_obj.intent in ["generate_tests", "fix_tests"]:
                    test_files = [f for f in modified_files if 'test' in f]
                    if test_files:
                        print(f"      → Run tests: pytest {os.path.join('projects', self.project_name, test_files[0])}")
                elif modified_files:
                     print(f"      → Main file: {os.path.join('projects', self.project_name, modified_files[0])}")

                post_tool_memory.write(plan_obj, ops, self.project_path)
                break
            else:
                print(f"      ✗ Failed at stage '{res.stage_reached}':\n{res.fix_signal[:500]}...")
                debug_advice = debugger.analyze(
                    task=task,
                    fix_signal=res.fix_signal or "",
                    modified_files=modified_files,
                    project_path=self.project_path
                )
                context_block += f"\n\n--- DEBUGGER ANALYSIS (attempt {attempt}) ---\n{debug_advice}\n"
                if checkpoint_hash:
                    self.rollback(self.project_path, checkpoint_hash)
                
                # If it's a model task, ensure migrations/db are clean for next attempt
                if plan_obj.app and (plan_obj.intent == "create_model" or "model" in task.lower()):
                    automator.reset_migrations(plan_obj.app)
                    automator.reset_database()
        else:
            print(f"\n❌ FAILED after {max_retries} attempts")
            return False

        elapsed = time.time() - start_total
        print(f"\n⏱ {elapsed:.1f}s total  ({plan_time:.1f}s plan | {code_time_total:.1f}s code | {val_time_total:.1f}s validate)")
        return True
