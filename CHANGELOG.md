# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y versionado
según [Semantic Versioning](https://semver.org/lang/es/). La versión vive en
[`app/version.py`](app/version.py) y se muestra en `/health`.

Mientras la versión sea `0.y.z` (desarrollo inicial) la API puede cambiar entre versiones
minor. Dentro de `0.x`, las migraciones de base de datos solo agregan (columnas nuevas
opcionales; nunca borrar ni renombrar), para que volver al tag de una versión anterior siga
funcionando sobre una base ya migrada. Única excepción: la migración que borra las columnas viejas (ver
`[0.8.2]`), tras la cual no se puede volver a la 0.8.1 o anterior.

## [Unreleased]

## [0.9.0-alpha.1] - 2026-11-27

Primera parte de la 0.9.0 (bloque 1 del BACKLOG): estados, fecha límite y visibilidad. El Pesaje (bloque 2) y las
llaves al iniciar (bloque 3) llegan en las siguientes.

### Changed (incompatible)
- **Ciclo nuevo del torneo:** `draft` (en preparación) → `registration_open` → `weigh_in` (pesaje) → `in_progress` →
  `finished`, un solo camino. `draft` ya no admite inscripciones: `POST` y `DELETE /api/v1/registrations` solo
  funcionan en `registration_open` (`409` en otro estado). `POST /tournaments/{id}/start` solo funciona desde
  `weigh_in`.
- **Visibilidad sin token:** las lecturas públicas aceptan token opcional. Sin token, los torneos en `draft` no
  aparecen (`GET /tournaments`, `GET /categories`) y su torneo, estructura, categorías, inscritos y llaves responden
  `404`; `GET /categories/{id}/registrants` responde `403` hasta el Pesaje, y el filtro `has_registrants` de
  `GET /categories` también (`403` salvo con un `tournament_id` ya en `weigh_in` o después). Un token inválido o
  vencido responde `401` también en estas lecturas.
- Editar un atleta que deja de encajar en su categoría: el retiro con `confirm_withdrawal` vale en
  `registration_open`, y el `409` sin salida vale en `weigh_in` además de `in_progress`.

### Added
- `registration_deadline` en los torneos: se fija con `PATCH /api/v1/tournaments/{id}` (ISO 8601 con zona horaria,
  futura y antes del día del torneo contado en UTC; se devuelve en UTC). Se puede mover mientras no venció; `null`
  solo en `draft`. Mientras no venció, tampoco se puede mover la fecha del torneo a ese día o antes (`422`).
- `POST /api/v1/tournaments/{id}/open-registration`: de `draft` a `registration_open`, con una fecha límite futura.
- `POST /api/v1/tournaments/{id}/close-registration`: el botón «Pasar a Pesaje»; cierra las inscripciones ya (la
  fecha límite pasa a ser ahora).
- `weigh_in` se calcula al leer: un torneo con inscripciones abiertas pasa solo a Pesaje cuando vence la fecha límite.

### Fixed
- `PATCH /api/v1/tournaments/{id}` con `null` en `name`, `date` o `location` respondía `500`; ahora `422`.

### Migración
- `f1a9d3b72c60` solo agrega `tournaments.registration_deadline` y los estados nuevos; no convierte datos. Un torneo
  `draft` que ya existía queda en preparación y sin fecha límite. Tras desplegar, `dev` se recarga con
  `scripts/reset_data.py dev --seed` (producción está vacía).

## [0.8.2] - 2026-11-26

### Removed
- **Sin categorías históricas:** todo torneo tiene estructura de categorías. `GET` y `PUT
  /api/v1/tournaments/{id}/category-structure` ya no responden `404` por un torneo sin estructura.
- La migración borra las columnas viejas (`athletes.belt_rank` y `categories.belt_group`) y vuelve obligatorios
  `athletes.grade` y `categories.age_division_id`. No se puede volver a la 0.8.1 o anterior sobre una base migrada.

## [0.8.1] - 2026-11-25

### Added
- **Nombre completo de la categoría:** `name` en cada categoría, listo para mostrar (por ejemplo
  `Principiantes · Cadete · Masculino · 37.1–41 kg`). Antes Principiantes y Novatos se veían idénticas.
- **Grupo de grado de la categoría:** `grade_group_id` y `grade_group_name`. Son nulos en Festival y en las categorías
  anteriores a la 0.8.0.
- **Filtros de `GET /api/v1/categories`:** `grade_group_id`, `gender` (`male` / `female`) y `has_registrants`
  (`true`: con inscritos; `false`: sin ninguno), combinables entre sí y con `tournament_id`. Con
  `has_registrants=true` se ocultan las categorías vacías.

### Changed
- El `detail` de los `409` que nombran categorías (`PATCH /api/v1/athletes/{id}` y
  `POST /api/v1/tournaments/{id}/finish`) usa el nombre completo (`name`).

### Removed
- **Incompatible — `belt_group`:** ya no sale en las categorías. Para mostrar la categoría usá `name` (o
  `grade_group_name`). En las categorías anteriores a la 0.8.0, que no tienen grupo, el cinturón (de color o negro)
  va dentro de `name`. La columna sigue en la base y se borra en la 1.0.0.

## [0.8.0] - 2026-11-24

### Added
- **Categorías en las que encaja un atleta:** `GET /api/v1/athletes/{id}/eligible-categories?tournament_id=` (requiere
  token) devuelve, ordenadas por id, las categorías de ese torneo que cumplen la misma regla que `POST /registrations`,
  sin mirar si ya está inscrito. Con la estructura de la Copa Diamante normalmente es una sola.
- **Atletas que encajan en una categoría:** `GET /api/v1/categories/{id}/eligible-athletes` (requiere token) devuelve,
  ordenados por nombre, los atletas que cumplen la misma regla que `POST /registrations`, incluidos los ya inscritos.
- **Estatura del atleta:** campo opcional `height_cm` (entero, 50 a 250 cm) al crear y editar atletas; en
  `PATCH`, `null` la borra. No se usa en ninguna regla de categorías y no sale en los endpoints públicos.
- **Estructura de categorías del torneo:** `GET /api/v1/tournaments/{id}/category-structure` (público) devuelve los
  grupos de grado, las divisiones de edad y las divisiones de peso del torneo. Todo torneo nuevo nace con la
  estructura de la Copa Diamante y con todas sus categorías ya creadas (grupo × género × edad × peso; 212 en total).
  Festival (hasta 9 años por año de nacimiento) está siempre y es una lista general por género, sin grupos de grado
  ni pesos.
- **Editar la estructura de categorías:** `PUT /api/v1/tournaments/{id}/category-structure` reemplaza de una vez
  los grupos de grado y las divisiones de edad y peso (Festival es fijo y no se envía), solo con el torneo en
  `draft`. Las categorías se recalculan: las que siguen correspondiendo conservan su id. Si la estructura no es
  válida responde `422` sin cambiar nada; con `validate_only=true` devuelve cómo quedaría sin guardar.
  Los torneos anteriores no tienen estructura (responde `404`) y sus categorías no cambian.

### Changed
- **Incompatible — pesos con un decimal como máximo:** `POST`/`PATCH /api/v1/athletes` (`weight_kg`) responden
  `422` si el peso tiene más de un decimal (`48.05`). Antes se aceptaba, y ese atleta no cabía en ninguna división de
  peso. Los datos ya guardados no cambian.
- **Incompatible — `POST /api/v1/registrations` revisa edad y grado:** en las categorías con estructura responde `422`
  si la edad del atleta (año del torneo menos año de nacimiento) no está entre `min_age` y `max_age`, o si su grado
  no pertenece al grupo de la categoría (un atleta sin grado no encaja en categorías con grupo). Antes solo se
  revisaban género y peso. Las categorías anteriores a la 0.8.0 siguen revisando solo género y peso.
  `PATCH /api/v1/athletes/{id}` aplica la misma regla de retiro (409 en torneo en curso, `confirm_withdrawal` en
  borrador) también al cambiar **grado** o **fecha de nacimiento**, no solo género o peso. El `detail` del 409 en
  torneo en curso cambió a «No se puede hacer este cambio: …».

### Removed
- **Incompatible — `POST /api/v1/categories`:** ya no existe (responde `405`). Las categorías salen solo de la
  estructura del torneo (`PUT /api/v1/tournaments/{id}/category-structure`). Las categorías de torneos anteriores
  se siguen leyendo igual.

### Fixed
- **CORS permite `PUT`:** desde un navegador, `PUT /api/v1/tournaments/{id}/category-structure` fallaba en el
  *preflight* (`400`) aunque el origen estuviera autorizado.
- **`Infinity` o `NaN` en un número del body** responden `422` en toda la API. Antes un peso `Infinity` se guardaba y
  hacía fallar con `500` cada lectura de ese atleta o categoría.
- **Ids de la ruta y de los filtros fuera del rango de `int4`** (`/clubs/{id}`, `?tournament_id=`, `?category_id=`…)
  responden `422` en vez de `500` en Postgres. Los ids dentro del rango que no existen siguen dando `404`.
- **Textos y números que no caben en la base** responden `422` en vez de `500`: nombres de club y atleta (hasta 120
  caracteres), nombre y lugar del torneo (150), y los enteros de rounds e ids del body
  (hasta 2.147.483.647). El límite de cada texto sale como `maxLength` en `/docs`.

## [0.7.0] - 2026-11-15

### Removed
- **Solo queda la API:** se eliminaron el panel admin y las páginas públicas en HTML (y su login por sesión).
  La interfaz es el frontend externo. `/` redirige a `/docs`. La API no cambia.

### Changed
- **Incompatible — importante para quien use la API:** los atletas tienen un **grado** fijo (`grade`: `kup_10` …
  `kup_1` y `dan`) en lugar del cinturón en texto libre. `POST /api/v1/athletes` exige `grade` (sin él, o con un
  valor que no está en la lista, responde `422`); `PATCH` lo acepta para cambiarlo. `belt_rank` deja de existir en
  la API: ya no se devuelve, y si se envía se ignora. A los atletas que ya existían se les asignó un grado al azar.

### Fixed
- **CORS permite `DELETE`:** desde el navegador, un frontend en otro dominio no podía retirar inscripciones
  (`DELETE /api/v1/registrations/{id}`, agregado en la 0.6.0): el navegador bloqueaba la llamada.
- `GET /api/v1/categories` y `GET /api/v1/registrations` devuelven siempre el mismo orden (el de creación). Antes
  no tenían orden y en Postgres podía cambiar entre una llamada y otra.

## [0.6.0] - 2026-11-12

### Added
- **Retirar a un atleta de una categoría:** `DELETE /api/v1/registrations/{id}` (responde `204`) y un botón
  «Retirar» con confirmación en cada fila de inscritos del admin. Solo con el torneo en `draft`; después
  responde `409` y el botón no aparece.
- `GET /api/v1/registrations` acepta el filtro `tournament_id` (todas las inscripciones de un torneo), combinable
  con `category_id`. Es un agregado: sin filtros sigue devolviendo todas.

### Changed
- **Incompatible — importante para quien use la API:** el estado de un torneo ya no se cambia con
  `PATCH /api/v1/tournaments/{id}` (enviar `status` ahora responde `422`). Se usan dos acciones:
  `POST /api/v1/tournaments/{id}/start` (de `draft` a `in_progress`) y `POST /api/v1/tournaments/{id}/finish`
  (de `in_progress` a `finished`, solo si no quedan combates por jugar). El estado no vuelve atrás: repetir
  una acción o saltar un paso responde `409`.
- **Incompatible — importante para quien use la API:** `POST /api/v1/matches/{id}/rounds` vuelve a exigir
  `round_number`, que tiene que ser el siguiente al último round guardado; si no, responde `409` sin guardar
  nada. Evita que un reenvío (la respuesta se perdió por mala señal) quede guardado como el round siguiente y
  cierre el combate con un ganador equivocado.
- **Importante para quien use la API:** las categorías y las inscripciones solo se crean mientras el torneo
  está en `draft`; con el torneo ya iniciado, `POST /api/v1/categories` y `POST /api/v1/registrations`
  responden `409`. Con esto, al pasar a «en curso» se cierra la preparación del torneo.
- En el admin, cuando el torneo ya empezó, los formularios de crear categoría e inscribir atleta se
  reemplazan por un aviso. El selector de estado se reemplaza por un solo botón según el estado
  («Cerrar inscripciones e iniciar torneo» o «Finalizar torneo»), con confirmación que avisa que es irreversible.
- **Importante para quien use la API:** las llaves (`POST /api/v1/categories/{id}/bracket`) y los resultados
  (`POST /api/v1/matches/{id}/rounds`) solo se aceptan con el torneo en curso; con el torneo en `draft` o
  `finished` responden `409`. Hay que iniciar el torneo antes de sortear.
- En el admin, con el torneo todavía en borrador, el botón «Generar llave» se reemplaza por un aviso.
- En la página pública de una categoría sin llave (con inscripciones abiertas, o en curso antes del sorteo)
  se muestra la lista de inscritos: solo nombre y club.
- **Nuevo en la API:** `GET /api/v1/categories/{id}/registrants`, público, con los inscritos de la categoría
  (solo `athlete_id`, `name` y `club`), y el campo `has_bracket` en las categorías para saber si mostrar la
  llave o la lista de inscritos. Son agregados: no rompen nada.
- En las llaves, del sitio público y del admin, el club de cada atleta aparece entre paréntesis junto a su
  nombre. La API sigue devolviendo solo el nombre.
- El estado `draft` se muestra como «Inscripciones abiertas» en lugar de «Borrador» (solo el texto; el valor
  `draft` de la API no cambia).

## [0.5.0] - 2026-10-26

### Added
- El admin **pide confirmación antes de guardar**: crear club, atleta, torneo o categoría, inscribir un
  atleta, generar una llave, cargar un round, guardar cambios de un atleta o un club, cambiar el estado
  del torneo y cerrar sesión abren una ventana con los datos que se van a enviar. La de los rounds avisa
  que no se pueden editar después.

### Changed
- **Importante para quien use la API:** `POST /api/v1/matches/{id}/rounds` ya no recibe `round_number`,
  solo `red_points` y `blue_points`. El servidor numera los rounds (1, 2, 3…) en el orden en que se
  cargan y devuelve el número asignado; un `round_number` enviado se ignora. Desaparece el error por
  round repetido.
- En el admin, el formulario de resultados muestra el número del round como texto fijo en vez de un
  campo editable.
- Si un formulario del admin falla (por ejemplo, un CI repetido), se vuelve a mostrar con todo lo que se
  había escrito en vez de vaciarse.

## [0.4.0] - 2026-10-25

### Added
- Cada atleta puede tener un **CI** (cédula de identidad), opcional porque hay niños que todavía no
  tienen. Si se informa es único y de 5 a 9 dígitos con, si corresponde, un complemento de 2 caracteres
  separado por guion (`1234567` o `1234567-1A`), sin lugar de expedición. Se guarda sin espacios y en
  mayúsculas. Un CI repetido responde `409`. Está en `POST /api/v1/athletes`, en las respuestas de
  atletas e inscripciones (`null` si no tiene) y en el formulario del admin. Migración
  `a4f1c2e8b7d3`: agrega la columna; los atletas ya cargados quedan sin CI.
- **Editar atletas**: `PATCH /api/v1/athletes/{id}` y botón "Editar" en el admin. Solo cambian los campos
  que se envían; `ci` con `null` o vacío lo borra, y el atleta puede cambiar de club. Reglas cuando el
  cambio de **género o peso** afecta inscripciones: en un torneo **en curso** se rechaza (`409`) si deja de
  cumplir las reglas de la categoría (si sigue encajando, se guarda); en un torneo **en borrador**, si deja
  de cumplirlas hay que confirmar (`?confirm_withdrawal=true`; en el admin, botón "Confirmar y retirar") y
  se lo retira de ella; en un torneo **finalizado** se permite y la inscripción queda como estaba.
- **Buscar atletas** por nombre o CI: `GET /api/v1/athletes?q=texto` y cuadro de búsqueda en la lista del
  admin. Busca el texto dentro del nombre o del CI sin distinguir mayúsculas ni tildes (`perez` encuentra a
  `Pérez`); sin `q` devuelve todos, como antes.
- **Editar clubes**: `PATCH /api/v1/clubs/{id}` y botón "Editar" en el admin (el nombre sigue siendo único).

### Changed
- Con `APP_ENV=production` o `staging`, un `SECRET_KEY` de menos de 32 bytes ahora impide arrancar la
  app (antes solo se avisaba en los logs).

## [0.3.0] - 2026-10-22

### Added
- CORS configurable con la variable `CORS_ORIGINS` (lista de orígenes separados por comas): permite
  que un frontend en otro dominio lea la API desde el navegador. Sin definirla no se permite ningún
  origen. Con `APP_ENV=production` la app se niega a arrancar si contiene `*`. Sin cookies: el token
  viaja en la cabecera `Authorization`.
- `APP_ENV=staging`, para el servicio de pruebas (`dev`): exige las mismas credenciales propias que
  `production`, pero sí permite `CORS_ORIGINS=*`.
- Documentación de la API en español en `/docs`, `/redoc` y `/openapi.json`: descripción general
  (autenticación, errores, advertencias), grupos con su explicación, y para cada endpoint un resumen,
  una descripción y los errores que puede devolver (`401`, `404`, `409`…). Cada campo y cada enum
  explican su significado. Un test falla si una operación o un campo quedan sin documentar.
- `docs/API.md`: guía para quien consume la API (cómo leer una llave, flujo de ejemplo con `curl`).

### Changed
- `/docs` ya no muestra las páginas HTML del admin y de la parte pública: solo la API y `/health`.
- Los grupos (`tags`) pasan a español: Autenticación, Torneos, Categorías, Clubes, Atletas,
  Inscripciones, Llaves, Combates y Sistema. **Importante para quien genere un cliente:** muchos
  generadores los usan para nombrar clases.
- Los `operationId` pasan a ser el nombre de la función (`create_club`, `list_tournaments`…) en vez de
  `create_club_api_v1_clubs_post`. Quien ya hubiera generado un cliente verá cambiar los nombres de
  sus métodos.
- El formulario de `POST /api/v1/auth/login` declara solo `username` y `password` (antes mostraba
  además `grant_type`, `scope`, `client_id` y `client_secret`, que no se usaban). El botón
  **Authorize** de Swagger sigue funcionando igual.
- El título de `/docs` muestra la versión leída de `app/version.py`.

## [0.2.0] - 2026-10-15

La API deja de estar abierta: cualquiera que abriera `/docs` podía crear y modificar datos.
Incluye también tres mejoras del admin. **Cambio incompatible** para quien escribiera sin token.

### Added
- `POST /api/v1/auth/login`: inicio de sesión de la API (formulario OAuth2 con el mismo usuario y
  clave del admin) que devuelve un JWT HS256 de 8 horas. En `/docs` aparece el botón
  **Authorize**. Nueva dependencia: `PyJWT`.
- Con `APP_ENV=production`, la app escribe en los logs al arrancar un aviso si `SECRET_KEY` mide
  menos de 32 bytes (`SECRET_KEY tiene N bytes; se recomiendan 32 o más`). Nunca imprime el valor
  de la clave y no impide el arranque.

### Security
- **Cambio incompatible:** todos los `POST` y `PATCH` de `/api/v1` exigen
  `Authorization: Bearer <token>`; sin token responden `401`. Antes cualquiera que abriera
  `/docs` podía crear y modificar datos.
- Privacidad: `GET /api/v1/athletes`, `GET /api/v1/athletes/{id}` y `GET /api/v1/registrations`
  también exigen token (devuelven fecha de nacimiento y peso, y hay menores). Siguen públicos
  los torneos, categorías, clubes, llaves y combates.
- La comparación de credenciales usa tiempo constante (`secrets.compare_digest`) y vive en un
  solo lugar, compartido por el login de la API y el del admin web. El admin web no cambia.
- Un test recorre el esquema OpenAPI y falla si un endpoint nuevo queda sin protección sin estar
  en la lista explícita de endpoints públicos.

### Removed
- La carpeta `http/` (archivos `.http` de REST Client): `pytest`, Swagger con **Authorize** y la
  colección que se importa desde `/openapi.json` los reemplazan, y cada endpoint nuevo exigía
  mantenerlos a mano sin que nada los verificara.

### Changed
- Admin: el selector de "Inscribir atleta" ya no ofrece a los atletas inscritos en esa
  categoría, ni a los inscritos en otra categoría del mismo torneo (antes aparecían todos y
  elegir uno daba un error 409). Si no queda nadie, se muestra un mensaje en vez del
  formulario.
- Admin: botón "Torneos" en la barra de navegación, a la izquierda de "Clubes" y "Atletas"
  (antes solo se llegaba al listado de torneos por el título).
- El estado del torneo se distingue por color en la lista pública y en el dashboard del
  admin: "Borrador" gris, "En curso" azul y "Finalizado" verde (antes los tres eran grises).

## [0.1.0] - 2026-10-04

Primera versión etiquetada: el sistema completo de las fases 0 a 8, en producción en
https://taekwondo-tournament-manager.onrender.com.

### Added
- Modelo de datos (clubes, atletas, torneos, categorías, inscripciones, llaves, combates y
  rounds) con migraciones de Alembic. SQLite en desarrollo, PostgreSQL en producción.
- API REST bajo `/api/v1/...` con validaciones de negocio: género y peso de la categoría, sin
  doble inscripción, un atleta por torneo.
- Generación aleatoria de llaves de eliminación simple, con pases directos (byes) repartidos.
- Carga de resultados round por round, con avance automático del ganador a la siguiente ronda.
- Pantalla pública (`/`) con torneos, categorías y llaves, y panel de administración
  (`/admin`) con login por sesión. Todo el texto visible en español.
- Docker y `docker compose` con Postgres local; despliegue en Render (Docker) + Neon.
- Bloqueo de arranque en producción (`APP_ENV=production`) si `SECRET_KEY` o `ADMIN_PASSWORD`
  siguen con su valor por defecto.
- Número de versión visible en la esquina de cada página y en `/health`.

### Fixed
- `pool_pre_ping=True` en la conexión a la base de datos: Neon suspende el cómputo por
  inactividad y la primera conexión tras un rato inactivo pudo fallar con un error 500.

[Unreleased]: https://github.com/pacha2880/taekwondo-tournament-manager/compare/v0.9.0-alpha.1...HEAD
[0.9.0-alpha.1]: https://github.com/pacha2880/taekwondo-tournament-manager/compare/v0.8.2...v0.9.0-alpha.1
[0.8.2]: https://github.com/pacha2880/taekwondo-tournament-manager/compare/v0.8.1...v0.8.2
[0.8.1]: https://github.com/pacha2880/taekwondo-tournament-manager/compare/v0.8.0...v0.8.1
[0.8.0]: https://github.com/pacha2880/taekwondo-tournament-manager/compare/v0.7.0...v0.8.0
[0.7.0]: https://github.com/pacha2880/taekwondo-tournament-manager/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/pacha2880/taekwondo-tournament-manager/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/pacha2880/taekwondo-tournament-manager/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/pacha2880/taekwondo-tournament-manager/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/pacha2880/taekwondo-tournament-manager/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/pacha2880/taekwondo-tournament-manager/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/pacha2880/taekwondo-tournament-manager/releases/tag/v0.1.0
