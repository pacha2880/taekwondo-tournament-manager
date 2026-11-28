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
