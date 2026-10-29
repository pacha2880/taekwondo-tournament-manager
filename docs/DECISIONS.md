# Decisiones de arquitectura (ADR liviano)

Registro corto de decisiones no obvias, con el porqué, para no tener que re-derivar el
razonamiento más adelante.

## 2026-09-11 — Jinja2 en vez de SPA separado

Se eligió server-side rendering con FastAPI + Jinja2 en una sola app, en vez de una API
separada + frontend en React/Vue. Motivo: el objetivo es un despliegue gratuito simple (un
solo servicio) y que el foco de aprendizaje sea el backend, que es lo que evalúa el puesto al
que se está aplicando. htmx queda como mejora incremental opcional, no bloqueante.

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

## 2026-09-22 — Fase 5: diseño propio y minimalista, no clonar sitios de marketing

Se consideró usar como referencia visual el sitio de una escuela de taekwondo real
(marketing/institucional, con tienda y noticias), pero se descartó: es un tipo de producto
distinto (vender clases, no mostrar datos de un torneo en vivo). Se optó por un diseño propio
y lo más simple posible — la parte visual queda deliberadamente básica, para que decisiones
de diseño "de verdad" se puedan tomar después (por alguien más, o más adelante) sin tocar
lógica de negocio, ya que las plantillas Jinja2 están separadas de `app/services`/`app/api`.

Decisiones concretas de la Fase 5:
- **CSS**: Bootstrap 5 vía CDN (un `<link>`, sin build step) — consistente con "tecnología
  simple", da componentes listos (navbar, list-group, badges) sin escribir CSS a mano.
  Paleta: sin personalización por ahora (Bootstrap por defecto); si se quiere un esquema
  rojo/azul (colores reales de protectores, y ya son los nombres que usa el modelo de datos
  — `athlete_red_id`/`athlete_blue_id`) queda como mejora visual posterior, no bloqueante.
- **Navegación**: tres niveles siguiendo la jerarquía de datos — `/` (lista de torneos) →
  `/torneos/{id}` (categorías de ese torneo) → `/categorias/{id}` (llave + resultados de esa
  categoría). Sin buscador ni filtros.
- **Vista de la llave**: lista de texto agrupada por ronda (no un árbol visual con líneas
  conectoras). Cada combate muestra los dos atletas, su estado (`pending`/`bye`/`finished`),
  el ganador si ya lo hay, y el puntaje de cada round si el combate ya se jugó.
- **Sin auto-refresh todavía**: la página se recarga manualmente. El auto-refresh en vivo
  (polling con htmx) queda anotado como el primer ítem de la Fase 9 (mejoras post-deploy),
  junto con cualquier otra mejora que se nos ocurra en el camino — deliberadamente no se
  implementa antes de tener el sistema desplegado y funcionando de punta a punta.

## 2026-09-25 — Fase 5.5: centralizar la traducción de enums, no traducirlos ad-hoc

Las plantillas de la Fase 5 imprimían `.value` de los enums del modelo directo, mostrando
"draft", "male", "bye" en la página pública — los enums se guardan en inglés a propósito
(identificadores internos, ver `app/models.py`), pero nadie los estaba traduciendo antes de
mostrarlos. Se centralizó la traducción en `app/web/labels.py` en vez de traducir en cada
plantilla, por dos razones: (1) un solo lugar para mantener las traducciones, y (2) permite
un guardrail automático simple — un test que falla si cualquier plantilla (actual o futura,
incluida la Fase 6) usa `.value` directo, sin necesidad de saber de antemano qué enum es.

Detalle técnico: los enums de este proyecto heredan de `(str, enum.Enum)`, lo que los hace
comparables e hasheables como strings — por eso `_LABELS` en `labels.py` es un diccionario
anidado por clase de enum (`{TournamentStatus: {...}, MatchStatus: {...}}`) en vez de uno
plano: dos enums distintos pueden compartir el mismo valor string (`TournamentStatus.FINISHED`
y `MatchStatus.FINISHED` son ambos `"finished"`), y un diccionario plano los trataría como la
misma clave.

