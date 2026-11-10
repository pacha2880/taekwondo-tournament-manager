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

## 0.2.0 — API protegida (login con JWT)

El agujero de seguridad estaba en producción: ningún endpoint de la API exigía autenticación,
así que cualquiera que abriera `/docs` podía crear y modificar datos. Esta versión lo cierra y
no toca la base de datos. Rompe a los consumidores que escribían sin token (por diseño).

- [x] `POST /api/v1/auth/login` (formulario OAuth2, mismo usuario y clave del admin) que
      devuelve un JWT HS256 de 8 horas, sin renovación automática.
- [x] Todo POST y PATCH de `/api/v1` exige `Authorization: Bearer <token>`.
- [x] Privacidad: `GET` de atletas e inscripciones también exigen token (devuelven fecha de
      nacimiento y peso, y hay menores). Siguen públicos: torneos, categorías, clubes, llaves
      y combates (solo nombres).
- [x] Un test recorre el esquema OpenAPI y falla si un endpoint nuevo queda sin protección y
      no está en la lista explícita de endpoints públicos.
- [x] Aviso en los logs al arrancar si `SECRET_KEY` mide menos de 32 bytes (solo con
      `APP_ENV=production`; no imprime el valor ni impide arrancar). Más adelante, cuando se hayan
      verificado las claves de dev y producción, se puede endurecer a que la app se niegue a
      arrancar con una clave corta.
- [x] Incluye tres mejoras de admin que ya estaban hechas: el selector de inscripción excluye a
      los ya inscritos, botón "Torneos" en la navbar y colores por estado del torneo.

## 0.3.0 — API para frontends externos

Pedido real: un amigo va a construir un frontend separado (otra tecnología) contra esta API;
primero solo lectura (torneos y llaves) y enseguida administración. Orden de trabajo dentro de la
versión: primero CORS (es lo que lo bloquea), después la documentación, de menos a más trabajo.
Nada de esto cambia cómo se comporta la API.

- [x] CORS configurable con la variable `CORS_ORIGINS` (lista separada por comas). Sin definirla
      no se permite ningún origen. En producción debe negarse a arrancar si contiene `*`. Sin
      cookies: el token viaja en la cabecera `Authorization`.

### Documentación de `/docs` (Swagger)

**Decidido:** todo en español —descripciones y nombres de los grupos (`tags`): Torneos,
Categorías, Atletas, Clubes, Inscripciones, Llaves, Combates, Autenticación, Sistema—, y en inglés
solo los identificadores (rutas, campos, valores de enums). Los grupos se fijan ahora porque muchos
generadores de clientes los usan para nombrar clases, y renombrarlos después rompería ese código.
Detalle completo del porqué en `docs/DECISIONS.md` (entrada 2026-10-16). Cinco pasos:

- [x] **1. Limpiar `/docs`.** Sacar las páginas HTML del esquema (`include_in_schema=False` en
      los routers `public` y `admin`); `operationId` limpios (`create_club`, `list_tournaments`…)
      con `generate_unique_id_function` — los nombres de las funciones ya son únicos entre
      routers; título y versión leídos de `app/version.py` en vez de escritos a mano.
- [x] **2. Descripción general** en la cabecera de `/docs` (Markdown, corta): qué es la API,
      cómo usar el botón **Authorize**, formato de errores (los de negocio vienen como `detail`
      en español; los 422 de validación, en el formato estándar de Pydantic), que el primer
      request tarda en el plan gratis, y que en `0.x` algo puede cambiar.
- [x] **3. Cada endpoint** con `summary`, descripción corta y `responses` con los errores reales
      (`401`, `404`, `409`, `422`). Los grupos (`openapi_tags`) con una explicación cada uno.
- [x] **4. Los campos que no se explican solos**, con `Field(description=..., examples=[...])`
      en `schemas.py`, y el significado de cada valor de los enums (`male`/`female`,
      `pending`/`bye`/`finished`, `draft`/`in_progress`/`finished`…). Son unos 45 campos: el
      contador del esquema da 125 porque cuenta los repetidos entre `Create`/`Read`, pero las
      descripciones se escriben una sola vez en las clases `*Base` y se heredan.
