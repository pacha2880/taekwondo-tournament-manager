# Decisiones de arquitectura (ADR liviano)

Registro corto de decisiones no obvias, con el porqué, para no tener que re-derivar el
razonamiento más adelante.

## 2026-09-11 — Jinja2 en vez de SPA separado

Se eligió server-side rendering con FastAPI + Jinja2 en una sola app, en vez de una API
separada + frontend en React/Vue. Motivo: el objetivo es un despliegue gratuito simple (un
solo servicio) y que el foco de aprendizaje sea el backend, que es lo que evalúa el puesto al
que se está aplicando. htmx queda como mejora incremental opcional, no bloqueante.

## 2026-09-11 — Render + Neon en vez de Railway/Fly.io/Render-Postgres

Investigado en 2026: Railway ya no tiene tier gratis real (solo $5 de crédito único),
Fly.io ya no da tier gratis a cuentas nuevas (solo trial de 2h) y pide tarjeta. Render sigue
con tier gratis real (750h/mes, sin tarjeta) pero su Postgres gratis expira a los 90 días.
Neon tiene Postgres gratis sin fecha de expiración. Combo elegido: Render (web service) +
Neon (Postgres), ambos gratis indefinidamente, para un proyecto portafolio que debe seguir
vivo en el tiempo.

## 2026-09-11 — Integración con LLM fuera de alcance

El job posting menciona LLM APIs/LangChain/Bedrock como *nice-to-have*, no como requisito.
No hay una necesidad real del dominio (torneos de taekwondo) que un LLM resuelva mejor que
lógica normal. Se descarta del plan inicial; se reconsidera solo si sobra tiempo al final,
como feature aislada y justificada (no forzada).

## 2026-09-11 — `discipline` se mantiene aunque hoy solo tenga un valor

`Category.discipline` (hoy solo `SPARRING`) se mantiene desde el modelo inicial en vez de
agregarse después. Agregar una columna nueva a una tabla que ya tiene datos en producción es
una migración con más riesgo que agregar una columna vacía a un modelo nuevo. Es una decisión
barata de tomar ahora y cara de tomar después.

## 2026-09-11 — Sin tabla oficial de pesos hardcodeada

Las tablas de peso por categoría (cinturón/edad/género) varían por federación y país, y
cambian con el tiempo. En vez de modelarlas como datos fijos del sistema, `Category` tiene un
`weight_label` de texto libre que el admin define al crear cada categoría del torneo. Esto
evita mantener datos regulatorios que no son el problema que este proyecto busca resolver.

## 2026-09-11 — `Club` como entidad propia, obligatoria en `Athlete`

Un atleta pertenece siempre a un club (no es opcional, no cambia por torneo). Se modela como
`Club(id, name)` + `Athlete.club_id` (FK obligatoria) en vez de un campo de texto libre en
`Athlete`, para no duplicar nombres de club con variaciones de escritura.

## 2026-09-12 — Desarrollo dentro de WSL desde el día 0

El usuario tiene Windows como host pero el despliegue es Linux (Render) y ya tenía WSL con
Ubuntu-22.04 instalado. En vez de dividir el desarrollo entre venv nativo de Windows y Docker
en WSL, todo el proyecto (venv, git, Docker cuando llegue la fase 7) vive dentro de WSL, en el
filesystem nativo de la distro (no en `/mnt/c/...`, que es notablemente más lento y da
problemas con file-watchers). Esto evita divergencias entre "funciona en mi máquina" (Windows)
y "falla en el contenedor" (Linux). Se verificó Python 3.10.12 disponible (no 3.12; ninguna
feature del plan lo requiere) y que Docker todavía no tiene la integración WSL activada en
esta máquina — pendiente antes de la fase 7, no bloqueante ahora.

## 2026-09-22 — Fase 5: diseño propio y minimalista, no clonar sitios de marketing

Se consideró usar como referencia visual el sitio de una escuela de taekwondo real
(marketing/institucional, con tienda y noticias), pero se descartó: es un tipo de producto
distinto (vender clases, no mostrar datos de un torneo en vivo). Se optó por un diseño propio
y lo más simple posible — la parte visual queda deliberadamente básica, para que decisiones
de diseño "de verdad" se puedan tomar después (por alguien más, o más adelante) sin tocar
lógica de negocio, ya que las plantillas Jinja2 están separadas de `app/services`/`app/api`.

Decisiones concretas de la Fase 5:
- **CSS**: Bootstrap 5 vía CDN (un `<link>`, sin build step) — consistente con "tecnología
  simple", da componentes listos (navbar, list-group, badges) sin escribir CSS a mano.
  Paleta: sin personalización por ahora (Bootstrap por defecto); si se quiere un esquema
  rojo/azul (colores reales de protectores, y ya son los nombres que usa el modelo de datos
  — `athlete_red_id`/`athlete_blue_id`) queda como mejora visual posterior, no bloqueante.
- **Navegación**: tres niveles siguiendo la jerarquía de datos — `/` (lista de torneos) →
  `/torneos/{id}` (categorías de ese torneo) → `/categorias/{id}` (llave + resultados de esa
  categoría). Sin buscador ni filtros.
- **Vista de la llave**: lista de texto agrupada por ronda (no un árbol visual con líneas
  conectoras). Cada combate muestra los dos atletas, su estado (`pending`/`bye`/`finished`),
  el ganador si ya lo hay, y el puntaje de cada round si el combate ya se jugó.
- **Sin auto-refresh todavía**: la página se recarga manualmente. El auto-refresh en vivo
  (polling con htmx) queda anotado como el primer ítem de la Fase 9 (mejoras post-deploy),
  junto con cualquier otra mejora que se nos ocurra en el camino — deliberadamente no se
  implementa antes de tener el sistema desplegado y funcionando de punta a punta.
