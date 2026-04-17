# SKILL: FastAPI Endpoint Generation
**Trigger:** project_type == "fastapi"

## Rules
- **Schemas:** Use Pydantic v2 `BaseModel`.
- **Async:** All route handlers must be `async def`.
- **DI:** Use FastAPI `Depends` for database sessions.
