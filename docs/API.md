# Guía para consumir la API

La referencia exacta de cada endpoint y cada campo está en **`/docs`** (Swagger) o **`/redoc`** (más
cómoda para leer), y el contrato completo en **`/openapi.json`**, de donde se puede importar una
colección en Postman o Insomnia, o generar un cliente tipado. Esta guía cubre lo que ahí no se ve
de un vistazo: cómo recorrer los datos, cómo leer una llave, qué hacer con cada error y un flujo completo
de ejemplo.

- URL de desarrollo (para probar sin tocar datos reales): `https://taekwondo-tournament-manager-dev.onrender.com`
- URL de producción: `https://taekwondo-tournament-manager.onrender.com`
- En el plan gratis el servidor se duerme tras 15 minutos sin tráfico: **el primer request puede tardar
  30-50 segundos**. Conviene mostrar un estado de carga y no dar timeouts cortos.
- Mientras la versión sea `0.x` puede haber cambios incompatibles; cada uno se registra en el
  [`CHANGELOG`](../CHANGELOG.md). `GET /health` devuelve la versión desplegada.

## Acceso

Lecturas **públicas**: torneos, categorías, clubes, llaves y combates. Todo `POST`/`PATCH` y las
lecturas de **atletas e inscripciones** piden `Authorization: Bearer <token>` (esas respuestas
incluyen fecha de nacimiento y peso, y hay menores). El token se obtiene en
`POST /api/v1/auth/login` (formulario con `username` y `password`), dura 8 horas y no se renueva solo:
al recibir un `401`, hay que volver a iniciar sesión.

**Desde un navegador (CORS):** un frontend en otro dominio solo puede leer las respuestas si su origen
está autorizado en el servidor (variable `CORS_ORIGINS`). Pasale al administrador del servidor el origen
exacto de tu frontend, por ejemplo `https://mi-frontend.example` o `http://localhost:5173` para
desarrollo. La API no usa cookies: el token viaja siempre en la cabecera.

## Recorrer los datos

Para una vista pública alcanza con tres llamadas, todas sin token:

1. `GET /api/v1/tournaments` — la lista de torneos.
2. `GET /api/v1/categories?tournament_id={id}` — las categorías de un torneo.
3. `GET /api/v1/categories/{id}/bracket` — la llave de una categoría. Responde **`404` mientras no se
   haya sorteado**: tratarlo como "todavía sin llave", no como un error.

Las listas no se paginan: devuelven todos los elementos.

## Cómo leer una llave

La llave trae **todos los combates de todas las rondas** en una lista plana (`matches`). Para dibujar el
árbol:

1. Agrupar por `round_number` (1 es la primera ronda; el número más alto es la final) y ordenar cada
   grupo por `slot` (0, 1, 2… de arriba hacia abajo).
2. El ganador de un combate avanza al combate cuyo id está en `next_match_id` (nulo en la final). El
   combate de `slot` par entrega su ganador al lado **rojo** (`athlete_red_*`) del siguiente, y el de
   `slot` impar al lado **azul**. Dicho de otra forma: el combate `i` de una ronda recibe a los
   ganadores de los combates `2i` y `2i + 1` de la ronda anterior.
3. `size` es la potencia de 2 igual o mayor al número de inscritos. Si sobran lugares, la primera ronda
   tiene **pases directos**: combates con `status: "bye"`, un solo lado ocupado (el otro es `null`) y
   `winner_id` ya definido. Ese ganador ya aparece colocado en el combate de la siguiente ronda, aunque
   nadie haya peleado todavía.
4. Un lado en `null` en una ronda posterior significa que ese atleta todavía no se conoce: espera el
   resultado de un combate anterior.
5. `round_scores` trae el resultado de cada round cargado, numerado por el servidor (1, 2, 3…) en el
   orden de carga. Un combate pasa a `finished` cuando un atleta gana `rounds_to_win` rounds de la
   categoría (2 equivale a un combate al mejor de 3).

Para mostrar nombres no hace falta pedir cada atleta: cada combate trae `athlete_red_name`,
`athlete_blue_name` y `winner_name`.

## Atletas

**Buscar:** `GET /api/v1/athletes?q=texto` devuelve los atletas cuyo nombre o CI contienen el texto, sin
distinguir mayúsculas ni tildes (`perez` encuentra a `Pérez`). Sin `q`, o con `q` vacío, devuelve todos.

**Editar:** `PATCH /api/v1/athletes/{id}` cambia solo los campos que se envían. Para quitar el CI se envía
`"ci": null` (o `""`). Si el cambio de **género o peso** deja al atleta fuera de una categoría en la que
está inscrito:

- En un torneo **en borrador** responde `409` y no cambia nada; `detail` nombra las categorías afectadas.
  Para aceptarlo, repetir la misma petición con `?confirm_withdrawal=true`: el atleta se guarda y se lo
  retira de esas categorías.
- En un torneo **en curso** responde `409` aunque se envíe `confirm_withdrawal=true` (la llave ya está
  sorteada): ese cambio no se puede hacer.
