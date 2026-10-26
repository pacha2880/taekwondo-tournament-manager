# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y versionado
según [Semantic Versioning](https://semver.org/lang/es/). La versión vive en
[`app/version.py`](app/version.py) y se muestra en la esquina de cada página y en `/health`.

Mientras la versión sea `0.y.z` (desarrollo inicial) la API puede cambiar entre versiones
minor. Dentro de `0.x`, las migraciones de base de datos solo agregan (columnas nuevas
opcionales; nunca borrar ni renombrar), para que volver al tag de una versión anterior siga
funcionando sobre una base ya migrada.

## [Unreleased]

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

[Unreleased]: https://github.com/pacha2880/taekwondo-tournament-manager/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/pacha2880/taekwondo-tournament-manager/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/pacha2880/taekwondo-tournament-manager/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/pacha2880/taekwondo-tournament-manager/releases/tag/v0.1.0
