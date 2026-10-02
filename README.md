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
`http://localhost:8000/docs`. Esto usa SQLite (`dev.db`) — para correr contra Postgres en
local, ver la sección Docker más abajo.

## Docker (Postgres local, paridad con producción)

```bash
docker compose up --build
```

Levanta dos servicios: `db` (Postgres 16) y `app` (la API/web, corriendo las migraciones de
Alembic automáticamente al arrancar — ver `docker-entrypoint.sh`). Queda en
`http://localhost:8000`, igual que en local. Credenciales de ejemplo en `docker-compose.yml`
(`taekwondo`/`taekwondo` para la DB, `admin`/`admin` para el panel admin) — son solo para
desarrollo local, no usar en producción.

Para correr los tests contra esta Postgres en vez de SQLite (con los contenedores arriba):

```bash
DATABASE_URL="postgresql+psycopg://taekwondo:taekwondo@localhost:5432/taekwondo" pytest -v
```

`docker compose down` para parar (el volumen `pgdata` persiste los datos entre reinicios).

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
- [x] Fase 7 — Docker + docker-compose (Postgres local)
- [ ] Fase 8 — Despliegue (Neon + Render)
- [ ] Fase 9 — Mejoras post-deploy (backlog abierto en [`docs/BACKLOG.md`](docs/BACKLOG.md))

Detalle de cada fase en el plan original y en [`CLAUDE.md`](CLAUDE.md).
