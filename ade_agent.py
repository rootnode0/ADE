## ade_agent.py
import os
import sys
import time
import argparse
import subprocess
from ai_dev_env.agents import planner, coder, validator
from ai_dev_env.agents.debugger import Debugger
from ai_dev_env.rag import indexer, retriever
from ai_dev_env.hooks import post_tool_memory

def get_current_commit(project_path):
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=project_path, text=True).strip()

def rollback(project_path, checkpoint_hash):
    subprocess.run(["git", "checkout", checkpoint_hash, "--", "."], cwd=project_path)
    print(f"      ↩ Rolled back to checkpoint {checkpoint_hash[:8]}")

def main():
    parser = argparse.ArgumentParser(description="ADE Orchestrator")
    parser.add_argument("project_name", help="Name of project in projects/")
    parser.add_argument("task", help="The coding task to execute")
    parser.add_argument("--max-retries", type=int, default=3)
    args = parser.parse_args()

    base_projects_dir = os.getenv("ADE_PROJECTS", os.path.join(os.getcwd(), "projects"))
    project_path = os.path.join(base_projects_dir, args.project_name)

    if not os.path.exists(project_path):
        print(f"✗ Project not found at {project_path}")
        sys.exit(1)

    start_total = time.time()

    # ── Pre-flight ──────────────────────────────────────────────
    validator.patch_django_settings(project_path)
    subprocess.run(["git", "add", "-A"], cwd=project_path)
    checkpoint_hash = get_current_commit(project_path)

    # ── PHASE 1: Planning ────────────────────────────────────────
    print(f"\n[1/3] Planning: {args.task}")
    start_plan = time.time()
    plan_obj = planner.plan(project_path, args.task)
    plan_obj.task = args.task  # thread original task into the plan object

    print(f"      Skill: {plan_obj.skill}  |  Type: {plan_obj.task_type}  |  App: {plan_obj.app_name}")

    # ── Index + Retrieve ─────────────────────────────────────────
    indexer.index_project(project_path)
    context = retriever.retrieve(project_path, args.task, plan_obj.target_files)
    context_block = retriever.build_context_block(context)
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
    val_instance = validator.ProjectValidator(project_path)
    debugger = Debugger()

    for attempt in range(1, args.max_retries + 1):
        print(f"\n[2/3] Coding (attempt {attempt}/{args.max_retries})")
        start_code = time.time()
        coder_inst = coder.ADE_Coder()
        try:
            ops = coder_inst.generate(coder.CoderInput(
                task=args.task,
                plan=plan_obj.model_dump(),
                skill_instructions=skill_instructions,
                context_block=context_block,
                global_rules=global_rules,
                project_path=project_path
            ))
            modified_files = coder_inst.apply_operations(ops, project_path)
            code_time_total += (time.time() - start_code)
        except Exception as e:
            print(f"      ✗ Coder failed: {e}")
            if attempt == args.max_retries:
                rollback(project_path, checkpoint_hash)
            continue

        print(f"[3/3] Validating")
        start_val = time.time()
        res = val_instance.validate(validator.ValidationInput(
            project_path=project_path,
            modified_files=modified_files,
            plan=plan_obj.model_dump()
        ))
        val_time_total += (time.time() - start_val)

        if res.passed:
            print(f"\n✅ SUCCESS — {plan_obj.task_type} complete")
            post_tool_memory.write(plan_obj, ops, project_path)
            break
        else:
            print(f"      ✗ Failed at stage '{res.stage_reached}': {res.fix_signal[:120] if res.fix_signal else 'unknown'}")
            # Debugger analyses failure and enriches context for next attempt
            debug_advice = debugger.analyze(
                task=args.task,
                fix_signal=res.fix_signal or "",
                modified_files=modified_files,
                project_path=project_path
            )
            context_block += f"\n\n--- DEBUGGER ANALYSIS (attempt {attempt}) ---\n{debug_advice}\n"
            rollback(project_path, checkpoint_hash)
    else:
        print(f"\n❌ FAILED after {args.max_retries} attempts")

    elapsed = time.time() - start_total
    print(f"\n⏱ {elapsed:.1f}s total  ({plan_time:.1f}s plan | {code_time_total:.1f}s code | {val_time_total:.1f}s validate)")

if __name__ == "__main__":
    main()
