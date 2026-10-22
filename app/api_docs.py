"""Texto de la documentación de la API (`/docs`, `/redoc`, `/openapi.json`).

Va en español porque la consume gente ajena al proyecto. Los identificadores (rutas, campos,
valores de enums) quedan en inglés. Los nombres de los grupos son parte del contrato: muchos
generadores de clientes los usan para nombrar clases, así que no se renombran sin avisar.
"""

from app.schemas import ErrorResponse

TAG_AUTH = "Autenticación"
TAG_CLUBS = "Clubes"
TAG_ATHLETES = "Atletas"
TAG_TOURNAMENTS = "Torneos"
TAG_CATEGORIES = "Categorías"
TAG_REGISTRATIONS = "Inscripciones"
TAG_BRACKETS = "Llaves"
TAG_MATCHES = "Combates"
TAG_SYSTEM = "Sistema"

API_DESCRIPTION = """
API para gestionar torneos de taekwondo (modalidad combate): clubes, atletas, torneos, categorías,
inscripciones, llaves de eliminación simple con pases directos (*byes*) y resultados round por round.

## Autenticación

Las lecturas de **torneos, categorías, clubes, llaves y combates son públicas**. Todo lo que escribe
(`POST`/`PATCH`) y las lecturas de **atletas e inscripciones** (llevan fecha de nacimiento y peso, y
hay menores) requieren un token:

1. `POST /api/v1/auth/login` con `username` y `password` como formulario devuelve un token JWT que
   dura **8 horas**. En esta página, el botón **Authorize** hace este paso por ti.
2. Envíalo en cada petición protegida: `Authorization: Bearer <token>`.

## Errores

Los errores de negocio responden `{"detail": "mensaje en español"}`. Códigos usados: `400` (la
petición no es válida en el estado actual), `401` (falta el token, es inválido o venció), `404` (no
existe), `409` (choca con datos existentes) y `422` (no cumple una regla de negocio, o el cuerpo no
tiene el formato esperado; en este último caso `detail` es una lista con el formato estándar de
FastAPI: `[{"loc": [...], "msg": "...", "type": "..."}]`).

## Valores en inglés

Las rutas, los nombres de los campos y los valores de los enums están en inglés (`male`,
`in_progress`, `bye`…). Cada campo y cada enum explica su significado en español.

## Antes de usarla

- En el plan gratis del servidor, el primer request tras un rato inactivo puede tardar 30-50 segundos.
- Mientras la versión sea `0.x` puede haber cambios incompatibles entre versiones. Cada uno se
  registra en el [CHANGELOG](https://github.com/pacha2880/taekwondo-tournament-manager/blob/main/CHANGELOG.md).
"""

TAGS_METADATA = [
    {"name": TAG_AUTH, "description": "Inicio de sesión para obtener el token que piden los endpoints protegidos."},
    {"name": TAG_TOURNAMENTS, "description": "Torneos y su estado (`draft`, `in_progress`, `finished`)."},
    {
        "name": TAG_CATEGORIES,
        "description": "Categorías de un torneo, definidas por edad, género, cinturón y peso.",
    },
    {"name": TAG_CLUBS, "description": "Clubes a los que pertenecen los atletas."},
    {
        "name": TAG_ATHLETES,
        "description": "Atletas. Incluyen fecha de nacimiento y peso, así que requieren token.",
    },
    {
        "name": TAG_REGISTRATIONS,
        "description": "Inscripción de un atleta en una categoría de un torneo. Valida género, peso y duplicados.",
    },
    {
        "name": TAG_BRACKETS,
        "description": "Llave de eliminación simple de una categoría, sorteada al azar, con pases directos si hace falta.",
    },
    {"name": TAG_MATCHES, "description": "Combates de una llave y carga de resultados round por round."},
    {"name": TAG_SYSTEM, "description": "Estado del servicio."},
]

_UNAUTHORIZED = "No autenticado: falta el token de acceso, es inválido o venció."


def errors(codes: dict[int, str] | None = None, *, auth: bool = False) -> dict:
    """Respuestas de error documentadas de un endpoint.

    `auth=True` agrega el 401. El 422 no se declara acá: FastAPI ya documenta el de validación de
    formato, y las reglas de negocio que responden 422 se explican en la descripción del endpoint.
    """
    merged = {401: _UNAUTHORIZED} if auth else {}
    merged.update(codes or {})
    assert 422 not in merged, "el 422 se documenta en la descripción del endpoint"
    return {code: {"model": ErrorResponse, "description": text} for code, text in merged.items()}
