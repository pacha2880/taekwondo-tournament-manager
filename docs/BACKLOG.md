# Backlog

Lo aceptado y ordenado en versiones. Las versiones ya liberadas están en [`CHANGELOG.md`](../CHANGELOG.md).

## Cómo se usa

- **Notion, [Pedidos e ideas](https://app.notion.com/p/542c165c4b604d2aa3901cd55d86d24c):** pedidos del cliente e
  ideas por decidir, con el texto original de cada reunión. Lo leen el cliente y el equipo del frontend.
- **Este archivo:** solo lo aceptado, en versiones y con el detalle técnico. Cada ítem enlaza a su fila de Notion;
  la fila pasa a «Aceptado» y anota la versión. El texto no se copia de un lado al otro.
- **[`DECISIONS.md`](DECISIONS.md):** el porqué de cada decisión técnica.

Reglas de cada versión: `pytest` en verde (SQLite en local; Postgres lo corre el CI del PR); migraciones solo
aditivas (única excepción: 2026-11-26, ver `DECISIONS.md`); los cambios incompatibles de la API se juntan en la versión, y cada cambio de la API se le avisa al frontend externo
en Notion apenas llega a `dev` (después del push; ver la skill `commit`). **Solo API:** la interfaz es el frontend externo.

## Ciclo de vida objetivo del torneo

**En preparación** (oculto; el admin arma las categorías) → **Inscripciones abiertas** (cada competidor se inscribe;
se cierran solas en la fecha límite) → **Pesaje** (la lista de inscritos se hace pública) → **En curso** (todas las
llaves juntas) → **Finalizado**.

La 0.6.0 deja tres de esos estados (inscripciones abiertas, en curso, finalizado); la 0.9.0 agrega los otros dos.

## 0.9.0 — Ciclo nuevo y pesaje

Spec acordado el 2026-11-26 (porqués en `DECISIONS.md`, 2026-11-26). Cambia la API de forma incompatible: va marcado
en el CHANGELOG y se acuerda con Kike **antes** del push a `dev`.

**Ciclo:** En preparación (`draft`) → Inscripciones abiertas (`registration_open`) → Pesaje (`weigh_in`) → En curso
(`in_progress`) → Finalizado (`finished`). Un solo camino, sin volver atrás: no se puede pasar de Inscripciones
abiertas a En curso sin el Pesaje.

**Visibilidad:** la API oculta sin token los torneos en preparación y la lista de inscritos antes del Pesaje; con token
devuelve todo, en los mismos endpoints. La vista pública del frontend no los muestra nunca, haya sesión o no (regla
del frontend, avisada a Kike en Notion).

### Bloque 1 — Estados, fecha límite y visibilidad

- [x] **En preparación (`draft`)**: sin token, `GET /tournaments` no lo lista y el torneo, sus categorías, su
      estructura y sus llaves responden `404`; con token se ve. Se arman las categorías (`PUT /category-structure`,
      solo en `draft`); todavía no se inscribe a nadie (`409`).
      [Notion](https://app.notion.com/p/415fae3be03b818fa550dabd0c34074a)
- [x] **Fecha límite de inscripción** (`registration_deadline`, guardada en UTC; el frontend la muestra en hora de
      Bolivia): se fija con `PATCH /tournaments/{id}`, siempre futura y antes del día del torneo (en UTC), y se puede
      mover mientras no haya vencido; después, `409`.
- [x] **Pasar a Pesaje**: acción nueva `POST /tournaments/{id}/close-registration`, solo desde `registration_open`;
      la fecha límite pasa a ser ahora. Es la forma de cerrar antes (no se pone una fecha pasada con `PATCH`).
- [x] **Abrir inscripciones**: acción nueva `POST /tournaments/{id}/open-registration`, solo desde `draft` y con una
      fecha límite futura (si no, `409`). El torneo pasa a ser público.
- [x] **Inscripciones abiertas (`registration_open`)**: se inscribe y se retira como hoy en `draft`
      (`category_mismatch`, una categoría por torneo, `confirm_withdrawal`); fuera de este estado, `409`. Las reglas de
      `app/api/lifecycle.py` que hoy dicen `draft` pasan a `registration_open`.
- [x] **Pesaje (`weigh_in`)**: el torneo entra solo cuando vence la fecha límite (o con «Pasar a Pesaje»). El estado se calcula al leer (función
      pura del torneo y la hora); leer no escribe en la base y no hace falta un cron. Inscripciones cerradas; editar un
      atleta inscrito responde como en En curso.
- [x] **Lista de inscritos oculta hasta el Pesaje**: sin token, `GET /categories/{id}/registrants` responde `403` antes
      del Pesaje; desde el Pesaje es pública. El filtro `has_registrants` de `GET /categories` tampoco da información
      antes del Pesaje (`403` sin un `tournament_id` ya publicado). Un token inválido responde `401` también en las
      lecturas públicas. [Notion](https://app.notion.com/p/415fae3be03b81568bd7f3cfcc2df971)
- [x] **Iniciar**: `POST /tournaments/{id}/start` solo desde `weigh_in` (antes, `409`).
- [x] `scripts/seed_demo_api.py` sigue el ciclo nuevo: un torneo en cada estado, con Festival sin CI, categorías de
      un solo inscrito y llaves con pases directos.

### Bloque 2 — Pesaje

- [x] **Pesaje oficial en la inscripción**, no en el atleta (`weight_kg` queda como el peso declarado). Solo en
      `weigh_in`. Sin tolerancia. [Notion](https://app.notion.com/p/415fae3be03b8125a671c9bf214adff8)
      Hecho: estados `pending`, `failed_first`, `second_allowed`, `cleared`, `disqualified`, `no_show` y
      `not_required`; `DELETE .../weigh-in` corrige un error de carga; el estado es público, los kilos no.
  - Primer pesaje: si entra en su categoría, queda habilitado. Si no, el admin elige: habilitar un segundo pesaje o
    descalificarlo directo (DSQ, Art. 16 de WT).
  - Segundo pesaje: si no entra, queda descalificado directo.
  - No se lo pasa a otra categoría. Las confirmaciones («¿habilitar segundo pesaje?», «¿seguro?») son del frontend.
- [x] **No presentado**: al iniciar el torneo, quien no quedó habilitado queda descalificado, y `start` devuelve la
      lista de los que no se pesaron para mostrarla.
- [x] Festival no tiene divisiones de peso: no necesita pesaje (`not_required`).

### Bloque 3 — Llaves al iniciar

- [x] **Todas las llaves juntas al iniciar**: `POST /start` sortea las llaves de todas las categorías con 2 o más
      inscritos, salvo Festival. Desaparece `POST /categories/{id}/bracket` (`405`). Hecho: las llaves no se re-sortean.
      [Notion](https://app.notion.com/p/415fae3be03b81e59b41cdd9c6196e7f)
- [x] **Sorteo separando clubes en la primera ronda**: dos atletas del mismo club no se enfrentan en la primera ronda,
      salvo que no se pueda evitar. Desde la segunda ronda no importa. Hecho: método greedy por prioridades (ver
      DECISIONS, 2026-11-26).
- [x] **Descalificados en la llave**: van en la llave, marcados, y pierden sin pelear.
  - El sorteo empareja primero a cada descalificado con un habilitado; solo si sobran, se enfrentan entre ellos.
  - Entre dos descalificados no avanza nadie, y su rival de la ronda siguiente gana sin pelear.
  - El combate ganado sin pelear tiene un estado propio, distinto de uno jugado.
  - Si todos los inscritos de una categoría quedan descalificados, no hay ganador: se muestra con todos marcados.
  - Hecho: estados `walkover` y `no_contest`, flags `athlete_red_disqualified` y `athlete_blue_disqualified`; un
    descalificado con bye queda `no_contest` con un solo lado.
- [x] **Festival sin llave**: solo una lista de varones y otra de damas, con nombre y club. Los combates se organizan
      en persona y no se registran (pedido de Abel, 2026-11-26). Todos llevan medalla de oro. No impide finalizar el
      torneo. Hecho: `is_festival` en la categoría; la lista es `/registrants`.
      [Notion](https://app.notion.com/p/415fae3be03b81909a7ee26f2cd969c4)

## 0.10.0 — Llaves de exhibición, campeones y ranking

- [ ] **Sin pelea**: el único inscrito de su categoría, o el único habilitado cuando todos los demás quedaron
      descalificados, es campeón sin pelea. Si todos quedaron descalificados, no hay campeón.
- [ ] **Lista de los que quedaron sin pelea**, aparte (los de arriba). Es la lista de candidatos a exhibición.
      [Notion](https://app.notion.com/p/415fae3be03b81728aefc395fb241292)
- [ ] **Llaves de exhibición, armadas a mano**, con el torneo en curso: el frontend manda la lista de atletas
      elegidos, la API valida que puedan entrar y genera una llave más del grupo «Exhibición» (puede haber varias).
  - Solo entran los que quedaron sin pelea (ver la lista de arriba).
  - Un atleta puede estar en más de una; la API marca a los que ya tienen pelea en ellas.
  - Finalizar el torneo exige que estas llaves también estén terminadas.
- [ ] Podio: oro el ganador de la final, plata el que perdió la final y **un solo bronce**, el semifinalista que
      perdió con el campeón. No hay combate por el bronce.
      [Notion](https://app.notion.com/p/415fae3be03b81b088fae8cc4f877e8a)
- [ ] **Ranking de clubes**, configurable por torneo: oro 7, plata 3, bronce 1 y sin pelea 1 (el único inscrito o el
      único habilitado). Cada niño de Festival suma como un oro (7). Las llaves de exhibición no suman. Sin campeón
      (todos descalificados), nadie suma. Reemplaza al ranking que hoy calcula el frontend.
      [Notion](https://app.notion.com/p/415fae3be03b817fb311feac5e158ed2)

## 0.11.0 — Cuentas e inscripción pública

Por etapas: el login actual del admin sigue funcionando hasta que Firebase esté probado.

- [ ] **Cuentas con Firebase Auth.** La API verifica el token de Firebase; los roles (admin, competidor) se
      guardan en nuestra base. [Notion](https://app.notion.com/p/415fae3be03b818d925eff564e07b1e8)
- [ ] **Una cuenta maneja uno o varios atletas**: normalmente el propio; a veces un tutor maneja los de sus hijos.
- [ ] **Inscripción pública**: con inscripciones abiertas, la cuenta elige entre las categorías en las que el
      atleta encaja (0.8.0). Queda inscrito al enviarla; el admin puede retirarlo mientras sigan abiertas.
- [ ] **Club de una lista**: el competidor elige entre los clubes existentes; si el suyo falta, lo crea el admin.
- [ ] **Foto de perfil** en Cloudflare R2: la base guarda solo la clave del archivo, el frontend la sube con una
      URL firmada, y la ven solo la cuenta y el admin. [Notion](https://app.notion.com/p/415fae3be03b81f9aca6fe1b1d8f62f8)
- [ ] **El admin pasa a Firebase** y se retira el login propio.

## 0.12.0 — Poomsae y las dos modalidades

Al final, cuando todo el ciclo funcione con kyorugi.

- [ ] **Poomsae**: categorías sin llave; una lista con el puntaje de cada competidor (hasta 4 decimales),
      ordenada por puntaje. Modelo de resultado propio; no se reusan `Match` ni `RoundScore`.
      [Notion](https://app.notion.com/p/415fae3be03b81a9b769d4ac7a91532d)
- [ ] **Inscribirse en kyorugi y en poomsae** del mismo torneo: la regla «un atleta, una categoría por torneo» pasa
      a ser por modalidad.

## Más adelante / sin versión

- [ ] **El día del evento** (pedido de Abel, 2026-11-26; va después del ciclo completo).
      [Notion](https://app.notion.com/p/424fae3be03b816cb6b4d0d4ac47579e)
  - Mesa de inspección: habilitar a cada competidor cuando pasa por la mesa, y estados del combate (pendiente →
    inspección → listo → en combate → terminado). [Notion](https://app.notion.com/p/415fae3be03b8180a362fde6c857ac45)
  - Numeración de los combates al sortear las llaves: qué pelea va primero.
  - Áreas de competición: cuántas hay en el torneo y a qué área va cada combate.
  - Horario estimado de cada combate.
  - Poder cambiar esa planificación (orden, área, hora) durante el evento.
- [ ] Roles de pesaje e inspector; por ahora todo lo hace el admin.
      [Notion](https://app.notion.com/p/415fae3be03b8164b7b5e59d660226c7)
- [ ] Vista pública de los combates pendientes o siguientes.
      [Notion](https://app.notion.com/p/415fae3be03b81e9abe9f1bb85380fdc)
- [ ] Permitir editar un round ya cargado (ver `DECISIONS.md`, 2026-10-26: hoy no hace falta y es el cambio con
      más riesgo de dejar datos inconsistentes).
- [ ] Acta de resultados imprimible por categoría, a partir de la plantilla `.docx` de la planilla física.
- [ ] Reglamento público en la vista de visitantes.
      [Notion](https://app.notion.com/p/415fae3be03b814682eec3c95ba1dd9b)
- [ ] Fotos del torneo (sin definir). [Notion](https://app.notion.com/p/415fae3be03b81a085b8d1443e8cbcfd)
- [ ] Link al sitio del club organizador (ej. `keumgangdelfines.com`, configurable) en la vista pública.
- [ ] Adjuntar un PDF a la inscripción (el formulario del WordPress lo pide para Festival y poomsae). Se reevalúa
      con la 0.11.0, que ya trae almacenamiento de archivos.
- [ ] Evitar atletas duplicados sin CI (niños) creados dos veces: el CI único de la 0.4.0 solo cubre a quien lo
      informa.
- [ ] Endpoint que junte la página de detalle de categoría (categoría, inscritos y llave en un request), si el
      frontend externo lo pide.

## Preguntas abiertas para Abel

- En poomsae, ¿un competidor se anota en varias formas o categorías del mismo torneo?

## Descartado

- **Inscripción por planilla Excel** (era la 0.9.0): Abel prefiere que cada uno se inscriba con su cuenta.
  [Notion](https://app.notion.com/p/415fae3be03b813eac58feed16593865)
- **Estatura mínima y máxima en la categoría** (era la 0.8.0): las categorías nunca se dividen por estatura.
- **Grados editables** (era la 0.8.0): los grados son fijos; lo editable son los grupos.
- **Plantillas de categorías editables con nombre** (era la 0.8.0): alcanza con la Copa Diamante fija, que cada
  torneo ajusta con el `PUT` de la estructura.
- **Fusionar categorías de peso contiguas** (Art. 6.1.1 de WT): la categoría de un solo inscrito queda campeón sin
  pelea.
- **Integración con el WordPress del club**: los dos sistemas quedan separados.
