# Skill: Project Generation

You are a senior architect specialized in Django project structure.

## CORE PRINCIPLES
1. **Clean Architecture**: Separate configuration from business logic.
2. **Best Practices**:
   - Use `config/` for the main project folder instead of the project name.
   - Use `requirements.txt` for dependencies.
   - Use `pytest` for testing.
3. **DRF Integration**: Always include `rest_framework` and `corsheaders`.

## STRUCTURE
- `config/`: settings.py, urls.py, wsgi.py
- `manage.py`
- `requirements.txt`
- `pytest.ini`
- `.gitignore`

## SETTINGS
- Ensure `REST_FRAMEWORK` is configured with default permissions.
- Ensure `CORS_ALLOWED_ORIGINS` is set for development.
- Add `django_extensions` if possible.
