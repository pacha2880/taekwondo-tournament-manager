# Backlog — Fase 9 (mejoras post-deploy)

Cosas que se nos van ocurriendo pero que deliberadamente no bloquean llegar a producción.
Ordenadas en versiones (ver [`CHANGELOG.md`](../CHANGELOG.md) y la sección **Versionado** del
`README.md`). El orden sale de tres pasadas de análisis: dependencias entre ítems, riesgo para
lo que ya funciona en producción, y valor frente a esfuerzo.

Reglas de cada versión: tests en verde contra SQLite **y** contra el Postgres de Docker;
migraciones solo aditivas (columnas nuevas opcionales, nunca borrar ni renombrar) para que
volver al tag anterior siga funcionando sobre una base ya migrada; tras el deploy, verificar
`/health` (muestra la versión) y una página pública.

## Decisiones pendientes

- **Categoría sin llave y cierre del torneo.** ¿Una categoría sin llave bloquea pasar el torneo
  a `FINISHED`? Propuesta: sí si tiene 2 o más inscritos (hay combates sin jugar); se ignora si
  tiene 0 o 1 (lo resuelve la 0.5.0).
- **Editar rounds ya cargados (ver "Más adelante").** ¿Hace falta, o alcanza con el número de
  round fijo más la confirmación previa de la 0.2.0?
- **Asignación de área/cancha por categoría.** Un torneo real corre varias categorías en
  paralelo en distintas áreas (viene de la planilla física de control, campo "AREA"). Falta
  decidir: ¿una entidad `Area` propia (nombre/número), o alcanza con que el admin indique
  cuántas áreas tiene el torneo al crearlo y las asigne por categoría? ¿Asignación manual, o
  alguna regla automática? Ver ítem en "Más adelante".

## 0.1.0 — Versionado

- [x] `app/version.py`, número de versión en la esquina de cada página y en `/health`,
      `CHANGELOG.md`.
- [x] `pool_pre_ping=True` en `app/database.py`: Neon suspende el cómputo por inactividad y la
      primera conexión tras un rato podía fallar con un 500. Se commiteó antes del commit de
      versión, así que quedó dentro del tag `v0.1.0` (no hizo falta una `0.1.1`).

## 0.2.0 — Admin más seguro (sin cambios de API ni de base de datos)

- [ ] En el `<select>` de "Inscribir atleta" de la pantalla admin de categoría
      (`app/web/admin/category_workspace.py::_category_detail_context`, variable
      `all_athletes`), filtrar los atletas que ya están inscritos en esa categoría — hoy
      aparecen todos (`select(Athlete).order_by(Athlete.name)`, sin excluir a los de
      `registrations`), lo que permite intentar inscribir a alguien ya inscrito y chocar con
      el 409 en vez de no ofrecerlo como opción directamente.
- [ ] En la navbar del admin, agregar un botón "Torneos" a la izquierda de "Clubes" y
      "Atletas" (hoy solo se llega al dashboard de torneos por el link del brand).
- [ ] En el formulario de carga de resultados del admin, no dejar el número de round libre —
      calcularlo y mostrarlo fijo (rounds ya cargados de ese combate + 1) para que no se pueda
      cargar un round fuera de orden. Sumar un popup de confirmación antes de guardar,
      aclarando que hoy no se puede editar después.
- [ ] De forma más general: cada vez que se crea algo desde el admin (club, atleta, torneo,
      categoría, inscripción, llave, round), mostrar un popup de confirmación con los datos
      antes de mandar el form — no necesariamente aclarando que no se puede editar después,
      solo para que el usuario confirme lo que está a punto de crear.
- [ ] Colores distintos por estado de torneo (`TournamentStatus`) en los badges — hoy
      "Borrador"/"En curso"/"Finalizado" se ven todos igual (gris). Mismo patrón que ya existe
      para `MatchStatus` (`match_status_badge_class` en `app/web/labels.py`): agregar algo
      como `tournament_status_badge_class`.

## 0.3.0 — Datos de atletas y clubes (única migración de esquema, aditiva)

Va antes del ciclo de vida a propósito: es la migración más simple, y sirve de ensayo del
camino commit → push → deploy → migración → rollback antes de los cambios de comportamiento.

- [ ] Campo CI (documento de identidad) único por atleta. Columna **nullable** en la base
      (los atletas ya cargados no tienen CI; en Postgres y SQLite un índice único admite
      varios `NULL`), obligatoria en el formulario de alta.
- [ ] Editar atleta (hoy solo se puede crear; un error de tipeo no se puede corregir sin SQL).
      Permite completar el CI de los atletas existentes.
- [ ] Buscar atleta por CI o por nombre en la pantalla admin de atletas.
- [ ] Editar club (a confirmar si hace falta).

