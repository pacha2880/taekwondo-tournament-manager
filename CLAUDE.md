# Contexto para asistentes de IA

Proyecto de portafolio: sistema de torneos de taekwondo en Python/FastAPI, construido por
fases incrementales. Este archivo es lo primero que hay que leer para retomar el trabajo en
cualquier punto intermedio.

## Estado actual

**Fase actual: 3 (generación de llaves) recién completada, pendiente de revisión del
usuario — no está commiteada. Próximo paso: Fase 4 (carga de resultados y propagación de
ganador).** Ver checklist completo en `README.md`.

Modelos en `app/models.py` (SQLAlchemy 2.0, estilo `Mapped`/`mapped_column`): `Club`,
`Athlete`, `Tournament`, `Category`, `Registration`, `Bracket`, `Match`, `RoundScore`.
Migración inicial en `alembic/versions/10c0a6918c73_initial_schema.py`. `alembic/env.py` lee
`DATABASE_URL` desde `app.database` (no desde `alembic.ini`, que queda con un valor dummy sin
usar).

API REST en `app/api/` (un router por entidad: `clubs`, `athletes`, `tournaments`,
`categories`, `registrations`), montada en `app/main.py` bajo `/api/v1/...`. Validaciones de
negocio ya implementadas en `registrations.py`: género del atleta debe coincidir con el de la
categoría (422), peso del atleta dentro de `min_weight`/`max_weight` de la categoría si están
definidos (422), no se permite inscripción duplicada del mismo atleta en la misma categoría
(409) ni en más de una categoría del mismo torneo (409). `Category` tiene además
`min_weight`/`max_weight` opcionales (float) junto al `weight_label` de texto libre, con
validación `min_weight <= max_weight` / `min_age <= max_age` en `schemas.py`. Tests en
`tests/` usan SQLite en memoria (`StaticPool`, ver `tests/conftest.py`) — no tocan `dev.db`.
19 tests pasando (`pytest -v`).

Generación de llaves en `app/services/brackets.py`, expuesta en `app/api/brackets.py`
(`POST`/`GET /api/v1/categories/{id}/bracket`). Lógica pura sin DB (`next_power_of_two`,
`seeding_order`, `build_first_round_slots`) separada de la persistencia
(`generate_bracket`) para poder testear el algoritmo de byes sin sesión de SQLAlchemy —
ver `tests/test_brackets.py` (incluye un test parametrizado que verifica, para n=2..19 y 20
semillas aleatorias por n, que nunca hay dos byes en el mismo cruce de la ronda 1).
`advance_winner(db, match)` en el mismo módulo propaga el ganador de un match a la
siguiente ronda; la reutiliza tanto la resolución automática de byes como (en la fase 4) el
cierre de un combate real. 62 tests pasando en total.

Nota de Python: en `app/schemas.py` se usa `import datetime` + `datetime.date` en vez de
`from datetime import date`, porque un campo Pydantic llamado `date` con un tipo también
llamado `date` y valor por defecto se pisa a sí mismo (la asignación ocurre antes que la
evaluación de la anotación) — ver el commit de fase 2 si hace falta el detalle.

## Entorno

- Se desarrolla dentro de **WSL (Ubuntu-22.04)**, nunca en Windows nativo ni en `/mnt/c/...`.
- Python 3.10+ (no asumir 3.12, no está instalado en esta máquina y no hace falta).
- Docker todavía no está habilitado en esta distro (falta activar la integración WSL de
  Docker Desktop) — no es necesario hasta la fase 7.
- **No hacer `git commit` ni `git push` salvo que el usuario lo pida explícitamente en ese
  momento.** Implementar y verificar (tests, server manual) y dejar los cambios sin stagear;
  el usuario revisa antes de decidir si se commitea. Cuando sí lo pida, un commit por
  sub-paso verificado (no uno gigante por fase), mensajes estilo `feat:`/`fix:`/`chore:`.

## Estilo de código

- Minimizar comentarios: priorizar código autodocumentado (nombres claros de variables y
  funciones) antes que explicar con un comentario. Solo comentar cuando aporta algo que el
  código en sí no puede transmitir (el porqué de una decisión no obvia, una referencia a un
  bug/limitación externa, una propiedad matemática no evidente a simple vista) — no repetir
  en palabras lo que ya dice el código.
- Después de implementar algo, hacer una segunda pasada rápida (de pasada, sin analizar a
  fondo ni frenar el flujo de trabajo) buscando si hay una versión más simple o coherente con
  el resto del código. No sacrificar velocidad por esto — si no aparece nada obvio en esa
  pasada rápida, seguir adelante.

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
- Los archivos `.http` en `http/` (ver más abajo) siguen funcionando de punta a punta.
- No romper lo verificado en fases anteriores (correr toda la suite, no solo los tests
  nuevos).

## Archivos `.http` para pruebas manuales

`http/` tiene un archivo por router (`clubs.http`, `athletes.http`, `tournaments.http`,
`categories.http`, `registrations.http`), pensado para la extensión **REST Client** de
VS Code con el servidor (`uvicorn app.main:app --reload`) corriendo en local. Cada archivo es
autocontenido: crea sus propias dependencias (por ejemplo `athletes.http` crea su propio club
antes del atleta) usando el encadenado de variables de REST Client
(`# @name` + `{{nombre.response.body.$.campo}}`), igual que las fixtures de
`tests/conftest.py` encadenan `club → athlete` y `tournament → category`. No reemplazan a
`pytest` — son para "ir probando a mano" mientras se desarrolla, con algunos casos de error
representativos (404/409/422) además del camino feliz.

Al agregar funcionalidad nueva (fase 3 en adelante: brackets, matches, round_scores), sumar
el archivo `.http` correspondiente siguiendo el mismo patrón, en vez de dejar que estos
archivos queden desactualizados.
