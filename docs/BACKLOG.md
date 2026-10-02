# Backlog — Fase 9 (mejoras post-deploy)

Cosas que se nos van ocurriendo pero que deliberadamente no bloquean llegar a producción.
Se implementan después de la Fase 8, priorizadas según convenga en ese momento:

- [ ] Auto-refresh en vivo de la pantalla pública (polling con htmx), en vez de recargar manual.
- [ ] Colores distintos por estado de torneo (`TournamentStatus`) en los badges — hoy
      "Borrador"/"En curso"/"Finalizado" se ven todos igual (gris). Mismo patrón que ya existe
      para `MatchStatus` (`match_status_badge_class` en `app/web/labels.py`): agregar algo
      como `tournament_status_badge_class`.
- [ ] Ocultar los torneos en estado `DRAFT` de la lista principal de la pantalla pública (`/`).
      Por ahora solo la lista — queda abierta la pregunta de si también hay que bloquear el
      acceso directo a `/torneos/{id}`/`/categorias/{id}` de un torneo en borrador (hoy no
      miran `status` para nada), para no depender de "seguridad por oscuridad".
- [ ] Darle comportamiento real al estado del torneo (`TournamentStatus`), no solo cosmético:
  - [ ] No permitir cargar resultados de rounds (`record_round` en `app/services/scoring.py`)
        mientras el torneo está en `DRAFT` — mensaje pidiendo pasar el torneo a "en curso"
        primero.
  - [ ] Solo permitir crear categorías (`create_category` en `app/api/categories.py`) mientras
        el torneo está en `DRAFT` — no "bloqueado en en curso", sino "solo permitido en
        DRAFT", para cubrir también el caso de un torneo ya `FINISHED`.
  - [ ] Solo permitir generar la llave de una categoría (`create_bracket`/`generate_bracket`)
        una vez el torneo está `IN_PROGRESS`, no en `DRAFT`. Motivo: que el sorteo sea un
        evento público — no algo que ya pasó en secreto antes de que el torneo apareciera en
        la pantalla pública (recordá que `DRAFT` se oculta de la lista). De paso resuelve la
        duda de "generar todas las llaves automático al activar": no hace falta, porque el
        admin sigue generando cada llave a mano, categoría por categoría, pero recién puede
        hacerlo después de pasar a `en curso` — el orden queda forzado por esta regla, sin
        necesidad de automatizar nada.
  - [ ] `FINISHED` es inmutable una vez alcanzado — ningún otro cambio de estado permitido
        después (ni volver a `DRAFT`/`IN_PROGRESS`, ni ningún otro campo del torneo). En el
        admin, el form que pasa el torneo a `FINISHED` necesita un popup de confirmación
        avisando que es irreversible, antes de mandar el cambio.
  - [ ] Solo se puede mover a `FINISHED` cuando **todos** los matches de **todas** las
        categorías del torneo llegaron a un estado terminal. Ojo con el detalle: un bye nunca
        pasa a `MatchStatus.FINISHED` (se queda en `BYE` para siempre, ver `app/models.py`),
        así que la condición es `status in (FINISHED, BYE)` para cada match, no
        `status == FINISHED` a secas — si no, un bracket con cualquier bye bloquearía el
        torneo para siempre. Falta decidir qué pasa con una categoría que nunca generó
        bracket (¿bloquea cerrar el torneo, o se ignora?).
  - [ ] Estas validaciones viven del lado de la API (no solo del admin), así que aplican
        también a cualquier consumidor directo de `/api/v1/...`, consistente con el resto del
        proyecto.
- [ ] Generar llave con un solo atleta inscrito (ganador directo, sin combate) — hoy
      `build_first_round_slots` exige mínimo 2 (`NotEnoughAthletes`). Tiene sentido de
      dominio (categoría con un solo competidor, se le otorga el primer lugar sin pelear),
      pero **requiere una decisión de modelo, no es solo bajar un número**: con `size=1`,
      `num_rounds = size.bit_length() - 1 = 0`, así que el loop de `generate_bracket` que
      crea `Match` nunca corre — el bracket quedaría con `matches=[]`, sin ningún lugar donde
      guardar "quién ganó" (hoy esa info vive siempre en `Match.winner_id`). Hay que decidir
      entre: (a) un `Match` artificial de un solo lado, ya `FINISHED`, sin combate real, o
      (b) un campo de "campeón por default" en `Bracket`/`Category` fuera del modelo de
      `Match`. Se conecta con la misma duda ya abierta arriba sobre categorías sin bracket
      para el chequeo de `FINISHED` — un bracket de 1 solo atleta tiene el mismo problema (0
      matches) para saber si "ya terminó".
