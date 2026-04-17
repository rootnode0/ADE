"""
ADE Debugger Agent
==================
When validation fails, the Debugger uses a reasoning model (deepseek-r1) to
produce a structured, actionable fix plan rather than just forwarding the
raw error string to the coder.

Output is a concise analysis block injected into the coder's context on the
next retry attempt.
"""
import os
import re
import requests
from ai_dev_env.config.manager import config


class Debugger:
    def __init__(self):
        self.url = f"{config.ollama_base_url}/api/generate"
        self.model = config.debug_model

    def analyze(
        self,
        task: str,
        fix_signal: str,
        modified_files: list,
        project_path: str,
    ) -> str:
        """
        Analyzes a validation failure and returns a structured fix-advice string
        to be injected into the coder's context on the next attempt.

        Returns a plain-text analysis block.
        """
        file_snippets = self._read_file_snippets(modified_files, project_path)

        prompt = f"""
You are ADE Debugger. A coding agent attempted a task and the validation failed.
Analyze the failure and provide concise, targeted fix instructions.

ORIGINAL TASK:
{task}

VALIDATION ERROR:
{fix_signal[:1000]}

MODIFIED FILES (first 60 lines each):
{file_snippets}

Your response MUST follow this structure exactly:
ROOT CAUSE: [one sentence]
FIX TARGET: [filename:line or general area]
FIX ACTION: [concrete code change needed — be specific]
AVOID: [what NOT to do on the next attempt]

Be brief and precise. No preamble. No markdown. No explanations beyond the format above.
"""
        try:
            resp = requests.post(
                self.url,
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.0,
                        "num_ctx": 4096,
                    },
                },
                timeout=60,
            )
            resp.raise_for_status()
            raw = resp.json().get("response", "")
            # Strip <think> blocks from reasoning models
            raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
            return raw if raw else f"[Debugger: no analysis generated]\nRaw error: {fix_signal[:300]}"
        except Exception as e:
            # Debugger failure is non-fatal — return the raw fix signal as fallback
            return f"[Debugger unavailable: {e}]\nRaw error: {fix_signal[:500]}"

    def _read_file_snippets(self, modified_files: list, project_path: str, max_lines: int = 60) -> str:
        """Read the first N lines of each modified file for context."""
        snippets = []
        for rel_path in modified_files:
            full_path = os.path.join(project_path, rel_path)
            if not os.path.exists(full_path):
                snippets.append(f"[{rel_path}]: file not found")
                continue
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()[:max_lines]
                content = "".join(lines)
                snippets.append(f"--- {rel_path} ---\n{content}")
            except Exception as e:
                snippets.append(f"[{rel_path}]: could not read ({e})")
        return "\n\n".join(snippets)
