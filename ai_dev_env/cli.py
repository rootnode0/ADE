import sys
import os
import argparse
import subprocess
from ai_dev_env.agents.orchestrator import Orchestrator
from ai_dev_env.agents import planner
from ai_dev_env.config.manager import config
import requests
import json
from ai_dev_env.agents.project_manager import handle_create

def print_banner():
    print("""
    █████╗ ██████╗ ███████╗
    ██╔══██╗██╔══██╗██╔════╝
    ███████║██║  ██║█████╗  
    ██╔══██║██║  ██║██╔══╝  
    ██║  ██║██████╔╝███████╗
    ╚═╝  ╚═╝╚═════╝ ╚══════╝
    Agentic Development Engine
    """)

def handle_chat(project_name):
    projects_dir = os.getenv("ADE_PROJECTS", os.path.join(os.getcwd(), "projects"))
    project_path = os.path.join(projects_dir, project_name)
    
    if not os.path.exists(project_path):
        print(f"❌ Project '{project_name}' not found.")
        return

    print(f"💬 Entering Chat Mode for project: {project_name}")
    print("Type 'exit' or 'quit' to leave. Type 'task: <task>' to execute a coding task.")
    
    from ai_dev_env.rag import indexer, retriever
    indexer.index_project(project_path)
    
    while True:
        try:
            user_input = input(f"ade:{project_name}> ").strip()
            if user_input.lower() in ["exit", "quit"]:
                break
            if not user_input:
                continue
            
            if user_input.lower().startswith("task:"):
                task = user_input[5:].strip()
                orch = Orchestrator(project_name)
                orch.run_task(task)
                continue

            # Conversational mode
            context = retriever.retrieve(project_path, user_input, [])
            context_block = retriever.build_context_block(context)
            
            prompt = f"You are ADE Chat, a helpful developer assistant for the project '{project_name}'.\n"
            prompt += f"Context from codebase:\n{context_block}\n\n"
            prompt += f"User Question: {user_input}\n\nResponse:"
            
            url = f"{config.ollama_base_url}/api/generate"
            payload = {
                "model": config.fast_model,
                "prompt": prompt,
                "stream": True
            }
            
            response = requests.post(url, json=payload, stream=True)
            for line in response.iter_lines():
                if line:
                    chunk = json.loads(line)
                    print(chunk.get('response', ''), end='', flush=True)
            print("\n")
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\n❌ Error: {e}")

def main():
    if len(sys.argv) < 2:
        print_banner()
        print("Usage:")
        print("  ade <project> \"<task>\"")
        print("  ade create <project_name> --type django")
        print("  ade chat <project>")
        return

    first_arg = sys.argv[1]
    
    if first_arg == "create":
        parser = argparse.ArgumentParser(prog="ade create")
        parser.add_argument("name")
        parser.add_argument("--type", default="django")
        args = parser.parse_args(sys.argv[2:])
        handle_create(args.name, args.type)
        
    elif first_arg == "chat":
        if len(sys.argv) < 3:
            print("Usage: ade chat <project>")
            return
        handle_chat(sys.argv[2])
        
    else:
        # Check if first_arg is a known project
        projects_dir = os.getenv("ADE_PROJECTS", os.path.join(os.getcwd(), "projects"))
        project_path = os.path.join(projects_dir, first_arg)
        
        if os.path.exists(project_path) and os.path.isdir(project_path):
            project_name = first_arg
            task = " ".join(sys.argv[2:])
            if not task:
                print(f"Usage: ade {project_name} \"<task>\"")
                return
            orch = Orchestrator(project_name)
            orch.run_task(task)
        else:
            # Maybe it's a task for a new project?
            task = " ".join(sys.argv[1:])
            print(f"🔍 Detecting intent for: {task}")
            # Use planner to see if it's a create_project intent
            plan = planner.plan("", task)
            if plan.intent == "create_project":
                handle_create(plan.project_name, plan.type)
            else:
                print(f"❌ Project '{first_arg}' not found and task is not a project creation command.")

if __name__ == "__main__":
    main()