- [x] **5. Test guardián**, igual que el de autenticación: falla si una operación de `/api/v1`
      queda sin `summary` o sin `description`, para que la documentación no se pudra cuando
      alguien agregue un endpoint nuevo.
- [x] **Extra, al final: `docs/API.md`**, corto — cómo leer una llave (`round_number`, `slot`,
      rojo/azul, `next_match_id`, pases directos) y un ejemplo de flujo con `curl`. No duplica lo
      que ya dice `/docs`; lo enlaza.

## 0.4.0 — Datos de atletas y clubes (única migración de esquema, aditiva)

Va antes del ciclo de vida a propósito: es la migración más simple, y sirve de ensayo del
camino commit → push → deploy → migración → rollback antes de los cambios de comportamiento.
También la necesita el frontend externo en su etapa de administración: hoy la API no tiene
edición de atletas ni de clubes, así que cada ítem de editar se hace **en la API y en el admin**.

- [x] Campo CI (documento de identidad) **opcional** (hay niños sin CI, confirmado con el cliente) y
      único cuando se informa, con formato `^\d{5,9}(?:-[0-9A-Z]{2})?$` (5 a 9 dígitos y complemento
      opcional; sin lugar de expedición). Los atletas ya cargados quedan sin CI.
- [x] Editar atleta (API y admin). Reglas al cambiar género o peso con inscripciones: torneo en
      curso lo bloquea si deja de encajar; en borrador retira de las categorías donde ya no encaja, con confirmación;
      finalizado lo permite. Ver `docs/DECISIONS.md`, 2026-10-24.
- [x] Buscar atleta por CI o por nombre (admin y `GET /athletes?q=`), sin distinguir mayúsculas ni tildes.
- [x] Editar club (API y admin).

## 0.5.0 — Admin más seguro, parte B (un cambio chico de API; sin cambios de base de datos)

La parte A (selector filtrado, botón "Torneos", colores de estado) salió en la 0.2.0.

- [x] El número de round deja de ser un dato que se envía: `POST /matches/{id}/rounds` recibe solo
      `red_points` y `blue_points` y el servidor numera los rounds (1, 2, 3…). Cierra el hueco de la
      API (se podía cargar el round 5 sin el 1) y el formulario del admin muestra el número fijo.
- [x] Ventana de confirmación con los datos antes de enviar cada formulario POST del admin (crear
      club, atleta, torneo, categoría; inscribir; generar llave; cargar round; editar atleta y
      club; cambiar el estado del torneo; cerrar sesión). La de rounds avisa que no se pueden editar
      después. Un test falla si un formulario nuevo no la declara.
- [x] Cuando un formulario del admin falla (CI repetido, rango inválido…), se vuelve a mostrar con
      todo lo que se había escrito en vez de vaciarse. Es una regla para todo formulario nuevo.

## 0.6.0 — Ciclo de vida del torneo (cambia el comportamiento de la API)

Es un conjunto de reglas que se apoyan unas en otras; no tienen sentido aplicadas a medias.
Una regla por commit, cada una con sus tests. Las validaciones viven del lado de la API (no
solo del admin), así que aplican también a cualquier consumidor directo de `/api/v1/...`,
consistente con el resto del proyecto.

Se implementa en 4 partes revisables: **1** se cierra la preparación (inscripciones, categorías, no
volver atrás), **2** se habilita el torneo en curso (llaves y rounds), **3** cierre del torneo, **4** vista
pública. La versión se sube al final, con las cuatro.

- [x] **(Parte 1)** Las inscripciones se cierran al pasar el torneo a «en curso»: `create_registration`
      responde 409 si el torneo no está en `draft`. Reemplaza la idea original de bloquear por llave
      generada: como las llaves solo se generan con el torneo en curso (Parte 2), una categoría con llave
      ya tiene las inscripciones cerradas, y todo el ciclo depende de una sola cosa, el estado del torneo.
      Ver `docs/DECISIONS.md`, 2026-10-27.