- En un torneo **finalizado** se permite y la inscripción queda como estaba.

Los dos `409` solo se distinguen por el texto. Lo práctico es mostrar `detail` al usuario y ofrecer
"confirmar" una vez: si la petición confirmada vuelve a dar `409`, el cambio no es posible.

## Ciclo de vida de un torneo

El estado no se cambia con `PATCH` sino con dos acciones, y solo avanza (`409` si se repite una o se salta un
paso):

- `POST /api/v1/tournaments/{id}/start`: de `draft` a `in_progress`. Mientras el torneo está en `draft` se
  crean las categorías y se inscribe a los atletas; al iniciarlo esas dos cosas se cierran
  (`POST /categories` y `POST /registrations` responden `409`).
- `POST /api/v1/tournaments/{id}/finish`: de `in_progress` a `finished`, los resultados quedan como
  definitivos. Exige que no queden combates por jugar: si falta alguno responde `409` y `detail` nombra las
  categorías pendientes.

## Errores

Los errores responden `{"detail": "mensaje en español"}`, pensado para mostrarlo tal cual:

| Código | Significa | Ejemplos |
|---|---|---|
| `400` | Falta algo previo para poder hacerlo | generar una llave con menos de 2 inscritos; cargar un round sin los dos atletas definidos |
| `401` | Falta el token, es inválido o venció | volver a iniciar sesión |
| `404` | No existe | id inexistente; llave todavía no sorteada |
| `409` | Choca con datos existentes o con el estado actual | nombre de club o CI repetido; atleta ya inscrito en esa u otra categoría del torneo; llave ya generada; combate ya terminado; torneo que ya empezó o que todavía tiene combates por jugar; edición de atleta (ver arriba) |
| `422` | No cumple una regla, o el cuerpo no tiene el formato esperado | atleta que no encaja en la categoría; round empatado; fecha inválida |

En los `422` de formato (campo faltante, tipo incorrecto), `detail` no es un texto sino una **lista** con
el formato estándar de FastAPI (`loc`, `msg`, `type` por cada error). Cada endpoint de `/docs` lista los
códigos que puede devolver.

## Valores de los enums

Viajan en inglés; para mostrarlos al usuario, esta es la traducción que usa la web del proyecto:

| Campo | Valor | Se muestra como |
|---|---|---|
| `status` de un torneo | `draft` / `in_progress` / `finished` | Borrador / En curso / Finalizado |
| `status` de un combate | `pending` / `bye` / `finished` | Pendiente / Pase directo / Finalizado |
| `gender` | `male` / `female` | Masculino / Femenino |
| `belt_group` | `color` / `black` | Cinturón de color / Cinturón negro |
| `discipline` | `sparring` | Combate |

## Ejemplo de flujo con `curl`

Los ids (`1`) son ilustrativos: en una base con datos hay que usar el `id` que devuelve cada `POST`.

```bash
BASE=https://taekwondo-tournament-manager-dev.onrender.com

# 1) Iniciar sesión y guardar el token
TOKEN=$(curl -s -X POST $BASE/api/v1/auth/login -d "username=admin&password=TU_CLAVE" \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['access_token'])")
AUTH="Authorization: Bearer $TOKEN"
JSON="Content-Type: application/json"

# 2) Club, torneo y categoría
curl -s -X POST $BASE/api/v1/clubs -H "$AUTH" -H "$JSON" -d '{"name": "Dojang Central"}'
curl -s -X POST $BASE/api/v1/tournaments -H "$AUTH" -H "$JSON" \
  -d '{"name": "Copa Cochabamba", "date": "2026-11-15", "location": "Cochabamba, Bolivia"}'
curl -s -X POST $BASE/api/v1/categories -H "$AUTH" -H "$JSON" \
  -d '{"tournament_id": 1, "gender": "male", "age_label": "Cadete", "min_age": 12, "max_age": 14,
       "belt_group": "color", "weight_label": "Hasta 45kg", "max_weight": 45}'

# 3) Atletas e inscripciones (repetir por cada atleta; la llave necesita al menos 2)
curl -s -X POST $BASE/api/v1/athletes -H "$AUTH" -H "$JSON" \
  -d '{"name": "Mateo Quispe", "ci": "1234567", "birth_date": "2012-03-14", "gender": "male",
       "belt_rank": "verde", "weight_kg": 38.5, "club_id": 1}'
curl -s -X POST $BASE/api/v1/registrations -H "$AUTH" -H "$JSON" -d '{"athlete_id": 1, "category_id": 1}'

# 4) Generar la llave y consultarla (la consulta es pública)
curl -s -X POST $BASE/api/v1/categories/1/bracket -H "$AUTH"
curl -s $BASE/api/v1/categories/1/bracket

# 5) Cargar un round: solo los puntos; el servidor lo numera y no admite empates
curl -s -X POST $BASE/api/v1/matches/1/rounds -H "$AUTH" -H "$JSON" \
  -d '{"red_points": 12, "blue_points": 5}'
```
