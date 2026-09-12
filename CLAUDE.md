# Contexto para asistentes de IA

Proyecto de portafolio: sistema de torneos de taekwondo en Python/FastAPI, construido por
fases incrementales. Este archivo es lo primero que hay que leer para retomar el trabajo en
cualquier punto intermedio.

## Estado actual

**Fase actual: 2 (CRUD base vía API) recién completada. Próximo paso: Fase 3 (generación de
llaves).** Ver checklist completo en `README.md`.

Modelos en `app/models.py` (SQLAlchemy 2.0, estilo `Mapped`/`mapped_column`): `Club`,
`Athlete`, `Tournament`, `Category`, `Registration`, `Bracket`, `Match`, `RoundScore`.
Migración inicial en `alembic/versions/10c0a6918c73_initial_schema.py`. `alembic/env.py` lee
`DATABASE_URL` desde `app.database` (no desde `alembic.ini`, que queda con un valor dummy sin
usar).

API REST en `app/api/` (un router por entidad: `clubs`, `athletes`, `tournaments`,
`categories`, `registrations`), montada en `app/main.py` bajo `/api/v1/...`. Validaciones de
negocio ya implementadas en `registrations.py`: género del atleta debe coincidir con el de la
categoría (422), no se permite inscripción duplicada del mismo atleta en la misma categoría
(409). Tests en `tests/` usan SQLite en memoria (`StaticPool`, ver `tests/conftest.py`) — no
tocan `dev.db`. 15 tests pasando (`pytest -v`).

Nota de Python: en `app/schemas.py` se usa `import datetime` + `datetime.date` en vez de
`from datetime import date`, porque un campo Pydantic llamado `date` con un tipo también
llamado `date` y valor por defecto se pisa a sí mismo (la asignación ocurre antes que la
evaluación de la anotación) — ver el commit de fase 2 si hace falta el detalle.

## Entorno

- Se desarrolla dentro de **WSL (Ubuntu-22.04)**, nunca en Windows nativo ni en `/mnt/c/...`.
- Python 3.10+ (no asumir 3.12, no está instalado en esta máquina y no hace falta).
- Docker todavía no está habilitado en esta distro (falta activar la integración WSL de
  Docker Desktop) — no es necesario hasta la fase 7.
- Un commit por sub-paso verificado, no uno gigante por fase. Mensajes estilo
  `feat:`/`fix:`/`chore:`.

## Reglas de extensibilidad (no romper)

- `Category.discipline` existe aunque hoy solo se use `SPARRING`. No eliminar el campo ni
  asumir que solo habrá un valor posible.
- `Match`/`RoundScore` son específicos de combate (sparring). Si se agregan Poomsae o
  Rompimiento, **no reusar estas tablas** — crear modelos de resultado propios
  (`PoomsaeScore`, `BreakingAttempt`) que cuelguen de `Category`/`Registration`.
- No hardcodear tablas oficiales de peso por cinturón/edad/género. `Category.weight_label`
  es texto libre que define el admin al crear la categoría — las tablas de peso varían por
  federación y no son parte del problema que este proyecto resuelve.
- `Club` es una entidad propia (`id`, `name`). `Athlete.club_id` es una FK obligatoria — el
  club es un atributo fijo del atleta, no algo que se elija por torneo/inscripción.
- `RoundScore` no tiene penalizaciones todavía; si se agregan, es aditivo (columnas nuevas),
  no un rediseño.

## Decisiones de arquitectura

Ver [`docs/DECISIONS.md`](docs/DECISIONS.md) para el porqué de: Jinja2 en vez de SPA,
Render+Neon en vez de Railway/Fly.io, desarrollo dentro de WSL, y las reglas de arriba.

## Verificación esperada en cada fase

- `pytest -v` pasa.
- Se puede levantar el server y probar manualmente vía `/docs` (Swagger) o navegador.
- No romper lo verificado en fases anteriores (correr toda la suite, no solo los tests
  nuevos).
