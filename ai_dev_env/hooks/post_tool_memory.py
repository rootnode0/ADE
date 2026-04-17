import os
import json
from datetime import datetime

def write(plan, operations, project_path):
    # Ensure ADE_BASE is set, fallback to current directory if not
    base_path = os.getenv("ADE_BASE", os.getcwd())
    session_dir = os.path.join(base_path, "ai_dev_env/memory/sessions")

    # CRITICAL FIX: Create the directory if it doesn't exist
    os.makedirs(session_dir, exist_ok=True)

    project_name = os.path.basename(project_path)

    session_data = {
        "timestamp": datetime.now().isoformat(),
        "project": project_name,
        "plan": plan.model_dump(),
        "operations_count": len(operations),
        "success": True
    }

    # Generate filename based on date, project, and task type
    date_str = datetime.now().strftime('%Y-%m-%d')
    filename = f"{date_str}_{project_name}_{plan.task_type}.json"

    file_path = os.path.join(session_dir, filename)

    try:
        with open(file_path, 'w') as f:
            json.dump(session_data, f, indent=2)
        print(f"      📝 Session logged to memory: {filename}")
    except Exception as e:
        print(f"      ⚠️  Warning: Could not log session memory: {e}")
