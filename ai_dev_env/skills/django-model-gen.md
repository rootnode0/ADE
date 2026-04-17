# SKILL: Django Model Generation
**Trigger:** task_type == "model-gen"

## Rules
- **Imports:** Always include `from django.db import models`.
- **Standard Fields:** Every model MUST have:
  - `created_at = models.DateTimeField(auto_now_add=True)`
  - `updated_at = models.DateTimeField(auto_now=True)`
- **Methods:** Include a `__str__` method returning the primary identifier.
- **Metadata:** Include `class Meta:` with `ordering = ["-created_at"]`.
- **Admin:** Generate a matching `admin.py` registration with `list_display`.

## Output Format
Return a JSON array of file operations. Use "append" for existing models.py or "create" for new apps.
