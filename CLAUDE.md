# Contexto para asistentes de IA

Proyecto de portafolio: sistema de torneos de taekwondo en Python/FastAPI, construido por
fases incrementales. Este archivo es lo primero que hay que leer para retomar el trabajo en
cualquier punto intermedio.

## Estado actual

**Fase actual: 8 (despliegue en Neon + Render) completada — la app está en producción en
https://taekwondo-tournament-manager.onrender.com.** Render con runtime Docker (plan gratis,
región Ohio), base de datos en Neon (Postgres, endpoint directo, región Ohio). Verificado en
producción con un flujo completo hecho por el admin: club, 7 atletas, torneo, categoría,
inscripciones, llave (7 atletas = 1 pase directo), todos los combates hasta la final con
desempates, torneo pasado a "Finalizado" y la pantalla pública mostrando el resultado. Esos
datos de demo (club "Club Demo Cochabamba", torneo "Copa Cochabamba DEMO") **siguen en la
base de producción**; el admin no tiene botón de borrar, así que cualquier limpieza se hace
con SQL desde el panel de Neon. Próximo paso: Fase 9, el backlog de `docs/BACKLOG.md`, con el
orden de versiones ya aprobado (0.2.0 en adelante); quedan decisiones pendientes del usuario,
anotadas al principio de ese archivo. Ver checklist completo en `README.md`.

**Versionado (SemVer).** Versión actual `0.1.0` en `app/version.py` (única fuente de verdad;
se muestra en la esquina de cada página vía `templates.env.globals["app_version"]` en
`app/web/templating.py`, y en `/health`). Al liberar una versión: subir `__version__`, mover
`[Unreleased]` de `CHANGELOG.md` a la sección nueva (`tests/test_version.py` falla si no
coinciden), y el tag `vX.Y.Z` se crea según las reglas de la sección **Entorno** más abajo
(workflow de git) — ver también la sección **Versionado** del `README.md`. Regla dentro de `0.x`: las migraciones de Alembic **solo agregan** (columnas
nuevas opcionales, nunca borrar ni renombrar), para que volver al tag anterior siga
funcionando sobre una base ya migrada. Hay un único entorno de plantillas compartido,
`app/web/templating.py` (filtros `es_label`/`match_status_badge_class` y la versión); los
módulos públicos y de admin lo importan de ahí en vez de crear el suyo.

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
siguiente ronda; la reutiliza tanto la resolución automática de byes como el cierre de un
combate real en `app/services/scoring.py`.

Carga de resultados en `app/services/scoring.py` (`record_round`), expuesta en
`app/api/matches.py` (`GET /api/v1/matches/{id}`, `POST /api/v1/matches/{id}/rounds`). Un
round no puede terminar en empate (422); no se puede cargar un round si el combate no tiene
ambos atletas definidos todavía (400, pasa con matches de ronda 2+ que esperan otro combate)
ni si ya está `FINISHED` (409); número de round duplicado también es 409. El combate se
marca `FINISHED` y dispara `advance_winner` en cuanto un atleta llega a
`category.rounds_to_win` rounds ganados — no antes, así que un empate 1-1 en un "mejor de 3"
deja el combate `pending` esperando el round de desempate. `register_n_athletes` en
`tests/conftest.py` es un fixture-factory compartido entre `test_api_brackets.py` y
`test_api_matches.py` para no duplicar el helper de inscribir N atletas.

Pantalla pública en `app/web/public.py` (Jinja2, templates en `app/templates/`, Bootstrap 5
vía CDN en `base.html`, sin build step). Tres rutas siguiendo la jerarquía de datos: `/`
(lista de torneos), `/torneos/{id}` (categorías), `/categorias/{id}` (llave agrupada por
ronda + resultados). El bracket se muestra como lista de texto por ronda, no como árbol
visual — ver `docs/DECISIONS.md` (entrada 2026-09-22) para el porqué de cada decisión de
esta fase, incluyendo que el auto-refresh en vivo queda anotado como backlog en la Fase 9
(post-deploy), no implementado todavía.

