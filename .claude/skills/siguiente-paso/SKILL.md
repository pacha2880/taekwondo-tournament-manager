---
name: siguiente-paso
description: Decide qué es lo siguiente que hay que implementar — lee el backlog, lo hecho y lo prometido, junta las ambigüedades en una sola tanda de preguntas y deja el spec de la próxima versión en el backlog. Usar cuando el usuario pregunta «¿qué sigue?», «¿cuál es el siguiente paso?» o pide un plan. Solo planifica: no implementa.
---

# Siguiente paso

El resultado es **el spec de la próxima versión completa**, acordado con el usuario y guardado en `docs/BACKLOG.md`.
La unidad es la versión, no el ítem suelto. Esta skill no programa, no commitea y no arranca la implementación:
termina en el spec y espera la confirmación del usuario.

## 1. Leer (solo esto, en paralelo)

- **Repo, con un subagente `explorador` (`model: "haiku"`):** `docs/BACKLOG.md` (ítems sin terminar, con su
  texto), `[Unreleased]` de `CHANGELOG.md`, `git log` desde el último tag, la versión de producción (`/health`) y si
  hay un PR `dev` → `main` abierto. Pedirle hechos textuales en listas, sin opinar ni resumir: el cruce se hace acá.
- **Notion, en la conversación principal mientras corre el agente** (el `explorador` no tiene el conector): las
  reuniones nuevas desde la última versión liberada y las filas «Aceptado» de Pedidos e ideas (los enlaces están
  en el backlog).

## 2. Cruzar

Listar en pocas líneas lo que no cuadra:

- lo prometido (a Abel o a Kike) que no está en el backlog o no está hecho;
- lo hecho que el backlog sigue mostrando como pendiente;
- versiones distintas entre el backlog y Notion;
- pedidos de reuniones que nadie anotó;
- reglas del backlog que chocan con el código o entre sí.

Lo menor (un texto viejo, una versión mal anotada) se corrige al guardar el spec, sin preguntar.

## 3. Elegir

La próxima versión del backlog sin liberar, salvo que algo la bloquee o haya un hueco más urgente (algo prometido
que no funciona en producción). En ese caso, proponer primero el arreglo, con una línea de por qué.

## 4. Preguntar (una sola tanda)

Todas las ambigüedades de la versión juntas, antes de cualquier plan. Hasta 4 preguntas por tanda, cada una sola
(se entiende sin el resto del mensaje), con 2 a 4 opciones y la recomendada primero. Las preguntas para el cliente
(Abel) van aparte, como lista, y no frenan si se puede avanzar sin ellas. Si no hay ambigüedades, decirlo.

## 5. Proponer el spec

En alto nivel, sin detalles de implementación:

- qué cambia en la API, endpoint por endpoint, y qué reglas nuevas hay;
- qué es incompatible y qué hay que acordar con Kike antes;
- 2 o 3 bloques grandes en orden, cada uno implementable de una vez.

## 6. Guardar y parar

Con las respuestas del usuario, escribir el spec en el ítem de la versión en `docs/BACKLOG.md` (y el porqué de cada
decisión no obvia en `docs/DECISIONS.md`). Dejar los cambios sin commitear, mostrar el resumen y terminar. La
implementación es otro flujo y la arranca el usuario.