- [x] **(Parte 1)** El estado deja de fijarse con `PATCH` y pasa a dos acciones:
      `POST /tournaments/{id}/start` (solo desde `draft`; no exige nada más) y
      `POST /tournaments/{id}/finish` (solo desde `in_progress`, ver condiciones abajo). Repetir una
      acción o saltar de `draft` a `finished` responde 409. Se **elimina `status` del `PATCH`** de
      torneos: cambio incompatible, va marcado en el CHANGELOG y hay que avisarle al frontend externo
      antes del deploy. En el admin, el selector se reemplaza por un solo botón según el estado:
      «Cerrar inscripciones e iniciar torneo» y «Finalizar torneo», cada uno con confirmación que
      avisa que es irreversible. Ver `docs/DECISIONS.md`, 2026-10-27.
- [x] Retirar a un atleta de una categoría: `DELETE /registrations/{id}`, solo con el torneo en
      `draft` (409 si no, con `require_tournament_status`). En el admin, un botón «Retirar» en cada
      fila de la lista de inscritos de la categoría, con confirmación (`data-confirm`); con el torneo
      ya iniciado el botón no aparece.
- [x] **(Parte 2)** No permitir cargar resultados de rounds (`record_round` en `app/services/scoring.py`)
      mientras el torneo está en `DRAFT` — mensaje pidiendo pasar el torneo a "en curso"
      primero.
- [x] **(Parte 1)** Solo permitir crear categorías (`create_category` en `app/api/categories.py`) mientras
      el torneo está en `DRAFT` — no "bloqueado en en curso", sino "solo permitido en
      DRAFT", para cubrir también el caso de un torneo ya `FINISHED`.
- [x] **(Parte 2)** Solo permitir generar la llave de una categoría (`create_bracket`/`generate_bracket`)
      una vez el torneo está `IN_PROGRESS`, no en `DRAFT`. Motivo: que el sorteo sea un
      evento público — no algo que ya pasó en secreto antes de que el torneo apareciera en
      la pantalla pública (recordá que `DRAFT` se oculta de la lista). De paso resuelve la
      duda de "generar todas las llaves automático al activar": no hace falta, porque el
      admin sigue generando cada llave a mano, categoría por categoría, pero recién puede
      hacerlo después de pasar a `en curso` — el orden queda forzado por esta regla, sin
      necesidad de automatizar nada. Además cierra un hueco de la 0.4.0: `PATCH /athletes` retira
      a un atleta de una categoría de un torneo en borrador sin mirar si ya tiene llave, porque con
      esta regla un torneo en borrador nunca tendrá llave.
- [x] `finish` exige que **todos** los matches de **todas** las categorías del torneo hayan
      llegado a un estado terminal. Ojo con el detalle: un bye nunca pasa a
      `MatchStatus.FINISHED` (se queda en `BYE` para siempre, ver `app/models.py`), así que la
      condición es `status in (FINISHED, BYE)` para cada match, no `status == FINISHED` a secas —
      si no, un bracket con cualquier bye bloquearía el torneo para siempre. **Decidido:** una
      categoría sin llave bloquea si tiene 2 o más inscritos (hay combates sin jugar) y se ignora si
      tiene 0 o 1 (la de 1 la resuelve la 0.7.0).
- [x] **(Parte 4)** Los torneos en `draft` **sí** se muestran en las páginas públicas (en la lista de
      inicio, con el estado «Inscripciones abiertas», y con sus páginas de torneo y de categoría). En la
      página de una categoría, mientras no se haya generado la llave (en `draft` y también en curso antes
      del sorteo), se muestra la **lista de inscritos** como una tabla simple con **nombre y club**. Una
      vez generada la llave, se muestra la llave como hasta ahora. **Privacidad:** solo nombre y club;
      nunca CI, fecha de nacimiento ni peso del atleta (hay menores; es la misma regla que mantiene
      `GET /athletes` detrás de token). Reemplaza la idea anterior de ocultar los borradores con 404.
- [x] **(Parte 4)** La API ofrece lo mismo para el frontend externo: `GET /categories/{id}/registrants`
      (público, solo `athlete_id`, `name` y `club`) y `has_bracket` en la categoría. Se eligió un endpoint
      propio en vez de ampliar `GET /bracket` (que habría cambiado su contrato: hoy responde 404 sin llave).
- [x] **(Parte 4)** En la vista de las llaves, el club de cada atleta aparece entre paréntesis junto a su
      nombre, por ejemplo «Mateo Quispe (Dojang Norte)».