- [ ] Mostrar un ícono de corona 👑 junto al nombre del campeón de cada categoría (el ganador
      del último match del bracket) en la pantalla pública y en el admin — para **cualquier**
      campeón, no solo el caso de categoría con un solo inscrito (ese caso de arriba también
      lo mostraría, pero esto aplica en general a toda categoría ya `FINISHED`).
- [ ] Permitir editar un round ya cargado. No es trivial: si es el round que cerró el combate,
      hay que reabrirlo (volver a `pending`, revertir `winner_id`) y, si el ganador ya se
      propagó a la siguiente ronda (`advance_winner`), también revertir esa propagación —
      puede afectar en cascada otro combate ya en curso.
- [ ] En el formulario de carga de resultados del admin, no dejar el número de round libre —
      calcularlo y mostrarlo fijo (rounds ya cargados de ese combate + 1) para que no se pueda
      cargar un round fuera de orden. Sumar un popup de confirmación antes de guardar,
      aclarando que hoy no se puede editar después (hasta que se resuelva el punto anterior).
- [ ] De forma más general: cada vez que se crea algo desde el admin (club, atleta, torneo,
      categoría, inscripción, llave, round), mostrar un popup de confirmación con los datos
      antes de mandar el form — no necesariamente aclarando que no se puede editar después,
      solo para que el usuario confirme lo que está a punto de crear.
- [ ] Campo CI (documento de identidad) único por atleta.
- [ ] Editar atleta (hoy solo se puede crear).
- [ ] Buscar atleta por CI o por nombre en la pantalla admin de atletas.
- [ ] Editar club (a confirmar si hace falta).
- [ ] Una vez generado el bracket de una categoría, bloquear nuevas inscripciones a esa
      categoría (`create_registration` en `app/api/registrations.py`, chequeando si
      `Category` ya tiene `Bracket` — 409, mismo criterio que `BracketAlreadyExists`). Es una
      regla a nivel de categoría, independiente del estado del torneo (`TournamentStatus`):
      dos categorías del mismo torneo pueden estar en momentos distintos (una con llave ya
      generada, otra todavía recibiendo inscripciones). En el admin, el botón "Generar llave"
      necesita un popup de confirmación explicando que después de esto no se puede inscribir
      a nadie más en esa categoría.
- [ ] Label de `TournamentStatus.DRAFT` — hoy se traduce como "Borrador"
      (`app/web/labels.py`), pero describe más específicamente el período en que se pueden
      crear categorías e inscribir atletas. Evaluar cambiar el label a algo como
      "Inscripciones" o "Inscripciones abiertas" — **solo el texto traducido**, no el
      identificador interno del enum (`DRAFT` se queda en inglés como está, ver sección
      Idioma de `CLAUDE.md`).
- [ ] En el `<select>` de "Inscribir atleta" de la pantalla admin de categoría
      (`app/web/admin/category_workspace.py::_category_detail_context`, variable
      `all_athletes`), filtrar los atletas que ya están inscritos en esa categoría — hoy
      aparecen todos (`select(Athlete).order_by(Athlete.name)`, sin excluir a los de
      `registrations`), lo que permite intentar inscribir a alguien ya inscrito y chocar con
      el 409 en vez de no ofrecerlo como opción directamente.
- [ ] En la navbar del admin, agregar un botón "Torneos" a la izquierda de "Clubes" y
      "Atletas" (hoy solo se llega al dashboard de torneos por el link del brand).
- [ ] Si algún día se construye un frontend separado (SPA) que consuma solo `/api/v1/...`:
      analizar si hace falta un endpoint agregado para la página de detalle de categoría. Hoy
      `_category_detail_context` (`app/web/admin/category_workspace.py`) junta categoría +
      torneo + inscripciones + todos los atletas + bracket en una sola función Python; un
      frontend desacoplado tendría que hacer 5 requests HTTP separados para lo mismo. No
      crear el endpoint agregado todavía — no hay frontend separado hoy, sería especular
      sobre un caso de uso que no existe.
- [ ] (agregar acá cualquier otra idea que surja durante el desarrollo)
