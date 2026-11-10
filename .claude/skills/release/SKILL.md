---
name: release
description: Prepara la liberación de una versión nueva (SemVer) en dev — sube app/version.py, cierra [Unreleased] del CHANGELOG, corre los tests en SQLite (Postgres lo corre el CI del PR) y deja los comandos del PR y del tag. Usar cuando el usuario pide liberar, cerrar o sacar una versión.
---

# Liberar una versión

El resultado es **un único commit `chore: versión X.Y.Z` en `dev`**, que es el último del PR
`dev` → `main`. El asistente nunca toca `main` ni crea el tag: eso lo hace el usuario después
del merge.

## 1. Verificar el punto de partida

- Rama actual `dev` y árbol limpio (`git status`). Si hay cambios sin commitear, **parar** y
  preguntar: el commit de versión no lleva otros cambios.
- `git fetch` y confirmar que `dev` no está detrás de `origin/dev`.
- Leer `git log --oneline origin/main..dev` y la sección `[Unreleased]` de `CHANGELOG.md`.
  Si algún commit visible no tiene su línea en el changelog, avisar antes de seguir. Si
  `[Unreleased]` está vacío, no hay nada que liberar.

## 2. Elegir el número

Partir de la última versión de `git tag` y de `app/version.py`. Dentro de `0.x`:

- **minor** (`0.Y+1.0`): cualquier cambio incompatible (`feat!:`, entradas «Incompatible» en
  el changelog) o funcionalidad nueva.
- **patch** (`0.Y.Z+1`): solo correcciones.

Proponer el número con una línea de justificación y **esperar confirmación** del usuario.

## 3. Editar

- `app/version.py`: `__version__ = "X.Y.Z"`.
- `CHANGELOG.md`:
  - Renombrar `## [Unreleased]` a `## [X.Y.Z] - AAAA-MM-DD` (fecha de hoy) y agregar arriba
    un `## [Unreleased]` vacío.
  - Links del final: `[Unreleased]` pasa a comparar `vX.Y.Z...HEAD`, y se agrega
    `[X.Y.Z]: .../compare/vANTERIOR...vX.Y.Z` arriba del link de la versión anterior.

## 4. Tests

SQLite, obligatorio:

```bash
.venv/bin/pytest -q
```

Postgres lo corre el CI en el PR (job `pytest-postgres`). Solo si el CI no está disponible,
correrlo en local como respaldo, **siempre contra `taekwondo_test`** (la suite borra todas las
tablas; crear la base una vez según `README.md`):

```bash
./dev.sh start
DATABASE_URL="postgresql+psycopg://taekwondo:taekwondo@localhost:5432/taekwondo_test" .venv/bin/pytest -q
```

## 5. Commit

Mostrar el diff y **pedir permiso** antes de `git commit -m "chore: versión X.Y.Z"`. Push a
`origin dev` solo si el usuario lo pide.

## 6. Mensaje final

1. Recordar que el usuario abre y mergea el PR `dev` → `main` con **merge normal** (merge
   commit, sin squash ni rebase). El PR no se puede mergear hasta que `pytest` y
   `pytest-postgres` estén en verde. El merge es el deploy a producción.
2. **Después del merge**, los comandos del tag, cada uno en su propio bloque `bash`:

   ```bash
   git checkout main && git pull
   ```

   ```bash
   git tag -a vX.Y.Z -m "X.Y.Z"
   ```

   ```bash
   git push origin vX.Y.Z
   ```

3. Después del push, verificar `/health` en
   https://taekwondo-tournament-manager.onrender.com/health (debe mostrar `X.Y.Z`) y una
   página pública.

Un tag publicado nunca se mueve, borra ni reescribe: si la versión salió mal, se corrige con
una versión de parche nueva.
