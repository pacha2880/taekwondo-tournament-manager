---
paths:
  - "alembic/**"
  - "app/models.py"
---
# Migraciones

Dentro de `0.x`, las migraciones de Alembic **solo agregan** (columnas nuevas opcionales): nunca borrar ni
renombrar. Así, volver a un tag anterior sigue funcionando sobre una base ya migrada. Para quitar o cambiar
algo, dejar lo viejo sin usar. Única excepción: `e5c7a3f90b18` (2026-11-26) borró columnas viejas porque se vaciaron
todas las bases; desde ahí no se vuelve a un tag ≤ 0.8.1 sobre una base migrada. Las valida el servicio `dev` de
Render (corre contra Neon en cada push a `dev`).
