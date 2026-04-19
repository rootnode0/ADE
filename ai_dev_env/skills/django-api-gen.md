# SKILL: Django API Generation
**Trigger:** task_type == "api-gen"

## Rules (MANDATORY STRICT CONSTRAINTS)
- **Models:** If `<app>/models.py` is provided in context and is empty or missing the target entity, you MUST first create a base model for that entity.
- **Serializers:** Always create a ModelSerializer for the target entity. Include `from rest_framework import serializers`.
- **Views:** Always create a ViewSet (e.g. `ModelViewSet`). Include `from rest_framework import viewsets`.
- **Routing:** Always create standard router configurations using `from rest_framework.routers import DefaultRouter`.
- **Target Files:** You MUST generate or update `<app>/models.py`, `<app>/serializers.py`, `<app>/views.py`, and `<app>/urls.py` in a single pass.
- **Scope:** Do NOT attempt to modify `settings.py` or any project-level `urls.py`. Your responsibility ends at the app-level files.
- **Consistency:** Ensure that every ViewSet class referenced in `urls.py` is defined in `views.py`, and every Serializer class referenced in `views.py` is defined in `serializers.py`.
- **Imports:** Use relative imports for local app modules (e.g., `from .views import ...`).

## Validation & Constraints
- **Model Fields:** NEVER use `required=True` in Django model fields. Use `null=False, blank=False` (default) if a field is required, or `null=True, blank=True` if it is optional.
- **Field Options:** Only use standard Django field options (`max_length`, `default`, `unique`, `verbose_name`, etc.).

## Common Pitfalls (TO AVOID)
- **RuntimeError:** "Model class ... doesn't declare an explicit app_label". This happens if the app is not in `INSTALLED_APPS`.
- **TypeError:** "Field.__init__() got an unexpected keyword argument 'required'".

## Output Format
Return a JSON array of file operations. Use "create" or "full_replace" for new API files.