**Decisión revisada**: `MatchRead` (`app/schemas.py`) ya no expone solo ids —
`athlete_red_name`/`athlete_blue_name`/`winner_name` se agregaron porque, en la práctica, el
100% de los consumidores (pantalla pública, admin, y la propia API) necesitaban resolver esos
nombres por su cuenta. La resolución batch (evita N+1 queries) vive en una sola función,
`resolve_athlete_names(db, matches)` en `app/services/brackets.py`, reusada por
`app/api/brackets.py`, `app/api/matches.py`, `app/web/public.py` y
`app/web/admin/category_workspace.py` — ninguno de los 4 vuelve a resolver nombres por su
cuenta.

Fase 5.5: las plantillas usaban `.value` directo de los enums, mostrando texto en inglés
("draft", "male", "bye"...). Se centralizó la traducción en `app/web/labels.py`
(`es_label` y `match_status_badge_class`, registrados como filtros Jinja en
`app/web/public.py`) — ver la sección **Idioma** más arriba para la regla completa y el
guardrail de test.

Pantalla admin en `app/web/admin.py` (prefijo `/admin`), templates en
`app/templates/admin/`. Login por sesión (`SessionMiddleware` de Starlette, cookie firmada
con `SECRET_KEY`) contra `ADMIN_USERNAME`/`ADMIN_PASSWORD` de variables de entorno — un solo
usuario, sin roles. `require_admin` (dependencia de FastAPI) protege cada ruta; si no hay
sesión, lanza `NotAuthenticated`, capturada por un `@app.exception_handler` en `main.py` que
redirige a `/admin/login` (no devuelve un 401 plano).

Decisión clave de esta fase: **los handlers de `app/web/admin.py` llaman directo a las
funciones de `app/api/*.py`** (ej. `create_club_api = create_club` importado de
`app/api/clubs.py`) en vez de reimplementar la validación de negocio en el admin. Son
funciones Python normales — `Depends(get_db)` es solo un default que se ignora al pasar `db`
explícito — así que se puede invocar `create_club_api(ClubCreate(...), db)` directo, sin pasar
por HTTP. Esto evita duplicar reglas como "no inscripción duplicada" o "el peso debe estar en
rango" entre la API JSON y los formularios del admin. Cada handler de admin atrapa
`HTTPException`/`ValidationError` y re-renderiza la misma página con el mensaje de error
(ya en español, viene de la API) en vez de dejar que se propague como una respuesta JSON
cruda.

