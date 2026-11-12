---
paths:
  - "alembic/**"
  - "app/models.py"
---
# Migraciones

Dentro de `0.x`, las migraciones de Alembic **solo agregan** (columnas nuevas opcionales): nunca borrar ni
renombrar. Así, volver a un tag anterior sigue funcionando sobre una base ya migrada. Para quitar o cambiar
algo, dejar lo viejo sin usar. Las valida el servicio `dev` de Render (corre contra Neon en cada push a `dev`).
