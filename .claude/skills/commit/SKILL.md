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
4. Push a `origin dev` solo si lo pidió.
5. Antes de ese push, correr el subagente `revisor` y mostrarle al usuario sus hallazgos, con el arreglo que propone
   cada uno. Si hay alguno, no pushear hasta que el usuario decida: corregir (en la conversación principal, no el
   revisor) o pushear igual. Si con eso se cierra una versión, proponer `/release`; si no, no
   mencionar tags.
6. Si había un `git stash` guardado para aislar este cambio (`git stash list`), después del commit recuperarlo con
   `git stash pop`. Si choca (típico en `CHANGELOG.md`), resolver dejando las dos partes y avisar.
7. Después del push a `dev`, si cambió la API (algo nuevo o incompatible), sumar el aviso en la sección
   «Avisos para el frontend (Kike)» de la página Taekwondo Torneos de Notion: versión, si es incompatible, y qué
   tiene que cambiar el frontend. En la misma pasada, actualizar «Progreso» y «Siguiente paso» de la fila del
   proyecto en Proyectos. Antes del push no: el aviso describe lo que ya está en el servicio `dev`. Un cambio
   **incompatible** además se acuerda con Kike antes del push (ver `DECISIONS.md`, 2026-11-12: `dev` es un entorno
   compartido con su frontend).
