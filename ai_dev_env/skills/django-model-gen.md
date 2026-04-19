# SKILL: Django Model Generation
**Trigger:** task_type == "model-gen"

## Rules (MANDATORY STRICT CONSTRAINTS)
- **Imports:** Always include `from django.db import models`.
- **Fields Types Mapping:** Only use these mappings:
  - string -> `models.CharField(max_length=255)`
  - text -> `models.TextField()`
  - integer -> `models.IntegerField()`
  - decimal -> `models.DecimalField(max_digits=10, decimal_places=2)`
  - boolean -> `models.BooleanField(default=False)`
- **Minimal Safe Generation:** ONLY generate the requested fields. DO NOT generate ANY relationships (ForeignKey, ManyToManyField) unless explicitly asked.
- **RESTRICTIONS - DO NOT INCLUDE THE FOLLOWING (INVALID IN DJANGO MODELS):**
  - NEVER use `required=True` in model fields (Django uses `null` and `blank` defaults instead).
  - NO `class Meta: fields = [...]`.
  - NO serializer-specific logic.
  - NO form logic.
- **Methods:** Include a `__str__` method returning the primary identifier field.
- **Admin:** Generate a matching `admin.py` registration.

## Output Format
Return a JSON array of file operations. Use "append" for existing files or "create" for new files.
