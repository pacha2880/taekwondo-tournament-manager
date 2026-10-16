# Contexto para asistentes de IA

Proyecto de portafolio: sistema de torneos de taekwondo en Python/FastAPI, construido por
fases incrementales. Leer este archivo primero. El porqué de cada decisión no obvia está en
`docs/DECISIONS.md`, el roadmap en `docs/BACKLOG.md`, y el checklist de fases y los comandos
de uso en `README.md` — este archivo no repite ese contenido, solo apunta a él.

## Estado actual

- Versión `0.2.0` (`app/version.py`, única fuente de verdad). En producción:
  https://taekwondo-tournament-manager.onrender.com (Render + Neon, región Ohio). Hay un
  servicio **dev** en Render que despliega la rama `dev` contra una rama `dev` de Neon.
- Quedan datos de demo en la base de **producción** (club "Club Demo Cochabamba", torneo
  "Copa Cochabamba DEMO"); el admin no tiene botón de borrar — limpieza solo por SQL desde el
  panel de Neon.
- En desarrollo en `dev`: `0.3.0` (CORS + documentación de la API para consumidores
  externos). Después: backlog de Fase 9 en `docs/BACKLOG.md` (tiene decisiones pendientes del
  usuario anotadas al principio del archivo).
- Contexto de prioridades: un amigo del usuario construye un frontend separado (otra
  tecnología) contra esta API — por eso la API pasó a ser un producto con su propia
  autenticación, CORS y documentación, priorizados antes que editar datos de atletas.

## Mapa del código

- `app/models.py` — SQLAlchemy 2.0 (`Mapped`/`mapped_column`): `Club`, `Athlete`,
  `Tournament`, `Category`, `Registration`, `Bracket`, `Match`, `RoundScore`.
- `app/api/` — un router por entidad, montado en `app/main.py` bajo `/api/v1/...`.
  Validaciones de negocio (género/peso de inscripción, duplicados) en `registrations.py`.
- `app/services/brackets.py` — generación de llaves: lógica pura sin DB separada de
  `generate_bracket` (que persiste), para poder testear byes sin sesión de SQLAlchemy.
  `advance_winner` propaga el ganador a la siguiente ronda. `resolve_athlete_names(db,
  matches)` resuelve nombres en batch (evita N+1) — la reusan `app/api/brackets.py`,
  `app/api/matches.py`, `app/web/public.py` y `app/web/admin/category_workspace.py`; no
  duplicar esa resolución en un quinto lugar.
- `app/services/scoring.py` — `record_round`: un round no puede empatar (422); el combate
  pasa a `FINISHED` (y dispara `advance_winner`) recién al llegar a
  `category.rounds_to_win` rounds ganados, no antes.
- `app/web/admin.py` / `app/web/admin/` — pantalla admin (login por sesión,
  `SessionMiddleware`). **Sus handlers llaman directo a las funciones de `app/api/*.py`** (ej.
  `create_club_api = create_club`) en vez de reimplementar validaciones de negocio — son
  funciones Python normales, `Depends(get_db)` es solo un default que se ignora al pasar `db`
  explícito. Cada handler atrapa `HTTPException`/`ValidationError` y re-renderiza la página
  con el error en español en vez de devolver JSON crudo.
- `app/web/labels.py` — traducción de enums a español (filtro Jinja `es_label` y
  `match_status_badge_class`). `app/web/templating.py` — único entorno Jinja2 compartido
  (filtros + versión global); no crear otro.
- `app/auth.py` / `app/api/auth.py` — login y JWT. `app/api_docs.py` — tags/descripciones de
  `/docs`. `app/cors.py` — CORS (`CORS_ORIGINS`, ver tabla de variables en `README.md`).
- `app/config.py` — lee variables de entorno y valida los ambientes desplegados
  (`DEPLOYED_ENVIRONMENTS = {"production", "staging"}`): ambos exigen `SECRET_KEY`/
  `ADMIN_PASSWORD` propios; solo `production` prohíbe `CORS_ORIGINS=*` (el servicio `dev` usa
  `staging` para poder aceptar cualquier origen mientras se prueba un frontend externo).

## Reglas para endpoints nuevos de `/api/v1`

- **Auth**: por default `dependencies=ADMIN_ONLY`. Si es una lectura que se decide pública a
  propósito, agregarla a `PUBLIC_ENDPOINTS` en `tests/test_api_auth.py` (ese test lee el
  esquema OpenAPI y falla si no se hace). Nunca público un endpoint que devuelva fecha de
  nacimiento o peso de un atleta.
- **Docs**: `summary` propio, `description`, `tags=[TAG_...]` (constantes de
  `app/api_docs.py`; grupos en español, no renombrar — los usan generadores de clientes), y
  `responses=errors({...}, auth=True/False)` con los errores reales (401 si requiere token,
  404 si tiene parámetro de ruta; el 422 de negocio se explica en la descripción, no en
  `errors()`). Todo campo nuevo de `app/schemas.py` lleva `Field(description=...)` en la clase
  `*Base`; todo enum nuevo, una docstring en español. `tests/test_api_docs.py` falla si falta
  algo de esto. `operationId` = nombre de la función (debe ser único entre routers).

## Gotchas no obvios

- FastAPI 0.141: los routers incluidos quedan como objetos anidados — `app.routes` **no**
  sirve para inventariar rutas (lo usan los tests de auth/docs). Usar
  `app.openapi()["paths"]`.
- En templates, `str(TournamentStatus.DRAFT)` da `"TournamentStatus.DRAFT"`, no `"draft"` —
  no asumir que `{{ status }}` imprime el valor plano. Comparar con `==` contra el string
  plano (`m.status == "pending"`, funciona porque los enums heredan de `(str, Enum)`); la
  regla de no usar `.value` está en **Idioma** más abajo.

