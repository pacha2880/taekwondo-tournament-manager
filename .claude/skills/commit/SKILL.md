---
name: commit
description: Cómo commitear y pushear en este repo — un commit por sub-paso, separar por hunks, estilo feat/fix/chore. Usar solo cuando el usuario da una orden directa de commitear o pushear.
---

# Commit

Solo con una orden directa y actual ("commiteá", "hacé el commit"). Si no la hubo, parar y preguntar.

1. Rama `dev` (`git branch --show-current`); nunca `main`.
2. Un commit por sub-paso verificado, no uno por fase. Si un archivo mezcla cambios de varios sub-pasos
   (típico: `CHANGELOG.md` o un archivo de tests), separar por hunks para que cada commit lleve solo lo suyo
   (`git apply --cached` con un parche parcial; `git add -p` no funciona acá porque es interactivo).
3. Mensaje `feat:` / `fix:` / `chore:` / `docs:` (`feat!:` si es incompatible), en español. La línea de
   `CHANGELOG.md` va en el mismo commit que el cambio.
4. Push a `origin dev` solo si lo pidió. Si con eso se cierra una versión, proponer `/release`; si no, no
   mencionar tags.
