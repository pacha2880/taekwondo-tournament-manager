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
- [ ] Fase 4 — Carga de resultados y propagación de ganador
- [ ] Fase 5 — Pantalla pública
- [ ] Fase 6 — Pantalla admin
- [ ] Fase 7 — Docker + docker-compose (Postgres local)
- [ ] Fase 8 — Despliegue (Neon + Render)

Detalle de cada fase en el plan original y en [`CLAUDE.md`](CLAUDE.md).
