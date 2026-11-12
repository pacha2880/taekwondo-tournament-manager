# Contexto para asistentes de IA

Sistema de torneos de taekwondo (FastAPI): API `/api/v1`, pantalla admin y páginas públicas. El porqué de
cada decisión no obvia está en `docs/DECISIONS.md`, el roadmap en `docs/BACKLOG.md`, la guía para quien
consume la API en `docs/API.md`, y la instalación y el versionado en `README.md`. Las reglas de cada área
están en `.claude/rules/` y se cargan solas al tocar esos archivos.

## Verificación de cada cambio

1. `.venv/bin/pytest -q` contra SQLite, siempre y con toda la suite.
2. Si cambió algo visible en pantallas: levantar el server (`uvicorn app.main:app --reload`) y mirarlo.

Nada más en el día a día. Al terminar un sub-paso, seguir el skill `documentar-cambio`.

- Postgres lo corre el CI en el PR `dev` → `main` (job `pytest-postgres`, requerido para mergear). En local
  solo como respaldo de `/release`.
- **Si se corre Postgres en local, siempre contra la base `taekwondo_test`, nunca `taekwondo`**: la suite
  hace `drop_all` y ya borró una vez los datos de desarrollo (un hook lo bloquea; ver `README.md`).
- Las migraciones las valida el servicio `dev` de Render, que las corre contra Neon en cada push a `dev`.

## Contexto que no está en el repo

- Producción: https://taekwondo-tournament-manager.onrender.com (Render + Neon, Ohio), despliega desde
  `main`. El servicio `dev` de Render despliega la rama `dev` contra una rama `dev` de Neon.
- Quedan datos de demo en la base de **producción** (club "Club Demo Cochabamba", torneo
  "Copa Cochabamba DEMO"); el admin no tiene botón de borrar — limpieza solo por SQL desde el
  panel de Neon.
- Un amigo del usuario construye un frontend separado (otra tecnología) contra esta API: la API es un
  producto, con su propia autenticación, CORS y documentación. Un cambio de contrato va al CHANGELOG y a
  `docs/API.md`.

## Reusar, no duplicar

- Nombres de atletas de una llave o combate: `resolve_athlete_names` (`app/services/brackets.py`).
- Regla de género/peso de un atleta contra una categoría: `category_mismatch` (`app/services/eligibility.py`).
- Reglas de estado del torneo: `app/api/lifecycle.py`. El estado cambia solo con `POST .../start` y
  `.../finish`, nunca con `PATCH`.
- Formato de CI: solo `CI_REGEX` de `app/schemas.py`.

## Idioma

- Texto visible para el usuario en español: páginas, admin, errores de la API y documentación de `/docs`.
- Identificadores en inglés: rutas, campos y valores de enums (se guardan en inglés a propósito; en
  plantillas se traducen con `|es_label`). Comentarios de código y mensajes de commit pueden ir en inglés.

## Reglas de extensibilidad (no romper)

- `Category.discipline` existe aunque hoy solo se use `SPARRING`. No eliminar el campo ni
  asumir que solo habrá un valor posible.
- `Match`/`RoundScore` son específicos de combate (sparring). Si se agregan Poomsae o
  Rompimiento, **no reusar estas tablas** — crear modelos de resultado propios
  (`PoomsaeScore`, `BreakingAttempt`) que cuelguen de `Category`/`Registration`.
- No hardcodear tablas oficiales de peso por cinturón/edad/género. `Category.weight_label`
  es texto libre que define el admin al crear la categoría — las tablas de peso varían por
  federación y no son parte del problema que este proyecto resuelve.
- `Athlete.ci` es opcional (hay niños sin CI) y único cuando se informa.
- `Club` es una entidad propia (`id`, `name`). `Athlete.club_id` es una FK obligatoria — el
  club es un atributo fijo del atleta, no algo que se elija por torneo/inscripción.
- `RoundScore` no tiene penalizaciones todavía; si se agregan, es aditivo (columnas nuevas),
  no un rediseño.
- Una regla de negocio se extrae en cuanto aparece la segunda copia. Nunca renombrar algo ya publicado
  en la API.

## Git

- **Commitear, pushear o taggear solo ante una orden directa y actual** ("commiteá", "hacé el commit").
  Frases sobre cómo organizar el trabajo ("un commit por cada uno", "procedamos") no son una orden:
  implementar, verificar, dejar todo sin stagear y preguntar. Cómo commitear: skill `commit`.
- Trabajar en `dev`; a `main` se llega solo con el PR que abre y mergea el usuario (el merge es el deploy).
- Tags `vX.Y.Z`: los crea el usuario; nunca mover ni borrar uno publicado. Procedimiento: `/release`.

## Entorno

- WSL Ubuntu-22.04 (nunca `/mnt/c/...`), Python 3.10 (no asumir 3.12), `docker compose` sin guion.
- Si Docker no resuelve DNS (pasa tras un `wsl --shutdown`):
  `sudo bash -c 'echo "nameserver 8.8.8.8" > /etc/resolv.conf'`.