Cuidado al escribir templates de admin: las comparaciones de estado (ej. "¿este combate está
pendiente?") deben hacerse con `==` contra el string plano (`m.status == "pending"`) — funciona
porque los enums heredan de `(str, Enum)` — **nunca** con `.value` (lo bloquea el guardrail de
`test_templates_language.py`) y tampoco asumir que `{{ status }}` imprime el valor plano: por
la forma en que `Enum` define `__str__`, `str(TournamentStatus.DRAFT)` da
`"TournamentStatus.DRAFT"`, no `"draft"` (aunque la comparación `==` y el filtro `|es_label`
sí funcionan bien, porque no dependen de `__str__`).

101 tests pasando en total.

Fase 8 (preparación del deploy): (1) `normalize_database_url` en `app/database.py` convierte
`postgres://`/`postgresql://` en `postgresql+psycopg://` — Neon entrega la forma genérica y
SQLAlchemy usaría `psycopg2`, que no está instalado. `alembic/env.py` lee la URL de ese mismo
módulo, así que las migraciones también quedan cubiertas. (2) `app/config.py`
(`check_production_settings`, llamada desde `app/main.py` al importar): si `APP_ENV=production`
y `SECRET_KEY`/`ADMIN_PASSWORD` siguen con su default (`dev-secret-key`/`admin`) o no están
definidas, lanza `RuntimeError` y el contenedor no arranca. `APP_ENV` es un nombre propio del
proyecto, no del framework; se eligió una variable explícita porque "hay Postgres" no distingue
producción de `docker compose` local (ambos usan Postgres con credenciales de desarrollo). (3)
El `CMD` del `Dockerfile` usa `${PORT:-8000}` porque Render asigna el puerto por `$PORT`.
Verificado con contenedores reales (con y sin `PORT`, con `APP_ENV=production` con valores por
defecto — falla — y con valores propios — arranca). Para `DATABASE_URL` en Render usar el
connection string **directo** de Neon (host sin `-pooler`), no el pooled.

Fase 7: `Dockerfile` (`python:3.10-slim`, sin `--reload`) + `docker-entrypoint.sh` (corre
`alembic upgrade head` antes de `exec`-ear el comando de arranque, así las migraciones ya
están aplicadas cuando el contenedor empieza a servir) + `docker-compose.yml` (`db` = Postgres
16 alpine con volumen nombrado `pgdata`, `app` = build local, espera a que `db` esté
`healthy`). Driver de Postgres: `psycopg[binary]` (psycopg 3, no psycopg2), URL
`postgresql+psycopg://...`. `tests/conftest.py` (fixture `client`) lee `DATABASE_URL` —
default `sqlite:///:memory:` si no está seteada, Postgres si lo está (con
`Base.metadata.drop_all` antes de `create_all` en cada test, porque Postgres es un servidor
persistente y no una base nueva por test como `:memory:`). Verificación real: con los
contenedores arriba, se corrió **toda** la suite de pytest apuntando al Postgres de Docker
(`DATABASE_URL=postgresql+psycopg://... pytest`) y los 92 tests pasaron igual que contra
SQLite — sin sorpresas con el `Enum` nativo de Postgres (que en SQLite es solo un `VARCHAR`
sin validar). Ver `docs/DECISIONS.md` (entrada 2026-10-02) sobre un primer intento de esta
verificación que resultó falso — el fixture tenía SQLite hardcodeado y la variable de entorno
no hacía nada. `.dockerignore` excluye `tests/`, `http/`, `docs/` de la imagen — son
herramientas de desarrollo, no hace falta que viajen a producción.

Nota de Python: en `app/schemas.py` se usa `import datetime` + `datetime.date` en vez de
`from datetime import date`, porque un campo Pydantic llamado `date` con un tipo también
llamado `date` y valor por defecto se pisa a sí mismo (la asignación ocurre antes que la
evaluación de la anotación) — ver el commit de fase 2 si hace falta el detalle.

## Entorno

- Se desarrolla dentro de **WSL (Ubuntu-22.04)**, nunca en Windows nativo ni en `/mnt/c/...`.
- Python 3.10+ (no asumir 3.12, no está instalado en esta máquina y no hace falta).
- Docker instalado y funcionando en esta distro desde la fase 7 (`docker compose` — nota la
  nueva sintaxis sin guion, no `docker-compose`). Nota de entorno: instalar Docker rompió la
  resolución DNS de la distro (`generateResolvConf = false` en `/etc/wsl.conf` sin nada que lo
  reemplace); se arregló con `sudo bash -c 'echo "nameserver 8.8.8.8" > /etc/resolv.conf'` — si
  vuelve a pasar (ej. después de un `wsl --shutdown`), ese es el fix.
- Si se maneja el admin con un navegador automatizado (herramientas `mcp__Claude_Browser__*`):
  tras cada envío de formulario hay que **esperar a que la página termine de recargar y
  verificarlo** antes de escribir el siguiente — en el plan gratis de Render la respuesta puede
  tardar más de 2 s, y escribir sobre el formulario viejo cancela el envío en curso (así se
  perdió un atleta en la prueba de producción). Las referencias (`ref_N`) de `read_page` se
  invalidan al recargar, y con el filtro `interactive` solo aparecen los elementos dentro del
  viewport — si el formulario quedó más abajo, usar `find` en vez de `read_page`.
- **No hacer `git commit`, `git push` ni `git tag` salvo que el usuario lo pida explícitamente
  en ese momento.** Implementar y verificar (tests, server manual) y dejar los cambios sin
  stagear; el usuario revisa antes de decidir si se commitea. Cuando sí lo pida, un commit por
  sub-paso verificado (no uno gigante por fase), mensajes estilo `feat:`/`fix:`/`chore:`.
- **Flujo de ramas.** El trabajo se hace en la rama **`dev`**, con commits chicos (uno por
  sub-paso) y probando ahí. A **`main`** solo se llega con un pull request `dev` → `main`, que
  el usuario abre y mergea (**merge normal**, con merge commit — no squash ni rebase, para
  conservar los commits por sub-paso) cuando se juntaron suficientes cambios para una versión; Render
  despliega desde `main`, así que el merge **es** el deploy a producción. El CI de GitHub
  Actions corre `pytest` en pushes a `main`/`dev` y en PRs a `main`. El asistente trabaja en
  `dev` y no toca `main`. Cada cambio visible suma una línea en `[Unreleased]` de
  `CHANGELOG.md` en el mismo commit que lo introduce.
- **Tags de versión (SemVer).** Cada versión liberada lleva un tag **anotado** `vX.Y.Z`
  (`git tag -a vX.Y.Z -m "X.Y.Z"`). Reglas:
  1. El tag va sobre **`main`, ya mergeado el PR** (no sobre `dev`), en el commit que contiene
     el cambio de `app/version.py` y de `CHANGELOG.md` de esa versión, con los tests en verde
     (SQLite y Postgres) — nunca antes. El cambio de versión es el último commit del PR.
  2. Una versión = un tag. **Nunca mover, borrar ni reescribir un tag ya publicado**: si una
     versión salió mal, se corrige con una versión de parche nueva.
  3. Al terminar el trabajo de una versión, el asistente **no crea el tag**: deja en `dev` el
     commit de cambio de versión y changelog y, en su mensaje final, le recuerda al usuario
     que primero tiene que abrir y mergear el PR `dev` → `main`, y **después** le da los
     comandos exactos (en bloques `bash` separados, uno por bloque): `git checkout main && git
     pull`, y `git tag -a vX.Y.Z -m "X.Y.Z"`, y `git push origin vX.Y.Z`. Solo crea el tag si
     el usuario se lo pide explícitamente.
  4. Después del push, recordarle verificar `/health` (debe mostrar la versión nueva) y una
     página pública antes de dar la versión por buena.
  5. Cuando el usuario pida **commit y push**, el asistente evalúa si el cambio cierra una
     versión (o un hito equivalente, ej. una fase completa desplegada) y, si vale la pena un
     tag, **pregunta antes de crearlo** — nunca lo crea por iniciativa propia en ese momento.
     Si no corresponde ninguno, no menciona tags.

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

## Idioma

- **Todo texto visible para el usuario va en español** (páginas públicas, futura pantalla
  admin, mensajes de error de la API vía `HTTPException`). Los enums de `app/models.py`
  (`TournamentStatus`, `Discipline`, `Gender`, `BeltGroup`, `MatchStatus`) se guardan en
  inglés a propósito — son identificadores internos — pero se traducen siempre con el filtro
  Jinja `|es_label` (definido en `app/web/labels.py`). **Nunca usar `.value` directo en una
  plantilla** — `tests/test_templates_language.py::test_no_raw_enum_value_in_templates`
  falla si aparece, sin importar en qué plantilla ni qué enum sea (incluida la fase 6).
- Fuera de este alcance, y está bien que queden en inglés: Swagger (`/docs`), los `tags` de
  los routers en la API, comentarios de código, mensajes de commit — son herramientas de
  desarrollo, no la interfaz del producto.

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
