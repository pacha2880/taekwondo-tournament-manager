---
paths:
  - "app/api/**"
  - "app/api_docs.py"
  - "app/schemas.py"
  - "tests/test_api_*.py"
---
# Endpoints de `/api/v1`

- **Auth**: por defecto `dependencies=ADMIN_ONLY`. Una lectura pública a propósito va también en
  `PUBLIC_ENDPOINTS` de `tests/test_api_auth.py`. **Nunca público un endpoint que devuelva fecha de
  nacimiento o peso** (hay menores); para mostrar inscritos sin token, `list_registrants` (solo nombre y club).
- **Docs** (`tests/test_api_docs.py` falla si falta algo):
  - `summary`, `description`, `tags=[TAG_...]` de `app/api_docs.py`.
  - `responses=errors({...}, auth=True/False)` con los errores reales (401 si pide token, 404 si tiene
    parámetro de ruta); el 422 de negocio se explica en la descripción, no en `errors()`.
  - Campo nuevo de `app/schemas.py`: `Field(description=...)` en la clase `*Base` (los de solo lectura,
    como `id` o `has_bracket`, en la `*Read`). Enum nuevo: docstring en español.
  - `operationId` = nombre de la función, único entre routers.
- Textos de `/docs` (summary, descripciones, tags) y mensajes de `HTTPException` en español; rutas, campos y
  valores de enums en inglés. Los nombres de los tags (Torneos, Categorías, Atletas, Clubes, Inscripciones,
  Llaves, Combates, Autenticación, Sistema) son contrato: los usan generadores de clientes, no renombrarlos.
- Reglas de estado del torneo: en `app/api/lifecycle.py` (409), no repetidas en cada endpoint.
- Para inventariar rutas usar `app.openapi()["paths"]`: con FastAPI 0.141 los routers incluidos quedan
  anidados y `app.routes` no los lista.
