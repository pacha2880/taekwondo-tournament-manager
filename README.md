# Torneos de Taekwondo

Sistema de gestión de torneos de taekwondo: inscripción de atletas, generación aleatoria de
llaves (con byes cuando el número de inscritos no es potencia de 2), categorías por edad,
género, cinturón (colores desde amarillo, y negro con su propia categoría absoluta) y peso,
carga de resultados de combate por round/puntaje, y dos pantallas: una pública de solo
lectura y una de administración.

Pensado para poder extenderse más adelante a otras disciplinas (formas/poomsae,
rompimiento) sin rehacer lo ya construido — ver [`docs/DECISIONS.md`](docs/DECISIONS.md).

## Stack

- Python 3.10+, FastAPI, SQLAlchemy 2.0 + Alembic, Pydantic v2
- Jinja2 (server-side rendering, sin frontend separado)
- SQLite en desarrollo, PostgreSQL en producción (mismo código, cambia `DATABASE_URL`)
- pytest + httpx para tests
- Docker + docker-compose (a partir de la fase 7) para Postgres local y paridad con producción
- Despliegue: [Neon](https://neon.tech) (Postgres gratis) + [Render](https://render.com) (web service gratis)

## Cómo correr en local

Este proyecto se desarrolla dentro de **WSL** (Ubuntu). Desde una terminal de WSL, en la
carpeta del proyecto:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

La API queda en `http://localhost:8000` y la documentación interactiva en
`http://localhost:8000/docs`.

## Pantallas

- **Pública** (sin login): `http://localhost:8000/` — lista de torneos, categorías y llaves.
- **Admin**: `http://localhost:8000/admin` — pide login. Usuario/contraseña salen de las
  variables de entorno `ADMIN_USERNAME`/`ADMIN_PASSWORD` (ver [`.env.example`](.env.example));
  si no se configuran, el valor por defecto es `admin`/`admin`. Cambiá `SECRET_KEY` también
  antes de desplegar — firma la cookie de sesión.

## Tests

```bash
pytest -v
```

## Probar la API manualmente

Con el servidor corriendo (`uvicorn app.main:app --reload`), hay dos formas de probar los
endpoints a mano, además de los tests automáticos:

- **Swagger** en `http://localhost:8000/docs`.
- **Archivos `.http`** en [`http/`](http/) (uno por entidad: `clubs.http`, `athletes.http`,
  `tournaments.http`, `categories.http`, `registrations.http`), pensados para la extensión
  [REST Client](https://marketplace.visualstudio.com/items?itemName=humao.rest-client) de
  VS Code — abrí el archivo y hacé click en "Send Request" arriba de cada petición. Cada
  archivo crea sus propias dependencias (club, torneo, etc.) antes de la petición principal,
  así que se pueden correr de punta a punta sin copiar IDs a mano.

## Estado del proyecto

- [x] Fase 0 — Esqueleto (git, estructura, docs)
- [x] Fase 1 — Modelo de datos + migraciones
- [x] Fase 2 — CRUD base vía API
- [x] Fase 3 — Generación de llaves
- [x] Fase 4 — Carga de resultados y propagación de ganador
- [x] Fase 5 — Pantalla pública
- [x] Fase 5.5 — Traducción de enums al español + guardrail para futuras plantillas
- [x] Fase 6 — Pantalla admin
- [ ] Fase 7 — Docker + docker-compose (Postgres local)
- [ ] Fase 8 — Despliegue (Neon + Render)
- [ ] Fase 9 — Mejoras post-deploy (backlog abierto, ver más abajo)

Detalle de cada fase en el plan original y en [`CLAUDE.md`](CLAUDE.md).

### Fase 9 — backlog de mejoras (después del deploy)

Cosas que se nos van ocurriendo pero que deliberadamente no bloquean llegar a producción.
Se implementan después de la Fase 8, priorizadas según convenga en ese momento:

- Auto-refresh en vivo de la pantalla pública (polling con htmx), en vez de recargar manual.
- Colores distintos por estado de torneo (`TournamentStatus`) en los badges — hoy "Borrador"/
  "En curso"/"Finalizado" se ven todos igual (gris). Mismo patrón que ya existe para
  `MatchStatus` (`match_status_badge_class` en `app/web/labels.py`): agregar algo como
  `tournament_status_badge_class`.
- Ocultar los torneos en estado `DRAFT` de la lista principal de la pantalla pública (`/`).
  Por ahora solo la lista — queda abierta la pregunta de si también hay que bloquear el
  acceso directo a `/torneos/{id}`/`/categorias/{id}` de un torneo en borrador (hoy no
  miran `status` para nada), para no depender de "seguridad por oscuridad".
- Darle comportamiento real al estado del torneo (`TournamentStatus`), no solo cosmético:
  - No permitir cargar resultados de rounds (`record_round` en `app/services/scoring.py`)
    mientras el torneo está en `DRAFT` — mensaje pidiendo pasar el torneo a "en curso" primero.
  - Solo permitir crear categorías (`create_category` en `app/api/categories.py`) mientras el
    torneo está en `DRAFT` — no "bloqueado en en curso", sino "solo permitido en DRAFT", para
    cubrir también el caso de un torneo ya `FINISHED`.
  - `FINISHED` es inmutable una vez alcanzado — ningún otro cambio de estado permitido después
    (ni volver a `DRAFT`/`IN_PROGRESS`, ni ningún otro campo del torneo). En el admin, el form
    que pasa el torneo a `FINISHED` necesita un popup de confirmación avisando que es
    irreversible, antes de mandar el cambio.
  - Solo se puede mover a `FINISHED` cuando **todos** los matches de **todas** las categorías
    del torneo llegaron a un estado terminal. Ojo con el detalle: un bye nunca pasa a
    `MatchStatus.FINISHED` (se queda en `BYE` para siempre, ver `app/models.py`), así que la
    condición es `status in (FINISHED, BYE)` para cada match, no `status == FINISHED` a secas
    — si no, un bracket con cualquier bye bloquearía el torneo para siempre. Falta decidir qué
    pasa con una categoría que nunca generó bracket (¿bloquea cerrar el torneo, o se ignora?).
  - Estas validaciones viven del lado de la API (no solo del admin), así que aplican también
    a cualquier consumidor directo de `/api/v1/...`, consistente con el resto del proyecto.
- Permitir editar un round ya cargado. No es trivial: si es el round que cerró el combate,
  hay que reabrirlo (volver a `pending`, revertir `winner_id`) y, si el ganador ya se propagó
  a la siguiente ronda (`advance_winner`), también revertir esa propagación — puede afectar
  en cascada otro combate ya en curso.
- En el formulario de carga de resultados del admin, no dejar el número de round libre —
  calcularlo y mostrarlo fijo (rounds ya cargados de ese combate + 1) para que no se pueda
  cargar un round fuera de orden. Sumar un popup de confirmación antes de guardar, aclarando
  que hoy no se puede editar después (hasta que se resuelva el punto anterior).
- De forma más general: cada vez que se crea algo desde el admin (club, atleta, torneo,
  categoría, inscripción, llave, round), mostrar un popup de confirmación con los datos antes
  de mandar el form — no necesariamente aclarando que no se puede editar después, solo para
  que el usuario confirme lo que está a punto de crear.
- Campo CI (documento de identidad) único por atleta.
- Editar atleta (hoy solo se puede crear).
- Buscar atleta por CI o por nombre en la pantalla admin de atletas.
- Editar club (a confirmar si hace falta).
- En el `<select>` de "Inscribir atleta" de la pantalla admin de categoría
  (`app/web/admin/category_workspace.py::_category_detail_context`, variable `all_athletes`),
  filtrar los atletas que ya están inscritos en esa categoría — hoy aparecen todos
  (`select(Athlete).order_by(Athlete.name)`, sin excluir a los de `registrations`), lo que
  permite intentar inscribir a alguien ya inscrito y chocar con el 409 en vez de no ofrecerlo
  como opción directamente.
- En la navbar del admin, agregar un botón "Torneos" a la izquierda de "Clubes" y "Atletas"
  (hoy solo se llega al dashboard de torneos por el link del brand).
- Si algún día se construye un frontend separado (SPA) que consuma solo `/api/v1/...`:
  analizar si hace falta un endpoint agregado para la página de detalle de categoría. Hoy
  `_category_detail_context` (`app/web/admin/category_workspace.py`) junta categoría +
  torneo + inscripciones + todos los atletas + bracket en una sola función Python; un
  frontend desacoplado tendría que hacer 5 requests HTTP separados para lo mismo. No crear
  el endpoint agregado todavía — no hay frontend separado hoy, sería especular sobre un caso
  de uso que no existe.
- (agregar acá cualquier otra idea que surja durante el desarrollo)
