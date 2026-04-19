import sys
import argparse
from ai_dev_env.agents.orchestrator import Orchestrator

def main():
    parser = argparse.ArgumentParser(description="ADE Orchestrator (Legacy Wrapper)")
    parser.add_argument("project_name", help="Name of project in projects/")
    parser.add_argument("task", help="The coding task to execute")
    parser.add_argument("--max-retries", type=int, default=3)
    args = parser.parse_args()

    orch = Orchestrator(args.project_name)
    success = orch.run_task(args.task, max_retries=args.max_retries)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
