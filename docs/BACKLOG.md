# Backlog

Lo aceptado y ordenado en versiones. Las versiones ya liberadas están en [`CHANGELOG.md`](../CHANGELOG.md).

## Cómo se usa

- **Notion, [Pedidos e ideas](https://app.notion.com/p/542c165c4b604d2aa3901cd55d86d24c):** pedidos del cliente e
  ideas por decidir, con el texto original de cada reunión. Lo leen el cliente y el equipo del frontend.
- **Este archivo:** solo lo aceptado, en versiones y con el detalle técnico. Cada ítem enlaza a su fila de Notion;
  la fila pasa a «Aceptado» y anota la versión. El texto no se copia de un lado al otro.
- **[`DECISIONS.md`](DECISIONS.md):** el porqué de cada decisión técnica.

Reglas de cada versión: `pytest` en verde (SQLite en local; Postgres lo corre el CI del PR); migraciones solo
aditivas; los cambios incompatibles de la API se juntan en la versión, y cada cambio de la API se le avisa al frontend externo
en Notion apenas llega a `dev` (después del push; ver la skill `commit`). **Solo API:** la interfaz es el frontend externo.

## Ciclo de vida objetivo del torneo

**En preparación** (oculto; el admin arma las categorías) → **Inscripciones abiertas** (cada competidor se inscribe;
se cierran solas en la fecha límite) → **Pesaje** (la lista de inscritos se hace pública) → **En curso** (todas las
llaves juntas) → **Finalizado**.

La 0.6.0 deja tres de esos estados (inscripciones abiertas, en curso, finalizado); la 0.9.0 agrega los otros dos.

## 0.9.0 — Ciclo nuevo y pesaje

Cambia el comportamiento de la API: va marcado como incompatible en el CHANGELOG.

- [ ] **Estado «En preparación»** (`draft`, el valor que ya existe): pasa a ser el inicial y cambia de
      significado. El torneo no se ve en público y el admin arma las categorías; todavía no se inscribe a nadie.
      [Notion](https://app.notion.com/p/415fae3be03b818fa550dabd0c34074a)
- [ ] **Estado «Inscripciones abiertas»** (`registration_open`, valor nuevo): se llega desde En preparación cuando
      el admin abre las inscripciones, con una acción nueva como `start` y `finish`. Las categorías quedan como
      vienen de En preparación. Se inscribe y se retira como hoy en `draft` (`category_mismatch`, una categoría por
      torneo, `confirm_withdrawal`); llaves y resultados siguen dando `409`. El público ve el torneo, pero **no la
      lista de inscritos**: hoy `GET /categories/{id}/registrants` la muestra y el frontend externo la usa, así que
      ocultarla se acuerda antes con Kike. Se sale solo por la fecha límite, hacia Pesaje. Falta decidir si el
      admin puede seguir yendo directo a En curso con `POST .../start`.
- [ ] **Migración de los torneos en `draft`**: pasan a `registration_open`, para que los que ya existen (también el
      torneo demo de producción) sigan visibles y aceptando inscripciones. Las reglas de `app/api/lifecycle.py` pasan de
      `draft` a `registration_open`.
- [ ] **Fecha límite de inscripción** (guardada en UTC, mostrada en hora de Bolivia). Pasada la fecha, el torneo
      queda en Pesaje solo. El estado se calcula al consultarlo con una función pura del torneo y la hora; leer no
      escribe en la base, y no hace falta un cron.
- [ ] **Estado «Pesaje»**: se cierran las inscripciones y la lista de inscritos se hace pública (hasta entonces
      está oculta). El admin pasa a En curso a mano. [Notion](https://app.notion.com/p/415fae3be03b81568bd7f3cfcc2df971)
- [ ] **Pesaje con segundo intento**: el admin anota el peso; si no entra en la categoría, hay un segundo pesaje;
      si tampoco entra o no se presenta, queda descalificado (DSQ, Art. 16 de WT). No se lo pasa a otra categoría.
      [Notion](https://app.notion.com/p/415fae3be03b8125a671c9bf214adff8)
- [ ] **Todas las llaves juntas al pasar a En curso.** Desaparece la generación por categoría. El descalificado
      va en la llave y pierde su combate sin pelear. [Notion](https://app.notion.com/p/415fae3be03b81e59b41cdd9c6196e7f)
- [ ] **Sorteo separando clubes en la primera ronda**: dos atletas del mismo club no se enfrentan en la primera
      ronda, salvo que no se pueda evitar. Desde la segunda ronda no importa.
- [ ] **Festival (hasta 9 años)**: categoría sin llave ni división de peso; se muestra como lista con nombre y
      club. [Notion](https://app.notion.com/p/415fae3be03b81909a7ee26f2cd969c4)

## 0.10.0 — Campeones y ranking

- [ ] Categoría con un solo inscrito: ese atleta es campeón sin pelea, sin llave ni combate artificial.
- [ ] Al iniciar el torneo, tabla aparte con las categorías de un solo inscrito.
      [Notion](https://app.notion.com/p/415fae3be03b81728aefc395fb241292)
- [ ] Podio: oro el ganador de la final, plata el que perdió la final y **un solo bronce**, el semifinalista que
      perdió con el campeón. No hay combate por el bronce.
      [Notion](https://app.notion.com/p/415fae3be03b81b088fae8cc4f877e8a)
- [ ] Ranking de clubes: oro 7, plata 3, bronce 1 y categoría sin pelea 1, configurable por torneo.
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

## 1.0.0

- [ ] Borrar la columna `athletes.belt_rank` (reemplazada por `grade` en la 0.7.0; ver `DECISIONS.md`, 2026-11-13).
- [ ] Borrar la columna `categories.belt_group` y el enum `BeltGroup` (salió de la API en la 0.8.1; ver `DECISIONS.md`,
      2026-11-25). Antes hay que resolver que el `name` de las categorías históricas la usa para separar color de negro.

## Más adelante / sin versión

- [ ] Mesa de inspección y estados del combate (pendiente → inspección → listo → en combate → terminado).
      [Notion](https://app.notion.com/p/415fae3be03b8180a362fde6c857ac45)
- [ ] Área de combate de cada categoría o combate (área 1, área 2…), cuando haya mesa de inspección.
- [ ] Roles de pesaje e inspector; por ahora todo lo hace el admin.
      [Notion](https://app.notion.com/p/415fae3be03b8164b7b5e59d660226c7)
- [ ] Vista pública de los combates pendientes o siguientes.
      [Notion](https://app.notion.com/p/415fae3be03b81e9abe9f1bb85380fdc)
- [ ] Permitir editar un round ya cargado (ver `DECISIONS.md`, 2026-10-26: hoy no hace falta y es el cambio con
      más riesgo de dejar datos inconsistentes).
- [ ] Acta de resultados imprimible por categoría, a partir de la plantilla `.docx` de la planilla física.
- [ ] Auto-refresh en vivo de la vista pública.
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