## Versionado (SemVer)

Versión en `app/version.py` (única fuente). Al liberar una versión: subir `__version__` y
mover `[Unreleased]` de `CHANGELOG.md` a su sección nueva (`tests/test_version.py` falla si no
coinciden). Dentro de `0.x`, las migraciones de Alembic **solo agregan** (columnas nuevas
opcionales, nunca borrar ni renombrar), para que volver a un tag anterior siga funcionando
sobre una base ya migrada. Reglas de tags y flujo de ramas: ver **Entorno** más abajo y la
sección **Versionado** de `README.md`.

## Entorno

- Se desarrolla dentro de **WSL (Ubuntu-22.04)**, nunca en Windows nativo ni en `/mnt/c/...`.
- Python 3.10+ (no asumir 3.12, no está instalado en esta máquina y no hace falta).
- Docker funcionando desde la fase 7 (`docker compose`, sin guion). Nota de entorno: instalar
  Docker rompió la resolución DNS de la distro (`generateResolvConf = false` en
  `/etc/wsl.conf` sin nada que lo reemplace); se arregló con
  `sudo bash -c 'echo "nameserver 8.8.8.8" > /etc/resolv.conf'` — si vuelve a pasar (ej. tras
  un `wsl --shutdown`), ese es el fix.
- Navegador automatizado (`mcp__Claude_Browser__*`) contra el admin: esperar a que la página
  recargue y verificarlo antes de escribir el siguiente campo (el plan gratis de Render puede
  tardar más de 2 s; escribir sobre el formulario viejo cancela el envío). Las referencias
  (`ref_N`) se invalidan al recargar; si el formulario no entra en el viewport, usar `find` en
  vez de `read_page`.
- **No hacer `git commit`, `git push` ni `git tag` salvo que el usuario lo pida explícitamente
  en ese momento.** Implementar y verificar (tests, server manual) y dejar los cambios sin
  stagear; el usuario revisa antes de decidir si se commitea. Cuando sí lo pida, un commit por
  sub-paso verificado (no uno gigante por fase), mensajes estilo `feat:`/`fix:`/`chore:`.
  **Qué cuenta como pedido de commit:** solo una orden directa y actual ("commiteá",
  "hacé el commit", "pedime el commit y lo hacés"). Frases que describen cómo estructurar el
  trabajo — "un commit por cada uno", "con tests", "procedamos con esto" — **no** son un
  pedido: en ese caso se implementa y se verifica, se deja todo **sin stagear y sin
  commitear**, y se pregunta antes de commitear. Ante la duda, no commitear y preguntar. (Esta
  regla existe porque ya se interpretó mal una vez y hubo que deshacer tres commits.)
  Cuando se pida el commit de cambios que quedaron mezclados en los mismos archivos (por
  ejemplo `CHANGELOG.md` o un archivo de tests con aportes de varios cambios), separar por
  hunks para que cada commit lleve solo lo suyo.
- **Flujo de ramas.** El trabajo se hace en la rama **`dev`**, con commits chicos (uno por
  sub-paso) y probando ahí. A **`main`** solo se llega con un pull request `dev` → `main`, que
  el usuario abre y mergea (**merge normal**, con merge commit — no squash ni rebase, para
  conservar los commits por sub-paso) cuando se juntaron suficientes cambios para una versión;
  Render despliega desde `main`, así que el merge **es** el deploy a producción. El CI de
  GitHub Actions corre `pytest` en pushes a `main`/`dev` y en PRs a `main`. El asistente
  trabaja en `dev` y no toca `main`. Cada cambio visible suma una línea en `[Unreleased]` de
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

- **Todo texto visible para el usuario va en español** (páginas públicas, pantalla admin,
  mensajes de error de la API vía `HTTPException`). Los enums de `app/models.py`
  (`TournamentStatus`, `Discipline`, `Gender`, `BeltGroup`, `MatchStatus`) se guardan en
  inglés a propósito — son identificadores internos — pero se traducen siempre con el filtro
  Jinja `|es_label` (definido en `app/web/labels.py`). **Nunca usar `.value` directo en una
  plantilla** — `tests/test_templates_language.py::test_no_raw_enum_value_in_templates`
  falla si aparece, sin importar en qué plantilla ni qué enum sea.
- **La documentación de la API (`/docs`, `/redoc`, `/openapi.json`) también va en español**,
  porque la consumen personas ajenas al proyecto: descripción general, `summary`/`description`
  de cada operación, descripciones de campos y de enums, y los nombres de los grupos (`tags`:
  Torneos, Categorías, Atletas, Clubes, Inscripciones, Llaves, Combates, Autenticación,
  Sistema). **Quedan en inglés los identificadores**: rutas, nombres de campos y valores de
  enums (`male`, `in_progress`…). Los nombres de los grupos son parte del contrato: muchos
  generadores de clientes los usan para nombrar clases, así que **no renombrarlos** sin
  avisar. Un test falla si una operación de `/api/v1` queda sin descripción o un campo sin
  documentar.
- Fuera de este alcance, y está bien que queden en inglés: comentarios de código y mensajes de
  commit.

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

Ver [`docs/DECISIONS.md`](docs/DECISIONS.md) para el porqué de cada decisión no obvia
(arquitectura, infra, auth, CORS, documentación de la API) — este archivo no repite esas
explicaciones, solo las reglas que de ellas se derivan.

## Verificación esperada en cada fase

- `pytest -v` pasa (contra SQLite; ver `README.md` para correrlo también contra el Postgres
  de Docker).
- Se puede levantar el server y probar manualmente vía `/docs` (Swagger) o navegador.
- No romper lo verificado en fases anteriores (correr toda la suite, no solo los tests
  nuevos).