## 2026-09-26 — Fase 6: el admin llama directo a las funciones de la API, no las reimplementa

La pantalla admin necesita las mismas reglas de negocio que ya existen en `app/api/*.py`
(género debe coincidir, peso en rango, no doble inscripción, etc.). En vez de reescribir esas
validaciones para los formularios HTML, `app/web/admin.py` importa y llama directo a las
funciones de los routers de la API (ej. `create_registration` de `app/api/registrations.py`)
como funciones Python normales, pasándoles una sesión de DB explícita. Esto es seguro porque
`Depends(get_db)` es solo un valor por defecto de FastAPI que no se usa cuando el llamador
pasa `db` explícitamente. El admin atrapa `HTTPException`/`ValidationError` y re-renderiza la
página con el error en vez de dejarlo pasar como JSON crudo.

Login: sesión simple con `SessionMiddleware` (cookie firmada con `SECRET_KEY`) contra un único
usuario definido en `ADMIN_USERNAME`/`ADMIN_PASSWORD` — no hay tabla de usuarios ni roles,
suficiente para un solo administrador por torneo. Una dependencia (`require_admin`) protege
cada ruta; en vez de devolver un 401 plano, lanza una excepción custom (`NotAuthenticated`)
capturada por un exception handler global que redirige a `/admin/login` — mejor experiencia
para un flujo pensado para navegador, no para consumo por API.

## 2026-09-29 — Revertir "MatchRead solo ids": agregar nombres de atletas a la API

En la Fase 5 se decidió que `MatchRead` expusiera solo ids de atletas (no nombres), para no
acoplar el contrato JSON a una necesidad de presentación. En la práctica, los tres
consumidores que existen hoy (pantalla pública, pantalla admin, y cualquier llamada directa a
la API) necesitan los nombres siempre — nadie quiere ids solos. Mantener la API "pura" estaba
protegiendo un caso de uso hipotético (un consumidor futuro que sí quisiera solo ids) a costa
de un problema real y actual: la misma lógica de resolución de nombres (batch query para
evitar N+1) estaba duplicada en `app/web/public.py` y `app/web/admin.py` (hoy
`app/web/admin/category_workspace.py`).

Se agregó `athlete_red_name`/`athlete_blue_name`/`winner_name` a `MatchRead`
(`app/schemas.py`), y se centralizó la resolución en `resolve_athlete_names(db, matches)`
(`app/services/brackets.py`) — la única función que hace esa consulta batch. La reusan
`app/api/brackets.py`, `app/api/matches.py`, `app/web/public.py` y
`app/web/admin/category_workspace.py`; ninguno vuelve a escribirla por su cuenta.

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
se muestra en la esquina de cada página (texto chico, fijo abajo a la derecha) y en `/health`,
que permite saber qué versión corre en producción sin abrir el navegador. Exponerla es
inofensivo en esta app y útil para verificar un deploy.

**Migraciones solo aditivas dentro de `0.x`** (columnas nuevas opcionales; nunca borrar ni
renombrar). Es lo que hace seguro volver a un tag anterior: el código viejo sigue funcionando
sobre una base ya migrada. Un cambio destructivo se haría en dos versiones (agregar lo nuevo
y migrar el código, y recién en una versión posterior borrar lo viejo).

**`CHANGELOG.md`** en formato Keep a Changelog, y un test que falla si su última versión
publicada no coincide con `app/version.py`, para que no se desincronicen.

**Un único entorno de plantillas** (`app/web/templating.py`): antes, `public.py` y
`admin/_shared.py` creaban cada uno su `Jinja2Templates` y registraban los mismos filtros por
duplicado. Para agregar la versión como global sin sumar una tercera copia se unificaron.

**Orden del backlog (tres pasadas de análisis):** 0.2.0 admin más seguro, 0.3.0 datos de
atletas, 0.4.0 ciclo de vida del torneo, 0.5.0 campeones, 0.6.0 en vivo. La 0.3.0 va antes
que el ciclo de vida a propósito: tiene la única migración de esquema y es simple, así que
ensaya el camino commit → push → deploy → migración → rollback antes de los cambios de
comportamiento. Detalle en `docs/BACKLOG.md`.