## 0.4.0 — Ciclo de vida del torneo (cambia el comportamiento de la API)

Es un conjunto de reglas que se apoyan unas en otras; no tienen sentido aplicadas a medias.
Una regla por commit, cada una con sus tests. Las validaciones viven del lado de la API (no
solo del admin), así que aplican también a cualquier consumidor directo de `/api/v1/...`,
consistente con el resto del proyecto.

- [ ] Una vez generado el bracket de una categoría, bloquear nuevas inscripciones a esa
      categoría (`create_registration` en `app/api/registrations.py`, chequeando si
      `Category` ya tiene `Bracket` — 409, mismo criterio que `BracketAlreadyExists`). Es una
      regla a nivel de categoría, independiente del estado del torneo (`TournamentStatus`):
      dos categorías del mismo torneo pueden estar en momentos distintos (una con llave ya
      generada, otra todavía recibiendo inscripciones). En el admin, el botón "Generar llave"
      necesita un popup de confirmación explicando que después de esto no se puede inscribir
      a nadie más en esa categoría.
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
- [ ] Solo se puede mover a `FINISHED` cuando **todos** los matches de **todas** las
      categorías del torneo llegaron a un estado terminal. Ojo con el detalle: un bye nunca
      pasa a `MatchStatus.FINISHED` (se queda en `BYE` para siempre, ver `app/models.py`),
      así que la condición es `status in (FINISHED, BYE)` para cada match, no
      `status == FINISHED` a secas — si no, un bracket con cualquier bye bloquearía el
      torneo para siempre. Qué pasa con una categoría que nunca generó bracket: ver
      "Decisiones pendientes".
- [ ] `FINISHED` es inmutable una vez alcanzado — ningún otro cambio de estado permitido
      después (ni volver a `DRAFT`/`IN_PROGRESS`, ni ningún otro campo del torneo). En el
      admin, el form que pasa el torneo a `FINISHED` necesita un popup de confirmación
      avisando que es irreversible, antes de mandar el cambio.
- [ ] Ocultar los torneos en estado `DRAFT` de la lista principal de la pantalla pública (`/`).
      Queda abierta la pregunta de si también hay que bloquear el acceso directo a
      `/torneos/{id}`/`/categorias/{id}` de un torneo en borrador (hoy no miran `status` para
      nada), para no depender de "seguridad por oscuridad". Va al final de esta versión: para
      entonces el admin ya completa todo el flujo sin depender de la vista pública.
- [ ] Label de `TournamentStatus.DRAFT` — hoy se traduce como "Borrador"
      (`app/web/labels.py`), pero describe más específicamente el período en que se pueden
      crear categorías e inscribir atletas. Evaluar cambiar el label a algo como
      "Inscripciones" o "Inscripciones abiertas" — **solo el texto traducido**, no el
      identificador interno del enum (`DRAFT` se queda en inglés como está, ver sección
      Idioma de `CLAUDE.md`).

Nota de compatibilidad: el torneo de demo que ya está en producción está `FINISHED`, así que
las reglas nuevas no lo afectan (solo se aplican al intentar una acción, no invalidan datos
existentes).

## 0.5.0 — Campeones

- [ ] Generar llave con un solo atleta inscrito (ganador directo, sin combate) — hoy
      `build_first_round_slots` exige mínimo 2 (`NotEnoughAthletes`). Tiene sentido de
      dominio (categoría con un solo competidor, se le otorga el primer lugar sin pelear),
      pero **requiere una decisión de modelo, no es solo bajar un número**: con `size=1`,
      `num_rounds = size.bit_length() - 1 = 0`, así que el loop de `generate_bracket` que
      crea `Match` nunca corre — el bracket quedaría con `matches=[]`, sin ningún lugar donde
      guardar "quién ganó" (hoy esa info vive siempre en `Match.winner_id`). Hay que decidir
      entre: (a) un `Match` artificial de un solo lado, ya `FINISHED`, sin combate real, o
      (b) un campo de "campeón por default" en `Bracket`/`Category` fuera del modelo de
      `Match`. Se conecta con la duda de "Decisiones pendientes" sobre categorías sin bracket
      para el chequeo de `FINISHED` — un bracket de 1 solo atleta tiene el mismo problema (0
      matches) para saber si "ya terminó".
- [ ] Mostrar un ícono de corona 👑 junto al nombre del campeón de cada categoría (el ganador
      del último match del bracket) en la pantalla pública y en el admin — para **cualquier**
      campeón, no solo el caso de categoría con un solo inscrito. Va después del ítem
      anterior porque depende de cómo se defina "campeón".
