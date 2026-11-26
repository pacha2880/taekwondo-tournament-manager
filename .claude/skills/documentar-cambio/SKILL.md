---
name: documentar-cambio
description: Checklist al terminar un sub-paso de código (feature, fix, cambio de API) — verificar y actualizar CHANGELOG, docs/API.md, DECISIONS, BACKLOG y, solo si corresponde, CLAUDE.md. Usar antes de dar un cambio por terminado.
---

# Cerrar un sub-paso

1. **Verificar**: `.venv/bin/pytest -q` (SQLite, toda la suite). Postgres no: lo corre el CI del PR.
2. **Documentar** solo lo que aplique:
   - `CHANGELOG.md`, `[Unreleased]`: una línea por cambio visible para usuarios de la app o de la API.
     El CI, las docs internas y la configuración de Claude no cuentan.
   - `docs/API.md`: si cambió el contrato o el comportamiento de la API (lo lee el frontend externo).
     Si cambia un endpoint que usa `scripts/seed_demo_api.py`, actualizar también el script. `scripts/reset_data.py`
     borra las tablas solo, desde `Base.metadata`: no hay lista que mantener.
   - `docs/DECISIONS.md`: si se tomó una decisión no obvia, con su porqué, y su fila en el índice (si reemplaza a
     otra, cambiar el estado de esa).
   - `docs/BACKLOG.md`: marcar lo terminado.
   - Comportamiento de una función que no se ve en su código: en su docstring.
   - Regla de una carpeta: en `.claude/rules/`.
   - `CLAUDE.md`: **solo** si es algo que Claude no puede sacar del repo, sirve en casi todas las
     sesiones y ya hubo que corregirlo. CLAUDE.md no es un registro de cambios.
3. **Parar**: dejar todo sin stagear, resumir por archivo y preguntar si commitear.