- [x] **(Parte 4)** Label de `TournamentStatus.DRAFT` — hoy se traduce como "Borrador"
      (`app/web/labels.py`), pero describe más específicamente el período en que se pueden
      crear categorías e inscribir atletas. Evaluar cambiar el label a algo como
      "Inscripciones" o "Inscripciones abiertas" — **solo el texto traducido**, no el
      identificador interno del enum (`DRAFT` se queda en inglés como está, ver sección
      Idioma de `CLAUDE.md`). **Decidido:** «Inscripciones abiertas».

Nota de compatibilidad: el torneo de demo que ya está en producción está `FINISHED`, así que
las reglas nuevas no lo afectan (solo se aplican al intentar una acción, no invalidan datos
existentes).

## 0.7.0 — Campeones

- [ ] Categoría con un solo inscrito: ese atleta **ya es el campeón**, sin combate y sin llave. No
      se genera llave (`build_first_round_slots` sigue exigiendo mínimo 2, `NotEnoughAthletes`) ni
      se inventa un `Match` artificial: el campeón se deduce de la única inscripción, sin cambios de
      modelo. En la página pública y en el admin, la categoría muestra a ese atleta como campeón en
      lugar de la llave. Encaja con `finish`, que ya ignora las categorías sin llave con 0 o 1
      inscritos.
- [ ] Al iniciar el torneo, avisar qué categorías tienen **un solo inscrito**, por si el admin quiere
      corregir algo antes (inscribir a alguien más, mover al atleta de categoría) — después de
      iniciarlo las inscripciones se cierran y ese atleta queda campeón sin pelear. En el admin, la
      lista aparece junto al botón «Cerrar inscripciones e iniciar torneo» y en su confirmación. Es
      un aviso, no un bloqueo: `POST /tournaments/{id}/start` no cambia.
- [ ] Mostrar un ícono de corona 👑 junto al nombre del campeón de cada categoría en la pantalla
      pública y en el admin: el ganador del último match de la llave o, en una categoría con un solo
      inscrito, ese atleta. Va después de los dos ítems anteriores porque depende de cómo se
      define "campeón".
- [ ] Ranking de clubes por puntos de medalla en la pantalla pública — oro=7, plata=3,
      bronce=1, categoría sin pelea=1 (valores reales de la convocatoria de Copa Diamante;
      dejar configurables por si otro torneo usa otra escala). Depende de los dos ítems
      anteriores y de algo que hoy no existe: el bracket solo guarda el ganador final
      (`Match.winner_id` de la final), no 2do/3er lugar — hay que decidir cómo derivarlos
      (2do = perdedor de la final, 3er = ¿ambos perdedores de semifinal, como es común en
      taekwondo, o se juega un 3er puesto?).

## 0.8.0 — Grados de cinturón y estatura (datos ampliados de atleta y categoría)

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

## 0.9.0 — Inscripción por planilla Excel (varios competidores de un club a la vez)

Hoy cada atleta se crea y se inscribe uno por uno en el admin. Un club suele llegar con varios
competidores juntos: la idea es que el admin descargue una planilla `.xlsx`, el club la llene y el admin la
suba para crear e inscribir a todos de una vez. Los detalles se afinan con el usuario al empezar esta
versión; abajo, las partes y las reglas candidatas que hay que confirmar entonces.

- [ ] **(Parte 1) Descargar la planilla** de un torneo en `draft`: una fila por competidor con los datos
      del atleta (nombre, CI, fecha de nacimiento, género, cinturón, peso) y la categoría, más una hoja de
      instrucciones. Valores con lista desplegable donde se pueda (género en español, categorías del
      torneo), para evitar errores de escritura.
- [ ] **(Parte 2) Subir y revisar sin guardar:** se lee el archivo y se muestra una vista previa fila por
      fila: atleta nuevo, atleta ya existente o error (con número de fila y el motivo en español). Todavía
      no se escribe nada en la base.
- [ ] **(Parte 3) Confirmar:** se crean los atletas que faltan y las inscripciones, reusando
      `create_athlete`/`create_registration` de `app/api/` (igual que hace el admin hoy), así las
      validaciones de negocio no se duplican.