## 2026-10-15 — API protegida con login y JWT (0.2.0)

**El problema.** Ningún endpoint de `/api/v1` exigía autenticación: el admin web usa sesión por
cookie, pero la API quedó abierta, así que cualquiera que abriera `/docs` podía crear y modificar
datos en producción. Se hizo visible al aparecer un consumidor externo (el frontend de un amigo,
en otra tecnología), pero el agujero existía desde antes.

**Token en la cabecera, no cookie.** Con un frontend en otro dominio, la cookie cruzada exige
`SameSite=None`, `credentials` en CORS, la bloquean cada vez más navegadores y abre la puerta a
CSRF. Un token que el frontend agrega a mano en `Authorization: Bearer` no sufre CSRF (una página
ajena no puede hacer que el navegador lo adjunte sola). El admin web sigue con cookie de sesión.

**JWT (HS256, PyJWT) y no un token propio de `itsdangerous`.** Para el servidor son equivalentes
(ambos *stateless*), pero JWT es el estándar: el frontend de otra tecnología puede leer el `exp`,
Swagger y las librerías lo entienden, y es lo que se espera en el mercado. El costo es una
dependencia pequeña. Al verificar se fija `algorithms=["HS256"]` (evita el error clásico de
aceptar `alg: none`; hay un test) y se exigen `exp` y `sub`.

**Login con formulario OAuth2** (`POST /api/v1/auth/login`): es la forma estándar y hace que
Swagger muestre el botón **Authorize**. Mismo usuario y clave del admin; la comparación es de
tiempo constante y vive en `app/auth.py`, compartida con el login del admin web. `SECRET_KEY` y las
credenciales se leen desde `app/config.py` en vez de tres lugares distintos.

**8 horas, sin renovación automática.** El token no se puede revocar antes de vencer (nadie lo
guarda). Ocho horas cubren una jornada de torneo; un refresh token agregaría almacenamiento,
rotación y revocación que no se justifican hoy. El "botón de pánico" es cambiar `SECRET_KEY`
(invalida todos los tokens y también las sesiones del admin web).

**Qué es público y qué no.** Públicos: torneos, categorías, clubes, llaves y combates (solo
nombres). Con token: todo `POST`/`PATCH`, y `GET` de atletas e inscripciones, porque devuelven fecha
de nacimiento y peso y hay menores. Si el frontend externo necesita mostrar "quiénes están
inscritos" antes de que exista la llave, se agregará un endpoint público que devuelva solo nombre
y club.

**Cómo se aplica.** La constante `ADMIN_ONLY = [Depends(require_api_admin)]` se pasa como
`dependencies=ADMIN_ONLY` en cada endpoint protegido. El admin web **no** se ve afectado: sus
handlers llaman a las funciones de `app/api/*.py` directamente (ver la decisión de la Fase 6) y
las dependencias de FastAPI solo corren cuando la petición entra por HTTP.

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
`allow_credentials=False`: así tampoco hay riesgo de que un origen permitido reutilice la sesión del
admin web. Se permiten solo `GET`, `POST`, `PATCH` y `OPTIONS`, y las cabeceras `Authorization` y
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

**Qué se muestra en `/docs`.** Solo la API y `/health`: las páginas HTML del admin y de la parte pública
se ocultan con `include_in_schema=False` en `include_router` (en FastAPI 0.141 los routers incluidos
quedan anidados, así que se pasa ahí y no en cada router). Antes aparecían 19 páginas HTML mezcladas con
la API, lo que además exponía la estructura del panel de administración.

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
repetidos o con restos de la ruta, o si aparecen páginas HTML en el esquema. Se comprobó con pruebas de
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
cambia nada; repetida con el parámetro, aplica el cambio y borra esas inscripciones. El admin usa la misma
función: vuelve a mostrar el formulario con el aviso (la excepción `WithdrawalNotConfirmed` lo distingue de los
demás `409`) y un botón "Confirmar y retirar" que reenvía el formulario con el parámetro. La validación de
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

