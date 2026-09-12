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
