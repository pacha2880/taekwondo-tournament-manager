# Changelog

Formato basado en [Keep a Changelog](https://keepachangelog.com/es-ES/1.1.0/) y versionado
según [Semantic Versioning](https://semver.org/lang/es/). La versión vive en
[`app/version.py`](app/version.py) y se muestra en la esquina de cada página y en `/health`.

Mientras la versión sea `0.y.z` (desarrollo inicial) la API puede cambiar entre versiones
minor. Dentro de `0.x`, las migraciones de base de datos solo agregan (columnas nuevas
opcionales; nunca borrar ni renombrar), para que volver al tag de una versión anterior siga
funcionando sobre una base ya migrada.

## [Unreleased]

### Fixed
- `pool_pre_ping=True` en la conexión a la base de datos: Neon suspende el cómputo por
  inactividad y la primera conexión tras un rato inactivo pudo fallar con un error 500.
  Se publicará como `0.1.1`.

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

[Unreleased]: https://github.com/pacha2880/taekwondo-tournament-manager/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/pacha2880/taekwondo-tournament-manager/releases/tag/v0.1.0
