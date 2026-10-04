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
