import os
import sys
import subprocess

def handle_create(name, ptype, base_projects_dir=None):
    projects_dir = base_projects_dir or os.getenv("ADE_PROJECTS", os.path.join(os.getcwd(), "projects"))
    project_path = os.path.join(projects_dir, name)
    
    if os.path.exists(project_path):
        # If it's just an empty dir or only contains .venv from a failed attempt, we might want to continue or ask for cleanup
        contents = os.listdir(project_path)
        if contents and contents != [".venv"]:
            print(f"❌ Project '{name}' already exists and is not empty at {project_path}")
            print(f"   Please delete it first: rm -rf {project_path}")
            return False
        print(f"⚠️  Directory exists but looks incomplete. Resuming initialization...")

    os.makedirs(project_path, exist_ok=True)
    
    if ptype == "django":
        print(f"🚀 Initializing Django project '{name}'...")
        try:
            # 1. Create venv
            subprocess.run([sys.executable, "-m", "venv", os.path.join(project_path, ".venv")], check=True)
            pip_bin = os.path.join(project_path, ".venv/bin/pip")
            
            # 2. Install django
            print("      → Installing Django & DRF...")
            subprocess.run([pip_bin, "install", "django", "djangorestframework", "django-cors-headers", "pytest", "pytest-django"], check=True)
            
            # 3. Start project
            python_bin = os.path.join(project_path, ".venv/bin/python")
            subprocess.run([python_bin, "-m", "django", "startproject", "config", "."], cwd=project_path, check=True)
            
            # 4. Git init
            subprocess.run(["git", "init"], cwd=project_path, check=True)
            subprocess.run(["git", "add", "."], cwd=project_path, check=True)
            subprocess.run(["git", "commit", "-m", "Initial Django project"], cwd=project_path, check=True)
            
            print(f"✅ Django project '{name}' created successfully.")
            return True
        except Exception as e:
            print(f"❌ Failed to create project: {e}")
            return False
    else:
        print(f"✅ Created empty project directory for '{name}'.")
        return True
