# SKILL: Precision Bug Fixing
**Trigger:** task_type == "bug-fix"

## Rules
- **Minimalism:** Fix ONLY the reported error. Do not refactor surrounding code.
- **Validation:** Ensure the fix doesn't break existing type hints.
- **Strategy:** Prefer adding guard clauses (if/else) over changing architecture.
- **Reasoning:** The `reasoning` field in the JSON must explain WHY the fix works.