- [ ] Ranking de clubes por puntos de medalla en la pantalla pública — oro=7, plata=3,
      bronce=1, categoría sin pelea=1 (valores reales de la convocatoria de Copa Diamante;
      dejar configurables por si otro torneo usa otra escala). Depende de los dos ítems
      anteriores y de algo que hoy no existe: el bracket solo guarda el ganador final
      (`Match.winner_id` de la final), no 2do/3er lugar — hay que decidir cómo derivarlos
      (2do = perdedor de la final, 3er = ¿ambos perdedores de semifinal, como es común en
      taekwondo, o se juega un 3er puesto?).

## 0.6.0 — En vivo

- [ ] Auto-refresh en vivo de la pantalla pública (polling con htmx), en vez de recargar manual.

## 0.7.0 — Grados de cinturón y estatura (datos ampliados de atleta y categoría)

Dos cambios de modelo que salen directo del pedido real de Abel Bravo (ver
`confidencial/reporte-analisis.md`, carpeta ignorada por git, no vinculado a ningún commit).

- [ ] Reemplazar `BeltGroup` (hoy un enum fijo `COLOR`/`BLACK`) por un catálogo de **grados**
      (10mo Kup ... 1er Kup, Danes) editable, y **divisiones** editables que agrupan rangos de
      esos grados (ej. Principiantes = 10mo-6to Kup, Novatos = 5to-2do Kup, Avanzados = 1er
      Kup y Danes) — configurables por torneo, no hardcodeadas, mismo principio que ya se usa
      para `weight_label`. Requiere diseño de modelo, no es una migración simple: `Athlete`
      necesita un grado individual, `Category` sigue agrupando por división (no por grado
      suelto), y hay que decidir cómo conviven las divisiones de un torneo viejo (ej. el de
      producción, ya `FINISHED`) con el catálogo nuevo.
- [ ] `Athlete.height_cm` (estatura, nullable) + `Category.min_height`/`max_height`
      (opcionales, mismo patrón que `min_weight`/`max_weight`) — la categoría Festival (hasta
      9 años) empareja por estatura en vez de peso.

## Más adelante / sin versión asignada

- [ ] Permitir editar un round ya cargado. No es trivial: si es el round que cerró el combate,
      hay que reabrirlo (volver a `pending`, revertir `winner_id`) y, si el ganador ya se
      propagó a la siguiente ronda (`advance_winner`), también revertir esa propagación —
      puede afectar en cascada otro combate ya en curso. Es el cambio con más riesgo de dejar
      datos inconsistentes; ver "Decisiones pendientes".
- [ ] Evitar atletas duplicados por doble clic en "Crear" (hoy no hay restricción de
      unicidad en atletas; el campo CI único de la 0.3.0 lo resuelve de raíz).
- [ ] Área/cancha asignada a cada categoría o bracket, para torneos que corren varias en
      paralelo (viene de la planilla física de control). Diseño sin decidir — ver "Decisiones
      pendientes".
- [ ] Acta de resultados imprimible por categoría (1er/2do/3er lugar + club, firmas), a partir
      de una plantilla `.docx` base — refleja el formato de la planilla física de control que
      ya usan en los torneos. Depende de tener 2do/3er lugar derivados (ver ranking de clubes
      en la 0.5.0).
- [ ] Adjuntar documentación (PDF) a una inscripción — el formulario real de Copa Diamante lo
      pide para ciertas modalidades. Necesita almacenamiento de archivos (hoy no hay ninguno
      en el proyecto). Baja prioridad hasta confirmar que hace falta en el sistema nuevo, no
      solo en el formulario viejo.
- [ ] Fecha de cierre de inscripciones por categoría/torneo, independiente de si ya se generó
      la llave (hoy la única forma de cerrar inscripciones es generar la llave, ver 0.4.0).
      Baja prioridad.
- [ ] Link al sitio del club organizador (ej. `keumgangdelfines.com`, configurable) en un
      lugar visible de la pantalla pública — pie de página o detalle del torneo.
- [ ] Integración con el sistema de inscripciones externo del club (hoy un formulario en
      WordPress): un endpoint que reciba inscripciones desde ahí en vez de cargarlas a mano en
      el admin. Idea especulativa, sin diseño — evaluar solo si de verdad hace falta
      reemplazar el formulario actual.
- [ ] Si algún día se construye un frontend separado (SPA) que consuma solo `/api/v1/...`:
      analizar si hace falta un endpoint agregado para la página de detalle de categoría. Hoy
      `_category_detail_context` (`app/web/admin/category_workspace.py`) junta categoría +
      torneo + inscripciones + todos los atletas + bracket en una sola función Python; un
      frontend desacoplado tendría que hacer 5 requests HTTP separados para lo mismo. No
      crear el endpoint agregado todavía — no hay frontend separado hoy, sería especular
      sobre un caso de uso que no existe.
- [ ] (agregar acá cualquier otra idea que surja durante el desarrollo)
