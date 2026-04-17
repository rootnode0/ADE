# SKILL: Django REST API Generation
**Trigger:** task_type == "api-gen"

## Rules
- **Stack:** Generate Serializer -> ViewSet -> URL wiring.
- **Serializers:** Use `serializers.ModelSerializer`. Explicitly list `fields`, never use `__all__`.
- **Views:** Use `viewsets.ModelViewSet` with `permission_classes = [permissions.AllowAny]` for dev.
- **URLs:** Use `rest_framework.routers.DefaultRouter`.
- **Wiring:** Ensure the app's `urls.py` is included in the main `config/urls.py`.

## Output Format
JSON array targeting `serializers.py`, `views.py`, and `urls.py`.
