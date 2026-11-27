# Decisiones de arquitectura (ADR liviano)

Registro corto de decisiones no obvias, con el porqué, para no tener que re-derivar el
razonamiento más adelante.

Cada entrada cuenta lo que se decidió en su fecha y no se reescribe: si algo cambia, se agrega una entrada y se
actualiza el estado acá.

## Índice

| Fecha | Decisión | Estado |
|---|---|---|
| 2026-09-11 | [Render + Neon en vez de Railway/Fly.io/Render-Postgres](#2026-09-11--render--neon-en-vez-de-railwayflyiorender-postgres) | Vigente |
| 2026-09-11 | [Integración con LLM fuera de alcance](#2026-09-11--integración-con-llm-fuera-de-alcance) | Vigente |
| 2026-09-11 | [`discipline` se mantiene aunque hoy solo tenga un valor](#2026-09-11--discipline-se-mantiene-aunque-hoy-solo-tenga-un-valor) | Vigente |
| 2026-09-11 | [Sin tabla oficial de pesos hardcodeada](#2026-09-11--sin-tabla-oficial-de-pesos-hardcodeada) | Reemplazada en parte por 2026-11-16: los pesos salen de la estructura del torneo |
| 2026-09-11 | [`Club` como entidad propia, obligatoria en `Athlete`](#2026-09-11--club-como-entidad-propia-obligatoria-en-athlete) | Vigente |
| 2026-09-12 | [Desarrollo dentro de WSL desde el día 0](#2026-09-12--desarrollo-dentro-de-wsl-desde-el-día-0) | Vigente |
| 2026-09-29 | [Revertir "MatchRead solo ids": agregar nombres de atletas a la API](#2026-09-29--revertir-matchread-solo-ids-agregar-nombres-de-atletas-a-la-api) | Vigente |
| 2026-10-01 | [Fase 7: `psycopg` (v3) en vez de `psycopg2`, migraciones en el entrypoint](#2026-10-01--fase-7-psycopg-v3-en-vez-de-psycopg2-migraciones-en-el-entrypoint) | Vigente |
| 2026-10-03 | [Fase 8: preparar la app para Render + Neon](#2026-10-03--fase-8-preparar-la-app-para-render--neon) | Vigente; `APP_ENV` se amplía en 2026-10-17 y `SECRET_KEY` en 2026-10-25 |
| 2026-10-04 | [Versionado semántico, empezando en 0.1.0](#2026-10-04--versionado-semántico-empezando-en-010) | Vigente, salvo el orden del backlog y «subir el minor en cada release» (hoy, la skill `release`) |
| 2026-10-15 | [API protegida con login y JWT (0.2.0)](#2026-10-15--api-protegida-con-login-y-jwt-020) | Vigente, salvo el largo de `SECRET_KEY` (2026-10-25) |
| 2026-10-15 | [Se quitan los `.http`; la app avisa si `SECRET_KEY` es corta](#2026-10-15--se-quitan-los-http-la-app-avisa-si-secret_key-es-corta) | Vigente, salvo el aviso de `SECRET_KEY` (2026-10-25) |
| 2026-10-16 | [API para frontends externos: CORS y documentación (0.3.0)](#2026-10-16--api-para-frontends-externos-cors-y-documentación-030) | Vigente, salvo la lista de métodos de CORS (hoy, `app/cors.py`) |
| 2026-10-17 | [`APP_ENV=staging`, para que el servicio `dev` pueda aceptar `CORS_ORIGINS=*`](#2026-10-17--app_envstaging-para-que-el-servicio-dev-pueda-aceptar-cors_origins) | Vigente |
| 2026-10-23 | [CI del atleta (0.4.0)](#2026-10-23--ci-del-atleta-040) | Vigente |
| 2026-10-24 | [Editar atletas y clubes (0.4.0)](#2026-10-24--editar-atletas-y-clubes-040) | Reemplazada en parte por 2026-11-23: también cuentan edad y grado; `null` también borra `height_cm` |
| 2026-10-25 | [Búsqueda de atletas (0.4.0)](#2026-10-25--búsqueda-de-atletas-040) | Vigente |
| 2026-10-25 | [`SECRET_KEY` corta: de aviso a error](#2026-10-25--secret_key-corta-de-aviso-a-error) | Vigente |
| 2026-10-26 | [El servidor numera los rounds (0.5.0)](#2026-10-26--el-servidor-numera-los-rounds-050) | Numeración reemplazada en la 0.6.0: el cliente envía `round_number`, que tiene que ser el siguiente. Sigue vigente no corregir rounds |
| 2026-10-27 | [Ciclo de vida del torneo, parte 1: el estado manda (0.6.0)](#2026-10-27--ciclo-de-vida-del-torneo-parte-1-el-estado-manda-060) | Vigente, salvo `create_category`, que ya no existe (0.8.0) |
| 2026-10-29 | [Ciclo de vida del torneo, parte 2: llaves y resultados solo en curso (0.6.0)](#2026-10-29--ciclo-de-vida-del-torneo-parte-2-llaves-y-resultados-solo-en-curso-060) | Vigente |
| 2026-11-02 | [Lista pública de inscritos en la API (0.6.0)](#2026-11-02--lista-pública-de-inscritos-en-la-api-060) | Vigente; desde 2026-11-26 suma `weigh_in_status` (nunca los kilos) |
| 2026-11-10 | [Listados de categorías e inscripciones siempre filtrados](#2026-11-10--listados-de-categorías-e-inscripciones-siempre-filtrados) | Revertida por 2026-11-12 |
| 2026-11-12 | [Filtros de los listados otra vez opcionales](#2026-11-12--filtros-de-los-listados-otra-vez-opcionales) | Vigente |
| 2026-11-13 | [Grado fijo del atleta y cómo se retira `belt_rank` (0.7.0)](#2026-11-13--grado-fijo-del-atleta-y-cómo-se-retira-belt_rank-070) | Reemplazada en parte por 2026-11-26: la columna `belt_rank` ya se borró |
| 2026-11-14 | [Solo API: se eliminaron las vistas HTML](#2026-11-14--solo-api-se-eliminaron-las-vistas-html) | Vigente |
| 2026-11-16 | [Estructura de categorías del torneo (0.8.0)](#2026-11-16--estructura-de-categorías-del-torneo-080) | Reemplazada en parte por 2026-11-25 y 2026-11-26: `belt_group` ya no está; ya no hay categorías históricas |
| 2026-11-22 | [Pesos con un decimal como máximo](#2026-11-22--pesos-con-un-decimal-como-máximo) | Vigente |
| 2026-11-23 | [`category_mismatch` revisa edad y grado](#2026-11-23--category_mismatch-revisa-edad-y-grado) | Reemplazada en parte por 2026-11-26: ya no hay categorías históricas ni atletas sin grado |
| 2026-11-25 | [Las categorías se distinguen por su grupo; `belt_group` sale de la API (0.8.1)](#2026-11-25--las-categorías-se-distinguen-por-su-grupo-belt_group-sale-de-la-api-081) | Reemplazada en parte por 2026-11-26: la columna `belt_group` ya se borró y no hay categorías históricas |
| 2026-11-26 | [Bases vaciadas y fuera el soporte de datos viejos](#2026-11-26--bases-vaciadas-y-fuera-el-soporte-de-datos-viejos) | Vigente |
| 2026-11-26 | [Ciclo del torneo de la 0.9.0: un solo camino, fecha límite y peso oficial en la inscripción](#2026-11-26--ciclo-del-torneo-de-la-090-un-solo-camino-fecha-límite-y-peso-oficial-en-la-inscripción) | Vigente |

## 2026-09-11 — Render + Neon en vez de Railway/Fly.io/Render-Postgres

Investigado en 2026: Railway ya no tiene tier gratis real (solo $5 de crédito único),
Fly.io ya no da tier gratis a cuentas nuevas (solo trial de 2h) y pide tarjeta. Render sigue
con tier gratis real (750h/mes, sin tarjeta) pero su Postgres gratis expira a los 90 días.
Neon tiene Postgres gratis sin fecha de expiración. Combo elegido: Render (web service) +
Neon (Postgres), ambos gratis indefinidamente, para un proyecto portafolio que debe seguir
vivo en el tiempo.

## 2026-09-11 — Integración con LLM fuera de alcance

El job posting menciona LLM APIs/LangChain/Bedrock como *nice-to-have*, no como requisito.
No hay una necesidad real del dominio (torneos de taekwondo) que un LLM resuelva mejor que
lógica normal. Se descarta del plan inicial; se reconsidera solo si sobra tiempo al final,
como feature aislada y justificada (no forzada).

## 2026-09-11 — `discipline` se mantiene aunque hoy solo tenga un valor

`Category.discipline` (hoy solo `SPARRING`) se mantiene desde el modelo inicial en vez de
agregarse después. Agregar una columna nueva a una tabla que ya tiene datos en producción es
una migración con más riesgo que agregar una columna vacía a un modelo nuevo. Es una decisión
barata de tomar ahora y cara de tomar después.

## 2026-09-11 — Sin tabla oficial de pesos hardcodeada

Las tablas de peso por categoría (cinturón/edad/género) varían por federación y país, y
cambian con el tiempo. En vez de modelarlas como datos fijos del sistema, `Category` tiene un
`weight_label` de texto libre que el admin define al crear cada categoría del torneo. Esto
evita mantener datos regulatorios que no son el problema que este proyecto busca resolver.

## 2026-09-11 — `Club` como entidad propia, obligatoria en `Athlete`

Un atleta pertenece siempre a un club (no es opcional, no cambia por torneo). Se modela como
`Club(id, name)` + `Athlete.club_id` (FK obligatoria) en vez de un campo de texto libre en
`Athlete`, para no duplicar nombres de club con variaciones de escritura.

## 2026-09-12 — Desarrollo dentro de WSL desde el día 0

El usuario tiene Windows como host pero el despliegue es Linux (Render) y ya tenía WSL con
Ubuntu-22.04 instalado. En vez de dividir el desarrollo entre venv nativo de Windows y Docker
en WSL, todo el proyecto (venv, git, Docker cuando llegue la fase 7) vive dentro de WSL, en el
filesystem nativo de la distro (no en `/mnt/c/...`, que es notablemente más lento y da
problemas con file-watchers). Esto evita divergencias entre "funciona en mi máquina" (Windows)
y "falla en el contenedor" (Linux). Se verificó Python 3.10.12 disponible (no 3.12; ninguna
feature del plan lo requiere) y que Docker todavía no tiene la integración WSL activada en
esta máquina — pendiente antes de la fase 7, no bloqueante ahora.

## 2026-09-29 — Revertir "MatchRead solo ids": agregar nombres de atletas a la API

En la Fase 5 se decidió que `MatchRead` expusiera solo ids de atletas (no nombres), para no
acoplar el contrato JSON a una necesidad de presentación. En la práctica, los tres
consumidores necesitan los nombres siempre — nadie quiere ids solos. Mantener la API "pura" estaba
protegiendo un caso de uso hipotético (un consumidor futuro que sí quisiera solo ids) a costa
de un problema real y actual: la misma lógica de resolución de nombres (batch query para
evitar N+1) estaba duplicada.

Se agregó `athlete_red_name`/`athlete_blue_name`/`winner_name` a `MatchRead`
(`app/schemas.py`), y se centralizó la resolución en `resolve_athlete_names(db, matches)`
(`app/services/brackets.py`) — la única función que hace esa consulta batch. La reusan
`app/api/brackets.py` y `app/api/matches.py`; ninguno vuelve a escribirla por su cuenta.

Detalle de implementación: como `Match` (el modelo ORM) no tiene atributos `*_name`, no se
puede confiar en la conversión automática `from_attributes=True` para esos tres campos.
`app/api/brackets.py`/`app/api/matches.py` construyen `MatchRead`/`BracketRead` con
`model_validate` y después les asignan los nombres resueltos por atributo (los modelos de
Pydantic v2 son mutables salvo que se marquen `frozen=True`) — no hace falta reconstruir el
objeto con `model_copy`.

## 2026-10-01 — Fase 7: `psycopg` (v3) en vez de `psycopg2`, migraciones en el entrypoint

Driver de Postgres elegido: `psycopg[binary]` (psycopg 3), no `psycopg2-binary`. Psycopg 3 es
el sucesor activamente mantenido, con soporte oficial de SQLAlchemy 2.0 vía el dialecto
`postgresql+psycopg://`, y no hay ninguna razón para arrancar un proyecto nuevo en 2026 sobre
la versión vieja.

Las migraciones de Alembic corren automático al arrancar el contenedor (`docker-entrypoint.sh`
hace `alembic upgrade head` antes de `exec "$@"`), no como un paso manual separado. Para una
sola instancia (que es lo que hay acá, y lo que habrá en Render en la fase 8) esto es seguro y
más simple que coordinar un paso de migración aparte — si en algún momento hubiera múltiples
instancias arrancando en paralelo, correr la migración en el entrypoint de cada una dejaría de
ser seguro (dos procesos compitiendo por aplicar la misma migración) y habría que moverla a un
paso de release separado.

**Corrección post-commit (2026-10-02)**: la primera vez que se afirmó haber corrido la suite
contra Postgres, esa verificación era falsa — `tests/conftest.py` tenía `"sqlite:///:memory:"`
hardcodeado en la fixture `client`, así que `DATABASE_URL=postgresql+psycopg://... pytest` no
tenía ningún efecto; los tests seguían corriendo contra SQLite sin importar la variable de
entorno. Se detectó al reproducir la verificación de punta a punta antes de un commit. Fix: la
fixture ahora lee `DATABASE_URL` (default `sqlite:///:memory:` si no está seteada) y arma el
engine según corresponda — `StaticPool`/`check_same_thread` solo para SQLite, que son
irrelevantes (y `check_same_thread` ni siquiera válido) para Postgres. Como Postgres es un
servidor persistente y no una base nueva por test como `:memory:`, hace falta
`Base.metadata.drop_all(bind=engine)` antes de `create_all` en cada test para mantener el
mismo aislamiento entre tests que ya daba SQLite gratis.

Con el fix, se confirmó la paridad SQLite/Postgres que esta fase existía para probar: se
corrió toda la suite de pytest apuntando al Postgres real de Docker (no solo a SQLite en
memoria) y los 92 tests pasaron igual, incluyendo las columnas `Enum` (que SQLAlchemy mapea a
un tipo `ENUM` nativo con validación en Postgres, y a un simple `VARCHAR` sin validar en
SQLite) — 24.6s contra Postgres vs. 4.1s contra SQLite, tiempos consistentes con que esta vez
sí viajó por red de verdad.

Nota de entorno (no de diseño): instalar Docker en esta WSL rompió la resolución DNS de la
distro (dejó `generateResolvConf = false` en `/etc/wsl.conf` sin nada que generara
`/etc/resolv.conf`). Se arregló escribiendo un `nameserver` fijo a mano — ver la sección
Entorno de `CLAUDE.md` si vuelve a pasar.

## 2026-10-03 — Fase 8: preparar la app para Render + Neon

**Render con runtime Docker**, no Python nativo: es la misma imagen que ya se probó contra
Postgres en la fase 7, así que lo que corre en producción es lo que se verificó.

**Postgres de Neon, no el de Render**: el Postgres gratis de Render expira a los 90 días; el de
Neon no vence. Región: Ohio (`us-east-2`) en ambos para que las consultas no crucen el país.

**Normalizar el prefijo de `DATABASE_URL`** (`normalize_database_url` en `app/database.py`):
Neon entrega `postgresql://...` y SQLAlchemy, sin driver explícito, usa `psycopg2` (no
instalado; el proyecto usa psycopg 3, que se pide con `postgresql+psycopg://`). Se normaliza en
código para poder pegar el string de Neon sin editarlo — editarlo a mano funcionaba igual, pero
es un olvido fácil que tira la app al arrancar.

**Bloqueo de credenciales por defecto en producción** (`app/config.py`): sin `SECRET_KEY` o
`ADMIN_PASSWORD` configurados, el código cae a `dev-secret-key`/`admin`, y en Render eso
dejaría un panel admin abierto en internet sin ningún aviso. No se puede detectar "estoy en
producción" mirando `DATABASE_URL` (`docker compose` local también usa Postgres con
credenciales de desarrollo), así que se usa una variable explícita, `APP_ENV=production`, que
solo se define en Render. Es un nombre propio del proyecto, no algo que FastAPI lea. Sin
`APP_ENV` no se revisa nada — por eso es parte de la lista de variables obligatorias de
Render. `ADMIN_USERNAME` no se valida: que sea `admin` no es el riesgo, la contraseña sí.

**`$PORT` en el `CMD` del `Dockerfile`**: Render asigna el puerto por la variable `PORT`;
`${PORT:-8000}` mantiene 8000 para local y `docker compose`. Se usa `exec` para que uvicorn
reciba directamente las señales de apagado.

**Connection string directo de Neon, no el pooled** (host sin `-pooler`): el endpoint con
pooling pasa por pgbouncer, que puede dar problemas con las migraciones de Alembic y con los
prepared statements de psycopg 3; el pooling solo aporta cuando hay muchísimas conexiones
simultáneas, y esta app tendrá muy pocas.

## 2026-10-04 — Versionado semántico, empezando en 0.1.0

La app ya está en producción y el backlog trae cambios de comportamiento, así que se adopta
[SemVer](https://semver.org/lang/es/) para poder volver a versiones anteriores y documentar
qué trae cada una.

**Empezar en `0.1.0`, no en `0.0.0` ni en `1.0.0`.** `0.0.0` significaría "nada publicado" y ya
hay producción. `1.0.0` declara una API pública estable, y todavía no lo es: el backlog incluye
reglas que cambian el comportamiento de `/api/v1/...` (ej. rechazar cargar resultados en un
torneo en borrador). SemVer permite eso dentro de `0.y.z`, y su FAQ recomienda arrancar en
`0.1.0` y subir el minor en cada release. `1.0.0` queda para cuando la API se declare estable.

**Una sola fuente de verdad: `app/version.py`.** No se usa `git describe` porque
`.dockerignore` excluye `.git` y la imagen que construye Render no tiene historial. La versión
se muestra en `/health`, que permite saber qué versión corre en producción sin abrir el navegador. Exponerla es
inofensivo en esta app y útil para verificar un deploy.

**Migraciones solo aditivas dentro de `0.x`** (columnas nuevas opcionales; nunca borrar ni
renombrar). Es lo que hace seguro volver a un tag anterior: el código viejo sigue funcionando
sobre una base ya migrada. Un cambio destructivo se haría en dos versiones (agregar lo nuevo
y migrar el código, y recién en una versión posterior borrar lo viejo).

**`CHANGELOG.md`** en formato Keep a Changelog, y un test que falla si su última versión
publicada no coincide con `app/version.py`, para que no se desincronicen.

**Orden del backlog (tres pasadas de análisis):** 0.2.0 admin más seguro, 0.3.0 datos de
atletas, 0.4.0 ciclo de vida del torneo, 0.5.0 campeones, 0.6.0 en vivo. La 0.3.0 va antes
que el ciclo de vida a propósito: tiene la única migración de esquema y es simple, así que
ensaya el camino commit → push → deploy → migración → rollback antes de los cambios de
comportamiento. Detalle en `docs/BACKLOG.md`.

## 2026-10-15 — API protegida con login y JWT (0.2.0)

**El problema.** Ningún endpoint de `/api/v1` exigía autenticación, así que cualquiera que abriera `/docs` podía crear y modificar
datos en producción. Se hizo visible al aparecer un consumidor externo (el frontend de un amigo,
en otra tecnología), pero el agujero existía desde antes.

**Token en la cabecera, no cookie.** Con un frontend en otro dominio, la cookie cruzada exige
`SameSite=None`, `credentials` en CORS, la bloquean cada vez más navegadores y abre la puerta a
CSRF. Un token que el frontend agrega a mano en `Authorization: Bearer` no sufre CSRF (una página
ajena no puede hacer que el navegador lo adjunte sola).

**JWT (HS256, PyJWT) y no un token propio de `itsdangerous`.** Para el servidor son equivalentes
(ambos *stateless*), pero JWT es el estándar: el frontend de otra tecnología puede leer el `exp`,
Swagger y las librerías lo entienden, y es lo que se espera en el mercado. El costo es una
dependencia pequeña. Al verificar se fija `algorithms=["HS256"]` (evita el error clásico de
aceptar `alg: none`; hay un test) y se exigen `exp` y `sub`.

**Login con formulario OAuth2** (`POST /api/v1/auth/login`): es la forma estándar y hace que
Swagger muestre el botón **Authorize**. Mismo usuario y clave del admin; la comparación es de
tiempo constante y vive en `app/auth.py`. `SECRET_KEY` y las
credenciales se leen desde `app/config.py` en vez de tres lugares distintos.

**8 horas, sin renovación automática.** El token no se puede revocar antes de vencer (nadie lo
guarda). Ocho horas cubren una jornada de torneo; un refresh token agregaría almacenamiento,
rotación y revocación que no se justifican hoy. El "botón de pánico" es cambiar `SECRET_KEY`
(invalida todos los tokens).

**Qué es público y qué no.** Públicos: torneos, categorías, clubes, llaves y combates (solo
nombres). Con token: todo `POST`/`PATCH`, y `GET` de atletas e inscripciones, porque devuelven fecha
de nacimiento y peso y hay menores. Si el frontend externo necesita mostrar "quiénes están
inscritos" antes de que exista la llave, se agregará un endpoint público que devuelva solo nombre
y club.

**Cómo se aplica.** La constante `ADMIN_ONLY = [Depends(require_api_admin)]` se pasa como
`dependencies=ADMIN_ONLY` en cada endpoint protegido.

**Test de inventario sobre el esquema OpenAPI, no sobre `app.routes`.** La primera versión del
test recorría `app.routes` buscando `APIRoute`; en FastAPI 0.141 los routers incluidos quedan como
objetos `_IncludedRouter` anidados, así que el recorrido no veía ninguna ruta y el test **pasaba en
vacío** sin verificar nada. Se detectó al ver que el conjunto de rutas sin proteger salía vacío. El
test ahora lee `app.openapi()["paths"]` (donde cada operación protegida declara su `security`, que
es además lo que ve quien consuma `/docs`), afirma que ve `POST /api/v1/clubs` para no poder pasar
vacío, y se comprobó con una prueba de mutación (quitar la protección de un endpoint hace fallar el
test). Un endpoint nuevo sin proteger y fuera de la lista `PUBLIC_ENDPOINTS` rompe el test.

**Margen de 30 s de reloj (`leeway`).** Los tests fallaban de forma intermitente (~1 de cada 50
corridas) con `401 Token inválido`. Con un registro temporal de la excepción se vio
`ImmatureSignatureError: The token is not yet valid (iat)`: el `iat` del token recién creado estaba
~2 s *adelante* de la hora de la verificación, es decir, el reloj de WSL2 retrocedió al
resincronizarse con Windows entre crear y verificar el token. Es la causa conocida de este síntoma,
y también ocurre en producción cuando dos instancias tienen relojes levemente distintos. La
solución estándar es tolerar un margen pequeño al verificar (`leeway`); aplica también al
vencimiento (un token vence hasta 30 s tarde, sin consecuencias prácticas). Hay un test del margen.

**Fixtures de test.** `client` manda un token válido por defecto (así los tests existentes no
cambian), `anon_client` comparte la misma base sin token, y un fixture automático fija un
`SECRET_KEY` de 32 bytes o más para no ensuciar la salida con `InsecureKeyLengthWarning` (PyJWT
avisa si la clave de HS256 es corta; la de producción la genera Render y es larga, pero **no se
valida su largo**: si `SECRET_KEY` fuera corta, PyJWT solo advertiría).

## 2026-10-15 — Se quitan los `.http`; la app avisa si `SECRET_KEY` es corta

**Se eliminó la carpeta `http/`** (archivos de REST Client). Con la API protegida, mantenerlos
exigía loguearse en cada archivo y agregar un archivo por cada endpoint nuevo, sin que nada los
verificara (y no se pudieron probar con la extensión real). Lo que cubrían ya lo hacen
`pytest` (comportamiento), Swagger con **Authorize** (exploración a mano) y la colección que se
importa desde `/openapi.json` en Postman o Insomnia. Siguen en el historial de git.

**Aviso de `SECRET_KEY` corta, no error.** PyJWT solo avisa cuando firma o verifica un token, y
una sola vez por proceso, así que es fácil no enterarse. La app ahora escribe una línea en los
logs al arrancar (solo con `APP_ENV=production`, para no molestar en desarrollo) si la clave mide
menos de 32 bytes, que es el mínimo que recomienda el RFC 7518 para HS256. Es un aviso y no un
error a propósito: si la clave real fuera corta, un error dejaría la app caída en producción en el
próximo deploy. Nunca imprime el valor. Se puede endurecer a error cuando se hayan verificado las
claves de dev y producción.

## 2026-10-16 — API para frontends externos: CORS y documentación (0.3.0)

**CORS con lista explícita y sin cookies.** Un frontend en otro dominio no puede leer las respuestas
si el servidor no lo autoriza (lo aplican los navegadores; `curl` y Postman lo ignoran, así que CORS
no protege la API: eso lo hace la autenticación). `CORS_ORIGINS` es una lista separada por comas; sin
definirla no se permite ningún origen, y con `APP_ENV=production` la app **se niega a arrancar si la
lista contiene `*`**. Como el token viaja en la cabecera `Authorization` y no hay cookies,
`allow_credentials=False`. Se permiten solo `GET`, `POST`, `PATCH` y `OPTIONS`, y las cabeceras `Authorization` y
`Content-Type`. El middleware de CORS se agrega al final para quedar como el más externo y responder
los *preflight* (`OPTIONS`) antes de que cualquier otra capa los toque; el preflight de un `POST`
protegido pasa sin token a propósito, porque el navegador nunca manda credenciales en un preflight.
Se separó en `app/cors.py` (`parse_origins` y `add_cors`) para poder probarlo sobre una app mínima sin
recargar `app.main`. Se quita la `/` final de cada origen al leerlo: un origen con barra final nunca
coincidiría con el que envía el navegador.

**Documentación en español, con los identificadores en inglés.** La consume gente ajena al proyecto, así
que las descripciones, los resúmenes y los nombres de los grupos van en español; rutas, campos y
valores de enums siguen en inglés (son el contrato). Los grupos (`tags`) quedaron fijados porque los
generadores de clientes los usan para nombrar clases: renombrarlos después rompería el código de quien
ya generó el suyo. Las descripciones viven en el código, junto a cada endpoint (`summary`,
`description`, `responses`) y en `Field(description=...)` de `app/schemas.py`, escritas una sola vez
en las clases `*Base` y heredadas por `Create`/`Read`; el texto general y los grupos están en
`app/api_docs.py`. Los enums se explican con su docstring, que Pydantic vuelca al esquema.

**`operationId` = nombre de la función** (`generate_unique_id_function=lambda route: route.name`):
pasa de `create_club_api_v1_clubs_post` a `create_club`. Los nombres de las funciones ya son únicos
entre routers y un test lo verifica. Es un cambio para quien hubiera generado un cliente, pero todavía
nadie lo había hecho.

**El 422 no se declara con el helper de errores.** FastAPI ya documenta el 422 de validación de formato;
los 422 de reglas de negocio (género y peso en inscripciones, empate en un round, rangos inválidos en una
categoría) se explican en la descripción del endpoint. `errors()` falla si se le pasa un 422 para evitar
pisar la respuesta estándar sin darse cuenta.

**Login simplificado.** `OAuth2PasswordRequestForm` agregaba al formulario `grant_type`, `scope`,
`client_id` y `client_secret`, que nunca se usaron y que además no se pueden documentar. Se reemplazó por
dos campos `Form` (`username`, `password`). El botón **Authorize** de Swagger sigue funcionando porque
depende del esquema de seguridad (`OAuth2PasswordBearer`) y no de este formulario; los campos extra que
manda Swagger se ignoran.

**Tests guardianes** (`tests/test_api_docs.py`), en la misma línea que el de autenticación: fallan si una
operación no tiene resumen propio (no el generado a partir del nombre de la función) ni descripción, si
no pertenece a exactamente un grupo declarado, si requiere token y no documenta el 401, si tiene un
parámetro de ruta y no documenta el 404, si algún campo o enum queda sin descripción, si hay `operationId`
repetidos o con restos de la ruta, o si aparecen rutas que no son de la API en el esquema. Se comprobó con pruebas de
mutación (quitar la descripción de un campo y de un endpoint hace fallar los tests).

## 2026-10-17 — `APP_ENV=staging`, para que el servicio `dev` pueda aceptar `CORS_ORIGINS=*`

**El problema.** `check_production_settings` solo validaba algo cuando `APP_ENV == "production"`
exactamente — cualquier otro valor (vacío, `development`, o lo que fuera) se salteaba **tanto** el
chequeo de credenciales por defecto **como** el de `CORS_ORIGINS=*`. El servicio `dev` de Render está
desplegado y es público (lo usa el frontend externo del amigo del usuario para probar con distintos
orígenes sin tener que actualizar una lista a mano), así que quedaba en la misma categoría que
`docker compose` local: si alguien se olvidaba de configurar `SECRET_KEY`/`ADMIN_PASSWORD` ahí, la app
arrancaba igual con los valores por defecto, expuestos en internet.

**La solución no es un tercer ambiente más laxo, es separar las dos condiciones.** Se agregó
`DEPLOYED_ENVIRONMENTS = {"production", "staging"}` en `app/config.py`: ambos exigen credenciales
propias (ahí `staging` es tan estricto como `production`), pero el rechazo de `CORS_ORIGINS=*` sigue
siendo exclusivo de `production` — es la única excepción real que necesitaba el servicio `dev`.
`warn_if_short_secret_key` también pasa a mirar `DEPLOYED_ENVIRONMENTS` en vez de solo `production`,
por la misma razón: un `staging` público con una clave corta es tan riesgoso como uno en producción.

## 2026-10-23 — CI del atleta (0.4.0)

**Opcional y único cuando existe.** Se había planteado obligatorio, pero el cliente confirmó que hay niños
pequeños sin CI, así que el campo es opcional en la base, en la API y en el admin. Una columna `NULL`able con
índice único admite varios `NULL` en SQLite y en Postgres, de modo que hay un solo criterio en todas las
capas y la migración solo agrega. Los atletas ya cargados quedan sin CI (no se inventan valores de relleno,
que además podrían chocar con un CI real). Omitir el campo, enviar `null` o enviar texto
vacío o en blanco (`""`) significan lo mismo, "sin CI", en la API y en el admin: lo resuelve el validador de
`app/schemas.py`, un solo lugar. Las respuestas siempre devuelven `null`.

**Formato: `[0-9]{5,9}(?:-[0-9A-Z]{2})?`.** Se pidió esta expresión y se revisó si alcanza. Cubre el CI
boliviano (número de 5 a 9 dígitos) y el complemento que se agrega para distinguir a dos personas con el mismo
número. Dos ajustes: (1) `[0-9]` en lugar de `\d`, porque en Python `\d` acepta dígitos de otros alfabetos
(por ejemplo árabe-índicos); (2) antes de validar se recortan espacios y se pasa a mayúsculas, así
`1234567-1a` no se rechaza ni se duplica. La unicidad es sobre el texto completo, porque el mismo número con
otro complemento es otra persona. **Limitación aceptada:** no admite CI de extranjeros con otros formatos ni
pasaportes. Si aparece el caso, se relaja la regla en `CI_REGEX` (`app/schemas.py`), que es el único lugar
donde está definida; el `pattern` se publica en el esquema OpenAPI para que el frontend externo valide igual.

**Mensaje en español sin `Field(pattern=...)`.** Con `pattern`, Pydantic responde en inglés ("String should
match pattern"); un validador (`AfterValidator`) con `ValueError` da el mensaje en español que ve el admin. El `pattern`
se publica aparte con `json_schema_extra`, a partir de la misma constante.

## 2026-10-24 — Editar atletas y clubes (0.4.0)

**`PATCH` con campos opcionales, igual que el de torneos.** Lo que no se envía no cambia y un `null` se ignora,
con una excepción: `ci`, donde `null` o `""` significa "borrar el CI" (se distingue de "no enviado" con
`exclude_unset`). El club del atleta se puede cambiar: corrige un error de carga o un traspaso, y las llaves
solo guardan nombres. La normalización del CI quedó en un tipo anotado (`NormalizedCi`) que comparten el alta y
la edición.

**Qué pasa al cambiar género o peso de un atleta inscrito** (la inscripción valida género y peso contra la
categoría; la edad no se valida, así que la fecha de nacimiento se edita siempre). La regla sale de la idea de
que cada inscripción pertenece a un torneo con un estado:

- **En curso:** se rechaza (`409`) si el nuevo valor ya no encaja en la categoría: no hay retiro posible
  porque la llave ya está sorteada, y sacarlo cambiaría las reglas del juego a mitad. Si sigue encajando se
  permite, igual que en borrador: no cambia la categoría ni la llave, y bloquearlo impediría corregir un
  error de tipeo o actualizar el peso para un torneo siguiente hasta que este termine.
- **En borrador:** si el nuevo género o peso ya no encaja en la categoría, se retira al atleta de ella, previa
  confirmación. Si sigue encajando no pasa nada: corregir un peso de 40 a 41 kg no debe sacarlo de ningún lado.
- **Finalizado:** se permite y no se toca la inscripción. El torneo ya es historia y el niño puede crecer para
  los siguientes; la inscripción antigua no se revalida ni se borra.

**Confirmación en dos pasos, sin estado en el servidor.** La API no tiene popups: si el cambio retiraría al
atleta de alguna categoría y no viene `confirm_withdrawal=true`, responde `409` con la lista de categorías y no
cambia nada; repetida con el parámetro, aplica el cambio y borra esas inscripciones. La validación de
género y peso se extrajo de `create_registration` a `app/services/eligibility.py` para que la inscripción y la
edición usen una sola regla.

**Hueco conocido hasta la 0.6.0: llaves en torneos en borrador.** Hoy se puede generar una llave en un torneo en
borrador; si luego se retira a un atleta de esa categoría, la llave queda apuntando a un atleta que ya no está
inscrito. No se agregó un chequeo ni el borrado de la llave porque la 0.6.0 prohíbe generarla fuera de `en
curso`, con lo que ese caso desaparece (ver BACKLOG). Hasta entonces, no editar género o peso de atletas de
categorías con llave en un torneo en borrador.

**Club.** Solo cambia el nombre, que sigue siendo único (`409` si lo tiene otro club; el propio nombre no cuenta).

## 2026-10-25 — Búsqueda de atletas (0.4.0)

**Un parámetro `q` opcional en `GET /athletes`, usado también por el admin.** El admin llama a la misma función
que la API (`list_athletes`), que delega en `app/services/athlete_search.py`; así hay una sola definición de
"coincide". Sin `q` el comportamiento es el de siempre. Busca el texto *dentro* del nombre o del CI.

**Se filtra en Python, no en SQL, para ignorar las tildes.** `ILIKE` ignora mayúsculas pero no tildes, y la
extensión `unaccent` de Postgres no existe en SQLite. Se normaliza (NFD sin marcas combinantes, `casefold`) el
texto buscado y el de cada atleta: `perez` encuentra a `Pérez`, y como efecto colateral `nunez` encuentra a
`Núñez` (la `ñ` también se descompone). **Costo aceptado:** cada búsqueda carga todos los atletas en memoria;
con cientos o pocos miles es imperceptible. Si el volumen crece, la salida es una columna de búsqueda
normalizada en la base o `unaccent` en Postgres, no cambiar el contrato de la API.

**Fuera de alcance, por decisión:** buscar por club y un filtro "solo sin CI" (la lista ya omite "CI" en quien
no lo tiene).

## 2026-10-25 — `SECRET_KEY` corta: de aviso a error

Con `APP_ENV=production` o `staging`, un `SECRET_KEY` de menos de 32 bytes ahora impide arrancar, igual que
las credenciales por defecto: un aviso en los logs es fácil de pasar por alto. Es el endurecimiento que preveía
la entrada de la 0.2.0. Antes de desplegarlo hay que confirmar que las claves de Render (`dev` y producción)
miden 32 bytes o más; si no, el deploy queda caído hasta cambiarlas.

## 2026-10-26 — El servidor numera los rounds (0.5.0)

**El número de round lo asigna el servidor, no el cliente.** El backlog planteaba fijar el número solo en el
formulario del admin, pero el hueco estaba en la API: `round_number` era obligatorio y solo se rechazaba un
número repetido, así que se podía cargar el round 5 sin el 1 o dejar huecos, y el frontend externo habría
heredado el problema. Ahora `RoundScoreCreate` solo lleva `red_points` y `blue_points`, y `record_round`
asigna `rounds ya cargados + 1`; la respuesta (`RoundScoreRead`) sigue incluyendo `round_number`. Se
eliminó `DuplicateRound`, que ya no puede ocurrir. Sin capa de compatibilidad (estamos en `0.x`, y Pydantic
ignora el campo si alguien todavía lo envía). **Costo aceptado:** la restricción única
`uq_round_per_match` sigue siendo la red de seguridad si dos envíos simultáneos calculan el mismo número: el
segundo falla con un error 500 en lugar de un mensaje claro.

**No se agrega corrección de rounds ya cargados.** Era la decisión pendiente del backlog: se resolvió que
alcanza con el número fijo. Corregir un round obligaría a
reabrir el combate y a deshacer el avance del ganador, que es el cambio con más riesgo de dejar datos
inconsistentes; se reabre solo si el uso real lo pide.

## 2026-10-27 — Ciclo de vida del torneo, parte 1: el estado manda (0.6.0)

**Las inscripciones se cierran por el estado del torneo, no por la llave.** El backlog planteaba bloquear las
inscripciones de una categoría en cuanto tuviera llave. Se cambió por una regla única: `create_registration` y
`create_category` solo funcionan con el torneo en `draft` (409 si no). Motivo: las llaves solo se generan con el
torneo en curso (para que el sorteo sea un evento público, no algo que pasó a escondidas), así que una
categoría con llave ya tiene las inscripciones cerradas, y toda la lógica depende de un único dato. Cada estado
queda con un significado claro: `draft` = preparación (categorías, inscripciones, ediciones de género/peso con
retiro), `in_progress` = lista congelada, llaves y resultados, `finished` = resultados definitivos.

**Costos aceptados.** Una vez que el torneo pasa a «en curso» no se puede inscribir a nadie más, ni siquiera en
una categoría que todavía no tiene llave, y como no se vuelve atrás tampoco hay forma de reabrir las
inscripciones.
Si hace falta, más adelante se puede agregar «reabrir inscripciones» solo cuando no exista ninguna llave.

**El estado cambia con acciones, no con `PATCH`.** `POST /tournaments/{id}/start` (solo desde `draft`) y
`POST /tournaments/{id}/finish` (solo desde `in_progress`). Primero se probó un `PATCH {"status": ...}` que solo
dejaba avanzar, pero «fijar un estado» escondía condiciones previas en un endpoint genérico y permitía saltar de
`draft` a `finished`, un torneo que nunca se jugó. Con una acción por paso cada una tiene sus condiciones, sus
errores y su documentación. No se vuelve atrás: reabrir un torneo con llaves volvería a permitir categorías e
inscripciones. Repetir una acción responde 409. `status` salió del `PATCH` (cambio incompatible, aceptado en
`0.x`), que además rechaza campos desconocidos (422) para que un cliente viejo que mande `status` se entere en
vez de que se ignore en silencio. Todos los bloqueos de estado responden 409, el mismo código que usa editar un
atleta inscrito en un torneo en curso.

**Para qué existe `finished`.** Las condiciones de `finish` ya garantizan que no queda nada por jugar (toda
llave terminada, contando los `bye`, y toda categoría con 2 o más inscritos con su llave), así que no hace
falta «congelar» nada más: cargar rounds o generar llaves ya es imposible, y el nombre, la fecha y el lugar se
pueden seguir corrigiendo. Su efecto es comunicar que los resultados son **definitivos** (para el público y el
frontend externo, «en curso» = pueden cambiar) y liberar la edición de atletas, que ya no quedan atados a ese
torneo. Una categoría sin llave con 0 o 1 inscritos no bloquea el cierre (no hay nada que jugar).

**Dónde vive.** `require_tournament_status` y `require_all_matches_played` están en `app/api/lifecycle.py`,
junto a la API y no en `app/services/`, porque lanzan `HTTPException` (los servicios no dependen de FastAPI).

## 2026-10-29 — Ciclo de vida del torneo, parte 2: llaves y resultados solo en curso (0.6.0)

**Sortear y puntuar solo con el torneo en curso.** `create_bracket` y `create_round_score` exigen
`in_progress` (409 si no). Para las llaves, el motivo es que el sorteo sea un evento público y que el orden
quede forzado: primero se cierra la preparación (`/start`), recién después se sortea. Para los resultados es
una **red de seguridad**: con la regla de las llaves no puede haber combates en un torneo en borrador, y
`/finish` exige que todos los combates hayan terminado, así que hoy no hay forma de llegar a esa
respuesta por la API; se mantiene porque cuesta una línea, da un mensaje claro y protege datos que pudieran
venir de antes de esta regla. La comprobación va antes que las demás (después del 404), así que sobre un torneo
finalizado el mensaje es el del estado y no el de «el combate ya terminó».

**Cierra el hueco de la 0.4.0.** `PATCH /athletes` retira a un atleta de las categorías de torneos en borrador
sin mirar si tienen llave; como ahora un torneo en borrador nunca tiene llave, ese caso ya no puede ocurrir.

**Tests.** `generate_bracket` (`tests/conftest.py`) inicia el torneo si sigue en borrador y sortea la llave,
para que cada test no repita esa preparación; los tests que ya iniciaban el torneo a mano quedan como estaban.

## 2026-11-02 — Lista pública de inscritos en la API (0.6.0)

Mientras una categoría no tiene llave, lo útil para el público es saber quién está inscrito. Se agregó
`GET /categories/{id}/registrants` (público) y el campo `has_bracket` en `CategoryRead`. **Privacidad:** el esquema
`RegistrantRead` tiene **solo** `athlete_id`, `name` y `club`, nunca CI, fecha de nacimiento ni peso (hay menores; es
la misma regla que mantiene `GET /athletes` detrás de token), así que no hay forma de filtrar datos sensibles por
error; la consulta vive en `app/services/registrants.py`. Se descartó ampliar `GET /bracket` con una bandera
`generated` y la lista de inscritos: habría cambiado su contrato (hoy responde 404 sin llave, y eso está
documentado), habría vuelto opcionales los campos de la llave y mezclaba dos recursos. También se descartó que
`GET /registrations` respondiera datos recortados sin token: el mismo endpoint con dos formas según la autenticación
es fácil de romper. El costo es una llamada más en la página de categoría del frontend; si algún día pesa, se puede
sumar un endpoint agregado del detalle de categoría.

## 2026-11-10 — Listados de categorías e inscripciones siempre filtrados

**Revertida el 2026-11-12** (ver la entrada siguiente).

**Sin filtro no servían.** `GET /categories` y `GET /registrations` devolvían, sin parámetros, los datos de todos
los torneos de la historia: una lista que nadie necesita, que crece con cada torneo y que no se pagina. Ahora el
filtro es obligatorio, aunque rompa a quien llamaba sin él: dentro de `0.x` la API puede cambiar, y es mejor
cortarlo antes de que el frontend externo dependa de eso.

**Dos formas de exigirlo.** En categorías hay un solo filtro, así que `tournament_id` es un parámetro requerido:
FastAPI responde el 422 y `/docs` lo marca como obligatorio, lo que les sirve a los generadores de clientes. En
inscripciones vale cualquiera de los dos (`category_id` o `tournament_id`), y eso OpenAPI no lo puede expresar,
así que la comprobación está en el endpoint, con un mensaje en español. Se agregó `tournament_id` a inscripciones
para que «todos los inscritos de un torneo» no obligue a una llamada por categoría.

## 2026-11-12 — Filtros de los listados otra vez opcionales

**El filtro obligatorio rompió al frontend externo.** Al desplegar en `dev`, el admin del frontend de Kike llamaba a
`GET /registrations` sin filtro (para contar atletas por torneo y para el detalle de un torneo) y empezó a recibir
`422`; hubo que hacer rollback del servicio `dev` en Render. La decisión anterior asumía que todavía nadie dependía
del listado completo, y no era así.

**Se vuelve a la forma compatible:** sin filtros, los dos listados devuelven todo, como en la `0.5.0`. Se mantiene
el filtro nuevo `tournament_id` en inscripciones, que no rompe nada. Exigir el filtro sigue siendo la meta, pero en
tres pasos (expandir → migrar → contraer): ofrecer el filtro, que el frontend lo use, y recién entonces volverlo
obligatorio, avisando antes. Para el conteo de atletas por torneo el frontend necesita algo que hoy no existe (por
ejemplo, un conteo en el torneo); hay que resolverlo antes de contraer.

**Regla que queda:** `dev` es un entorno compartido con el frontend externo. Un cambio incompatible de la API se
acuerda con Kike antes de llegar a `dev`, no después.

## 2026-11-13 — Grado fijo del atleta y cómo se retira `belt_rank` (0.7.0)

**El grado pasa a ser un valor fijo** (`Grade`: `kup_10` … `kup_1`, `dan`), como pidió Abel: los grupos de grado
(Principiantes, Novatos, Avanzados) que vienen después necesitan comparar grados, y un texto libre («verde», «negro
1er dan») no se puede comparar. El orden del enum es el orden de los grados. Es obligatorio al crear un atleta,
aunque eso rompa a quien no lo mande: sin grado, el atleta no se podría ubicar en ningún grupo.

**`belt_rank` se retira en dos tiempos (expandir → contraer).** Dentro de `0.x` las migraciones solo agregan, para
poder volver a un tag anterior sobre una base ya migrada. Por eso la columna queda en la base: la API y el código ya
no la usan, y el modelo la llena con el valor del grado al crearlo o cambiarlo (la `0.6.0` la exige y la devuelve).
Los atletas que ya existían conservan su texto original. La columna se borra en la `1.0.0`.

**`grade` es nullable en la base y obligatorio en la API**, por la misma razón: si se vuelve a la `0.6.0`, esa versión
crea atletas sin grado. A los que ya existían la migración les asignó un grado al azar (decisión del usuario: hoy solo
hay datos de demo).

**Un campo que ya no existe se ignora** (no responde `422`): es como se comportaba la API con cualquier campo
desconocido, y cambiarlo ahora sería otro cambio incompatible sin un pedido real.

## 2026-11-14 — Solo API: se eliminaron las vistas HTML

Hasta la `0.6.0` el proyecto también tenía un panel admin y páginas públicas en HTML (Jinja2, con login por
sesión). Se eliminaron porque el frontend externo cubre las dos cosas y mantenerlas costaba en cada cambio de la
API. Si hiciera falta en una emergencia (por ejemplo, operar un torneo sin el frontend), el código está en el tag
`v0.6.0`: `app/web/`, `app/templates/`, sus routers y el `SessionMiddleware` en `app/main.py`, y las dependencias
`Jinja2` e `itsdangerous`. Hay que adaptarlo a la API de ese momento (por ejemplo, `grade` en lugar de `belt_rank`).

## 2026-11-16 — Estructura de categorías del torneo (0.8.0)

**Las categorías salen de una estructura del torneo, no se cargan a mano.** Abel quiere grupos de grado editables
(Principiantes, Novatos, Avanzados) y cada grado cubierto por un solo grupo. Los pesos y las edades dependen solo de
edad y género, nunca del grupo (así lo hacen el reglamento WT y la Copa Diamante). Entonces una categoría es una
combinación de grupo × género × división de edad × división de peso, y el torneo guarda solo esas tres listas.

**Grupos y edades se guardan como cortes.** Cada uno dice desde dónde empieza y termina donde empieza el siguiente,
así que no puede haber huecos ni solapes por cómo están guardados: la regla «cada grado en exactamente un grupo» se
cumple sola. Los pesos son límites superiores por edad y género; N límites dan N + 1 divisiones (la última es «más
de»). El último grupo siempre llega hasta Dan.

**Se edita la estructura entera de una vez** (`PUT`, en la parte 2), no grupo por grupo: mover un corte toca dos
grupos, y de a uno habría un momento con un grado sin grupo. Al guardar, las categorías se recalculan: las que
siguen correspondiendo conservan su `id` (y con él sus inscripciones y su llave), y las demás se crean o se borran.
Una categoría se identifica por grupo × género × edad × posición de su división de peso, así que cambiar un límite
de peso no le cambia el `id`. Se descartaron: crear categorías por lotes como filas de una tabla (los pesos se
repetirían en cada grupo y podrían diferir por error), validar la cobertura recién al iniciar el torneo (quedarían
estados a medias) y que cada categoría copiara su rango (los grupos dejarían de mandar).

**Las categorías históricas quedan como están.** Las de torneos anteriores se cargaron con texto libre y
color/negro; convertirlas obligaría a inventar a qué grupo iba «color». No tienen estructura ni se recalculan.

**Todo torneo nuevo nace con la estructura de la Copa Diamante** (la convocatoria real del club). Es la única
plantilla y es fija: no hacen falta plantillas editables con nombre (decidido 2026-11-18), porque cada torneo ajusta
la suya con el `PUT`. Las columnas viejas de la categoría (`age_label`,
`min_weight`…) se llenan desde la estructura, para que quien las lea no note el cambio, y `belt_group` (que sigue
en la API hasta que se retire, ver BACKLOG) se llena con negro solo en el último grupo, para poder volver a la 0.7.0.

**Festival es fijo** (pedido del club, 2026-11-16): es la primera división de edad, siempre presente, hasta 9 años
por año de nacimiento, y es una lista general por género, sin grupos de grado ni pesos. Las demás divisiones empiezan
en 10 años.

**La estructura se edita mientras el torneo está en `draft`, y el borrador es el propio torneo.** Al crear el torneo
se carga la plantilla; cada «Guardar» es un `PUT` que queda en el servidor, así que si el organizador sale y vuelve
(o cambia de dispositivo) encuentra lo último guardado. No hace falta una plantilla aparte adjunta al torneo. Lo que
todavía no se guardó lo puede conservar el frontend en el navegador, como comodidad, nunca como lo oficial. Cuando
exista «En preparación» (0.9.0), el `PUT` se limita a ese estado y la estructura queda fija al abrir inscripciones.

## 2026-11-22 — Pesos con un decimal como máximo

Las divisiones de peso van en décimas (`Hasta 48`, `48.1–55`), con los dos extremos incluidos: un peso con más
decimales (48.05) quedaría entre dos divisiones y no cabría en ninguna. Por eso todo peso que entra por la API
(atleta, categoría, límites de la estructura) admite como máximo un decimal, y con más responde `422` en vez de
redondear en silencio.

**Sigue siendo `float`, no `Decimal`:** Pydantic serializa `Decimal` como string en el JSON (`"48.1"`), lo que
cambiaría el contrato de `weight_kg`, `min_weight` y `max_weight`; y con un solo decimal el error de `float` no se
nota (el mínimo de cada división ya se redondea a décimas).

**Solo en los schemas de entrada:** los `*Read` también validan lo que devuelven, y un peso con más decimales
guardado antes de esta regla haría fallar la lectura con un 500. Los datos existentes no se tocan.

## 2026-11-23 — `category_mismatch` revisa edad y grado

**Edad por año:** edad = año del torneo menos año de nacimiento (Art. 4 WT), no por fecha exacta; así nacer el 31-dic o
el 1-ene del mismo año da el mismo resultado.

**Categorías históricas sin revisar edad ni grado:** su `min_age`/`belt_group` los cargó el admin a mano y no hay
grupo de grado contra el cual comparar; solo se revisan género y peso, como antes.

**Atleta sin grado no encaja:** solo ocurre con datos de la 0.6.0; en una categoría con grupo no se puede saber si
corresponde, y fallar es mejor que aceptar en silencio.

## 2026-11-25 — Las categorías se distinguen por su grupo; `belt_group` sale de la API (0.8.1)

**Principiantes y Novatos se veían idénticas.** Con la estructura de la 0.8.0 dos categorías de la misma edad, género
y peso solo difieren en el grupo de grado, pero la API no lo decía. Ahora la categoría trae `grade_group_id`,
`grade_group_name` y `name` (nombre completo, listo para mostrar), y `GET /categories` filtra por grupo, género y
si tiene inscritos. Los `detail` de `409` que nombran categorías usan `name`.

**`belt_group` sale de la API.** Con el grupo, «color/negro» sobra y confundía: no es lo que separa las categorías.
Es un cambio incompatible, pero la 0.8.0 se había publicado un día antes y esto la completa: se publica como 0.8.1 y
no como minor, por decisión del usuario.

**La columna `categories.belt_group` se queda**, porque dentro de `0.x` no se borran columnas y la 0.8.0 todavía la
lee (hay que poder volver a ese tag). Se borra en la 1.0.0 (ver BACKLOG).

**En las categorías históricas el cinturón va dentro de `name`:** no tienen grupo y `belt_group` es el único dato que
separa las de color de las de cinturón negro; sin él en el nombre, esas categorías se verían iguales.

## 2026-11-26 — Bases vaciadas y fuera el soporte de datos viejos

**Los datos viejos no servían.** El 2026-11-26 se vaciaron todas las bases (local, `dev` y producción) y se recargaron
con la versión actual (`scripts/reset_data.py`). Ya no hay atletas sin grado, categorías sin estructura ni torneos
anteriores a la 0.8.0.

**Se borró lo que solo cuidaba esos datos**, porque cada rama y cada test de compatibilidad costaba en cada cambio:
las columnas `athletes.belt_rank` y `categories.belt_group` y el enum `BeltGroup`, las categorías históricas con sus
ramas (el `404` de `category-structure` por torneo sin estructura, revisar solo género y peso, el cinturón dentro de
`name`) y el caso «atleta sin grado». `athletes.grade` y `categories.age_division_id` pasan a ser obligatorias.

**Es la única excepción a «dentro de `0.x` las migraciones solo agregan»** (migración `e5c7a3f90b18`). La regla sigue
para lo que venga. Consecuencia: sobre una base migrada ya no se puede volver a un tag ≤ 0.8.1.

## 2026-11-26 — Ciclo del torneo de la 0.9.0: un solo camino, fecha límite y peso oficial en la inscripción

Spec en `docs/BACKLOG.md` (0.9.0). Lo no obvio:

**Siempre se pasa por el Pesaje.** `start` solo funciona desde Pesaje. Con un atajo desde Inscripciones abiertas habría
dos caminos y el pesaje (con sus descalificaciones) se podría saltar sin querer. Para cerrar antes, el admin usa «Pasar a Pesaje»
(`close-registration`), que pone la fecha límite en ahora. Es una acción explícita como `start` y `finish`, deja en
la base cuándo se cerró de verdad, y así el `PATCH` de la fecha límite acepta solo fechas futuras.

**La fecha límite es obligatoria para abrir y se mueve solo hasta que vence.** Moverla después reabriría
inscripciones con la lista ya publicada y pesajes cargados; el estado solo avanza, como desde la 0.6.0.

**La fecha límite cae antes del día del torneo, contado en UTC.** El torneo tiene solo fecha, sin hora ni zona, y la
fecha límite se guarda en UTC; comparar en UTC evita guardar la zona del torneo (en Bolivia el tope es las 19:59 de la
víspera, sin problema porque el pesaje va antes del torneo). La regla vale solo mientras la fecha límite se puede
mover: después es historia, y un torneo postergado tiene que poder cambiar su fecha.

**Pesaje calculado, no guardado.** El torneo entra en Pesaje cuando vence la fecha: el estado se calcula al leer, con
una función pura del torneo y la hora. Sin cron ni escrituras al leer.

**El peso oficial vive en la inscripción.** Cada inscripción guarda sus pesajes y si quedó descalificada. El
`weight_kg` del atleta sigue siendo el peso declarado: pisarlo borraría el historial de cada torneo y chocaría con la
regla de retiro al editar un atleta (2026-10-24).

**Oculto sin token, todo con token, en los mismos endpoints.** Sin token no se ven los torneos en preparación ni la
lista de inscritos antes del Pesaje; con token se ve todo. El token protege la API, no decide qué muestra la vista
pública: esa vista nunca los muestra, haya sesión o no (regla del frontend). No contradice 2026-11-02 («el mismo
endpoint con dos formas es fácil de romper»): la forma de la respuesta es la misma, solo cambia qué filas se ven.

**Pesaje sin tolerancia.** No se aplican los 100 g del Art. 9 de WT. Si el primer pesaje no entra, el admin elige
segundo pesaje o descalificación; si el segundo no entra, queda descalificado.

**`start` cierra el pesaje.** Los `pending` pasan a `no_show` (no se presentaron) y los que quedaron sin decidir
(`failed_first`, `second_allowed`) a `disqualified`: pesaron fuera de la categoría y no pasaron un segundo pesaje. `start`
devuelve a los `no_show` para que el frontend los muestre.

**El pesaje se puede reiniciar mientras el torneo está en Pesaje.** `DELETE /registrations/{id}/weigh-in` vuelve la
inscripción a `pending` y borra los pesos, para corregir un tipeo (decisión del usuario). Tras `start` ya no.

**El estado del pesaje es público desde el Pesaje; los kilos nunca.** `GET /categories/{id}/registrants` suma
`weigh_in_status`, pero los pesos solo salen con token (hay menores).

**Editar el peso declarado sigue dando 409 si deja de encajar.** En Pesaje o En curso el atleta no puede cambiar su
`weight_kg` a uno que no encaje en su categoría, aunque el peso oficial ya sea el del pesaje. Se dejó como estaba por
YAGNI.

**La migración `a7c2e41d9b35` deja en `pending` las inscripciones de torneos en curso o finalizados.** No se convierten
a `cleared`: no hay datos reales (producción vacía desde 2026-11-26, `dev` se recarga con el seed).

**Los descalificados van en la llave y no ganan nada.** El sorteo los empareja primero con habilitados, para que el
descalificado pierda contra alguien que sigue. Entre dos descalificados no avanza nadie (se descartó que avance uno
al azar: un descalificado aparecería en rondas siguientes). Si todos quedan descalificados, no hay ganador ni puntos.

**Festival sin llaves; exhibición armada a mano (0.10.0).** Festival es solo una lista de varones y otra de damas:
los combates se organizan en persona y no se registran (Abel, 2026-11-26). Todos llevan oro y cada niño suma 7 al
ranking, como un oro. Las llaves de
exhibición se arman a mano con atletas elegidos por el organizador, varias por torneo. A exhibición solo van los que
se quedaron sin pelea; no suma al ranking, porque ya sumaron su punto de «sin pelea».