- [ ] **(Parte 4, a decidir)** Exponerlo también en `/api/v1` para el frontend externo, o dejarlo solo en
      el admin.

Reglas candidatas (a confirmar con el usuario al empezar, no antes):

- **Estado del torneo:** solo en `draft`, con `require_tournament_status` (las inscripciones ya se cierran
  al iniciar el torneo).
- **Club:** ¿un club por planilla, elegido al descargarla o al subirla? `Athlete.club_id` es fijo: ¿qué
  pasa si la planilla trae un atleta que ya existe en otro club? ¿Error, o se permite cambiarlo de club?
- **Atleta ya existente:** se reconoce por CI. ¿Y los que no tienen CI (niños)? ¿Por nombre + fecha de
  nacimiento, o siempre se crean nuevos (riesgo de duplicados)? Si existe pero cambió algún dato (peso,
  cinturón), ¿se actualiza, se ignora o se marca como error?
- **Categoría:** ¿la elige el club en la planilla, o el sistema la sugiere a partir de género, edad,
  peso y cinturón? La regla de elegibilidad vive en `category_mismatch` (`app/services/eligibility.py`);
  no duplicarla. Si encaja en más de una categoría, ¿quién decide?
- **Todo o nada vs. parcial:** ¿una fila con error frena toda la planilla, o se inscriben las válidas y
  se informan las demás? En cualquier caso, la confirmación corre en una sola transacción.
- **Duplicados:** el mismo atleta dos veces en la planilla, o ya inscrito en otra categoría del torneo
  (hoy `create_registration` responde 409).
- **Formato del archivo:** solo `.xlsx` (nueva dependencia, probablemente `openpyxl`); fechas que llegan
  como fecha o como texto, pesos con coma decimal, género escrito en español; límite de filas y de tamaño.
- **Privacidad y seguridad:** solo admin (hay fechas de nacimiento y pesos de menores); el archivo se
  procesa en memoria y no se guarda; si la planilla viene precargada con datos, cuidar las celdas que
  empiecen con `=` (inyección de fórmulas).
- **Quién la llena:** ¿el club la completa por su cuenta y el admin la sube, o algún día el club la sube
  directo (necesitaría cuentas por club, algo que hoy no existe)?

## Más adelante / sin versión asignada

- [ ] Permitir editar un round ya cargado. No es trivial: si es el round que cerró el combate,
      hay que reabrirlo (volver a `pending`, revertir `winner_id`) y, si el ganador ya se
      propagó a la siguiente ronda (`advance_winner`), también revertir esa propagación —
      puede afectar en cascada otro combate ya en curso. Es el cambio con más riesgo de dejar
      datos inconsistentes. Decidido en la 0.5.0 que por ahora no hace falta (ver
      `docs/DECISIONS.md`, 2026-10-26); se reabre si el uso real lo pide.
- [ ] Evitar atletas duplicados por doble clic en "Crear" (hoy no hay restricción de
      unicidad en atletas; el campo CI único de la 0.4.0 lo resuelve de raíz).
- [ ] Área/cancha asignada a cada categoría o bracket, para torneos que corren varias en
      paralelo (viene de la planilla física de control). Diseño sin decidir — ver "Decisiones
      pendientes".
- [ ] Acta de resultados imprimible por categoría (1er/2do/3er lugar + club, firmas), a partir
      de una plantilla `.docx` base — refleja el formato de la planilla física de control que
      ya usan en los torneos. Depende de tener 2do/3er lugar derivados (ver ranking de clubes
      en la 0.7.0).
- [ ] Adjuntar documentación (PDF) a una inscripción — el formulario real de Copa Diamante lo
      pide para ciertas modalidades. Necesita almacenamiento de archivos (hoy no hay ninguno
      en el proyecto). Baja prioridad hasta confirmar que hace falta en el sistema nuevo, no
      solo en el formulario viejo.
- [ ] Fecha de cierre de inscripciones por categoría/torneo, independiente de si ya se generó
      la llave (hoy la única forma de cerrar inscripciones es generar la llave, ver 0.6.0).
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
- [ ] Auto-refresh en vivo de la pantalla pública (polling con htmx), en vez de recargar manual.