## 2026-10-26 — El servidor numera los rounds y el admin confirma antes de guardar (0.5.0)

**El número de round lo asigna el servidor, no el cliente.** El backlog planteaba fijar el número solo en el
formulario del admin, pero el hueco estaba en la API: `round_number` era obligatorio y solo se rechazaba un
número repetido, así que se podía cargar el round 5 sin el 1 o dejar huecos, y el frontend externo habría
heredado el problema. Ahora `RoundScoreCreate` solo lleva `red_points` y `blue_points`, y `record_round`
asigna `rounds ya cargados + 1`; la respuesta (`RoundScoreRead`) sigue incluyendo `round_number`. Se
eliminó `DuplicateRound`, que ya no puede ocurrir. Sin capa de compatibilidad (estamos en `0.x`, y Pydantic
ignora el campo si alguien todavía lo envía). **Costos aceptados:** (1) la restricción única
`uq_round_per_match` sigue siendo la red de seguridad si dos envíos simultáneos calculan el mismo número: el
segundo falla con un error 500 en lugar de un mensaje claro; la ventana de confirmación deshabilita el botón
tras el primer clic, así que es poco probable. (2) El admin muestra «Round N» calculado al renderizar la
página; si se carga un round desde otra pestaña, un envío desde una página vieja se numera con el que
corresponde en ese momento, no se rechaza.

**Ventana de confirmación genérica.** Todo `<form method="post" data-confirm="Título">` del admin abre una
ventana de Bootstrap con los datos que el usuario escribió (etiqueta y valor de cada campo; para los
`<select>`, el texto de la opción elegida) y los botones Cancelar / Confirmar; `data-confirm-note` agrega una
aclaración. El script vive una sola vez en `admin/base.html`, junto con el JavaScript de Bootstrap 5.3.3 del
mismo CDN que el CSS. Queda fuera solo el login. «Salir» y el cambio de estado del torneo también piden
confirmación; el del estado avisará además que es irreversible cuando la 0.6.0 prohíba volver atrás; en «Editar atleta», la pantalla que
ya avisa «Este cambio retira al atleta de…» no abre una segunda ventana. Como los tests no ejecutan
JavaScript, `tests/test_admin_confirmations.py` revisa en las plantillas que ningún formulario POST nuevo
olvide el atributo, y el comportamiento de la ventana se verificó a mano en el navegador.

**Un formulario que falla conserva lo escrito.** Cada manejador de creación pasa lo que recibió con
`echo_form(...)` (`app/web/admin/_shared.py`, convierte `None` en vacío) y la plantilla lo vuelve a poner en
los campos (`form.<campo>`); en los `<select>` se marca la opción elegida. Es solo de la vista: la API no
cambia. Es una regla para todo formulario nuevo del admin; los de editar ya lo hacían.

**No se agrega corrección de rounds ya cargados.** Era la decisión pendiente del backlog: se resolvió que
alcanza con el número fijo y la confirmación con los puntos a la vista. Corregir un round obligaría a
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
inscripciones. Por eso el cambio de estado pide confirmación en el admin avisando que cierra la preparación.
Si hace falta, más adelante se puede agregar «reabrir inscripciones» solo cuando no exista ninguna llave.

**El estado cambia con acciones, no con `PATCH`.** `POST /tournaments/{id}/start` (solo desde `draft`) y
`POST /tournaments/{id}/finish` (solo desde `in_progress`). Primero se probó un `PATCH {"status": ...}` que solo
dejaba avanzar, pero «fijar un estado» escondía condiciones previas en un endpoint genérico y permitía saltar de
`draft` a `finished`, un torneo que nunca se jugó. Con una acción por paso cada una tiene sus condiciones, sus
errores y su documentación, y el admin muestra un solo botón según el estado («Cerrar inscripciones e iniciar
torneo», «Finalizar torneo»). No se vuelve atrás: reabrir un torneo con llaves volvería a permitir categorías e
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
En el admin, cuando el torneo ya empezó, los formularios de crear categoría e inscribir se reemplazan por un
aviso en vez de dejar que fallen.
