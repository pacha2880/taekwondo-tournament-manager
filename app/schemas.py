# Se usa "import datetime" (no "from datetime import date") porque un campo Pydantic llamado
# `date` con tipo `date` y valor por defecto se pisa a sí mismo: la asignación ocurre antes de
# que se evalúe la anotación.
import datetime
import math
import re
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, field_validator

from app.models import Discipline, Gender, Grade, MatchStatus, TournamentStatus


# Postgres `Integer` (int4). SQLite doesn't enforce it, so a bigger number passed the tests and was a 500 in Postgres.
INT4_MAX = 2_147_483_647
Int4 = Annotated[int, Field(ge=-INT4_MAX - 1, le=INT4_MAX)]
Int4Id = Annotated[int, Field(ge=1, le=INT4_MAX)]


class ErrorResponse(BaseModel):
    detail: str = Field(description="Mensaje del error, en español.", examples=["Club no encontrado"])


class TokenResponse(BaseModel):
    access_token: str = Field(description="Token JWT para enviar como `Authorization: Bearer <token>`.")
    token_type: str = Field(default="bearer", description="Siempre `bearer`.")
    expires_in: int = Field(description="Segundos que faltan para que el token venza (8 horas).", examples=[28800])


class ClubBase(BaseModel):
    name: str = Field(max_length=120, description="Nombre del club. No puede repetirse.", examples=["Dojang Central"])


class ClubCreate(ClubBase):
    pass


class ClubUpdate(BaseModel):
    name: str | None = Field(
        default=None, max_length=120, description="Nuevo nombre. No puede repetirse. Si no se envía, no cambia."
    )


class ClubRead(ClubBase):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Identificador del club.")


CI_REGEX = r"[0-9]{5,9}(?:-[0-9A-Z]{2})?"


def normalize_ci(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip().upper()
    if not value:
        return None
    if not re.fullmatch(CI_REGEX, value):
        raise ValueError("el CI debe tener de 5 a 9 dígitos y, si corresponde, un complemento (ej. 1234567-1A)")
    return value


NormalizedCi = Annotated[str | None, AfterValidator(normalize_ci)]


def check_one_decimal(value: float | None) -> float | None:
    # Weight divisions go in tenths (48 → 48.1): a weight like 48.05 would fall between two divisions.
    # Infinity passes round() unchanged and then can't be serialized back to JSON (500).
    if value is not None and not (math.isfinite(value) and round(value, 1) == value):
        raise ValueError("el peso tiene que ser un número finito con un decimal como máximo")
    return value


# Only on input schemas: the *Read ones also validate what's already stored, which may predate this rule.
WeightKg = Annotated[float, AfterValidator(check_one_decimal)]


class AthleteBase(BaseModel):
    name: str = Field(max_length=120, description="Nombre completo del atleta.", examples=["Mateo Quispe Mamani"])
    ci: NormalizedCi = Field(
        default=None,
        description=(
            "Cédula de identidad, opcional (hay niños que todavía no tienen). Si se informa: de 5 a 9 "
            "dígitos y, si corresponde, un complemento de 2 caracteres separado por guion; sin lugar de "
            "expedición. Se guarda sin espacios y en mayúsculas, y no puede repetirse. Si no tiene, se omite, o se envía `null` o texto vacío (la respuesta devuelve `null`)."
        ),
        examples=["1234567", "1234567-1A"],
        json_schema_extra={"pattern": f"^{CI_REGEX}$"},
    )
    birth_date: datetime.date = Field(description="Fecha de nacimiento (`YYYY-MM-DD`).", examples=["2012-03-14"])
    gender: Gender = Field(description="Género del atleta. Debe coincidir con el de la categoría en que se inscribe.")
    grade: Grade = Field(description="Grado del atleta.", examples=["kup_6"])
    weight_kg: float = Field(description="Peso en kilogramos, con un decimal como máximo.", examples=[38.5])
    height_cm: int | None = Field(
        default=None,
        ge=50,
        le=250,
        description="Estatura en centímetros, opcional (de 50 a 250). No se usa para asignar categorías.",
        examples=[152],
    )
    club_id: Int4Id = Field(description="Id del club al que pertenece. El club debe existir.")


class AthleteCreate(AthleteBase):
    @field_validator("weight_kg")
    @classmethod
    def check_weight(cls, value: float) -> float:
        return check_one_decimal(value)


class AthleteUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=120, description="Nuevo nombre. Si no se envía, no cambia.")
    ci: NormalizedCi = Field(
        default=None,
        description=(
            "Nuevo CI, con el mismo formato que al crear. Si no se envía, no cambia; `null` o texto vacío "
            "lo borra."
        ),
        json_schema_extra={"pattern": f"^{CI_REGEX}$"},
    )
    birth_date: datetime.date | None = Field(
        default=None,
        description="Nueva fecha de nacimiento (`YYYY-MM-DD`). Si no se envía, no cambia. Ver las reglas con inscripciones en la operación.",
    )
    gender: Gender | None = Field(
        default=None,
        description="Nuevo género. Si no se envía, no cambia. Ver las reglas con inscripciones en la operación.",
    )
    grade: Grade | None = Field(
        default=None,
        description="Nuevo grado. Si no se envía, no cambia. Ver las reglas con inscripciones en la operación.",
    )
    weight_kg: WeightKg | None = Field(
        default=None,
        description="Nuevo peso en kilogramos, con un decimal como máximo. Si no se envía, no cambia. Ver las reglas con inscripciones en la operación.",
    )
    height_cm: int | None = Field(
        default=None,
        ge=50,
        le=250,
        description="Nueva estatura en centímetros (de 50 a 250). Si no se envía, no cambia; `null` la borra.",
    )
    club_id: Int4Id | None = Field(
        default=None, description="Id del nuevo club, que debe existir. Si no se envía, no cambia."
    )


class AthleteRead(AthleteBase):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Identificador del atleta.")
    club: ClubRead = Field(description="Club al que pertenece el atleta.")


class TournamentBase(BaseModel):
    name: str = Field(max_length=150, description="Nombre del torneo.", examples=["Copa Cochabamba"])
    date: datetime.date = Field(description="Fecha del torneo (`YYYY-MM-DD`).", examples=["2026-11-15"])
    location: str = Field(max_length=150, description="Lugar donde se realiza.", examples=["Cochabamba, Bolivia"])


class TournamentCreate(TournamentBase):
    pass


class TournamentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=150, description="Nuevo nombre. Si no se envía, no cambia.")
    date: datetime.date | None = Field(default=None, description="Nueva fecha (`YYYY-MM-DD`). Si no se envía, no cambia.")
    location: str | None = Field(default=None, max_length=150, description="Nuevo lugar. Si no se envía, no cambia.")


class TournamentRead(TournamentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Identificador del torneo.")
    status: TournamentStatus = Field(description="Estado actual del torneo.")


class CategoryBase(BaseModel):
    tournament_id: Int4Id = Field(description="Id del torneo al que pertenece la categoría. El torneo debe existir.")
    discipline: Discipline = Field(
        default=Discipline.SPARRING,
        description="Modalidad. Hoy solo existe `sparring` (combate), que es el valor por defecto.",
    )
    gender: Gender = Field(description="Género de la categoría. Solo se inscriben atletas del mismo género.")
    age_label: str = Field(max_length=60, description="Nombre del rango de edad.", examples=["Cadete"])
    min_age: Int4 = Field(description="Edad mínima, en años.", examples=[12])
    max_age: Int4 | None = Field(
        default=None, description="Edad máxima, en años. Si es nulo, no hay tope.", examples=[14]
    )
    weight_label: str = Field(
        max_length=60,
        description="Nombre de la división de peso.",
        examples=["48.1–55 kg"],
    )
    min_weight: float | None = Field(
        default=None,
        description="Peso mínimo en kg, con un decimal como máximo. Si se define, no se inscriben atletas más livianos.",
    )
    max_weight: float | None = Field(
        default=None,
        description="Peso máximo en kg, con un decimal como máximo. Si se define, no se inscriben atletas más pesados.",
        examples=[45],
    )
    rounds_to_win: Int4 = Field(
        default=2,
        description="Rounds que hay que ganar para ganar un combate (2 equivale a un combate al mejor de 3).",
    )


class CategoryRead(CategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Identificador de la categoría.")
    grade_group_id: int | None = Field(
        description="Id del grupo de grado de la categoría. Es nulo en Festival y en las categorías anteriores a la 0.8.0."
    )
    grade_group_name: str | None = Field(
        description="Nombre del grupo de grado (por ejemplo `Novatos`). Es nulo en Festival y en las categorías "
        "anteriores a la 0.8.0.",
        examples=["Novatos"],
    )
    name: str = Field(
        description="Nombre completo de la categoría, listo para mostrar: grupo de grado, edad, género y peso, "
        "separados por ` · `. Distingue categorías que solo difieren en el grupo de grado.",
        examples=["Principiantes · Cadete · Masculino · 37.1–41 kg"],
    )
    has_bracket: bool = Field(
        description="Si la categoría ya tiene la llave generada. Mientras es `false`, lo que se muestra al público es "
        "la lista de inscritos (`GET /categories/{id}/registrants`)."
    )


class GradeGroupRead(BaseModel):
    id: int = Field(description="Identificador del grupo de grado. Se conserva al editar la estructura.")
    name: str = Field(description="Nombre del grupo.", examples=["Novatos"])
    from_grade: Grade = Field(description="Primer grado del grupo.")
    to_grade: Grade = Field(
        description="Último grado del grupo: el anterior al primero del grupo siguiente (el último grupo llega hasta "
        "`dan`)."
    )


class WeightLimitsRead(BaseModel):
    male: list[float] = Field(
        description="Límites superiores de las divisiones de peso masculinas, en kg y de menor a mayor. Cada división "
        "va desde el límite anterior + 0,1 hasta el suyo, y la última es «más de» el último límite.",
        examples=[[48, 55, 63, 73]],
    )
    female: list[float] = Field(description="Igual que `male`, para las divisiones femeninas.", examples=[[44, 49, 55, 63]])


class AgeDivisionRead(BaseModel):
    id: int = Field(description="Identificador de la división de edad. Se conserva al editar la estructura.")
    name: str = Field(description="Nombre de la división.", examples=["Junior"])
    from_age: int = Field(
        description="Edad mínima. La edad se cuenta por año de nacimiento: año del torneo menos año de nacimiento.",
        examples=[15],
    )
    to_age: int | None = Field(
        description="Edad máxima: la anterior a la mínima de la división siguiente. Es nula en la última (sin tope).",
        examples=[17],
    )
    has_weight_divisions: bool = Field(
        description="Si se divide por peso. Si es `false` (por ejemplo Festival), hay una sola categoría por grupo y "
        "género, sin importar el peso."
    )
    weight_limits: WeightLimitsRead = Field(description="Divisiones de peso por género (vacías si no se divide por peso).")


class CategoryStructureRead(BaseModel):
    """Estructura de categorías de un torneo: sus categorías son todas las combinaciones de grupo de grado, género,
    división de edad y división de peso."""

    grade_groups: list[GradeGroupRead] = Field(
        description="Grupos de grado, de menor a mayor. Entre todos cubren cada grado exactamente una vez."
    )
    age_divisions: list[AgeDivisionRead] = Field(
        description="Divisiones de edad, de menor a mayor. Entre todas cubren cada edad exactamente una vez."
    )


class GradeGroupInput(BaseModel):
    id: int | None = Field(
        default=None,
        description="Id de un grupo que ya existe, para conservarlo (y sus categorías). Sin id, se crea uno nuevo; los "
        "grupos que no se envían se borran, salvo el último, que no se puede quitar.",
    )
    name: str = Field(max_length=60, description="Nombre del grupo, hasta 60 caracteres. No puede repetirse.", examples=["Novatos"])
    from_grade: Grade = Field(
        description="Primer grado del grupo. El primer grupo empieza en `kup_10` y cada uno empieza después del anterior."
    )


class WeightLimitsInput(BaseModel):
    male: list[WeightKg] = Field(
        max_length=30,
        description="Límites superiores masculinos en kg (con un decimal como máximo), de menor a mayor, sin repetir y "
        "hasta 30. Vacía: una sola división "
        "con todos los pesos.",
        examples=[[48, 55, 63, 73]],
    )
    female: list[WeightKg] = Field(
        max_length=30, description="Igual que `male`, para las divisiones femeninas.", examples=[[44, 49, 55, 63]]
    )


class AgeDivisionInput(BaseModel):
    id: int | None = Field(
        default=None,
        description="Id de una división que ya existe, para conservarla (y sus categorías). Sin id, se crea una nueva; las "
        "que no se envían se borran.",
    )
    name: str = Field(
        max_length=60,
        description="Nombre de la división, hasta 60 caracteres. No puede repetirse ni llamarse Festival.",
        examples=["Junior"],
    )
    from_age: int = Field(
        le=120,
        description="Edad mínima (por año de nacimiento), hasta 120. La primera división empieza en 10, justo después "
        "de Festival, y cada una empieza después de la anterior.",
        examples=[15],
    )
    weight_limits: WeightLimitsInput = Field(description="Divisiones de peso por género.")


class CategoryStructureUpdate(BaseModel):
    """Estructura completa de categorías de un torneo, sin Festival (que es fijo y no se envía)."""

    grade_groups: list[GradeGroupInput] = Field(description="Grupos de grado, de menor a mayor.")
    age_divisions: list[AgeDivisionInput] = Field(description="Divisiones de edad después de Festival, de menor a mayor.")


class CategoryPreview(BaseModel):
    grade_group_name: str | None = Field(description="Grupo de grado. Es nulo en Festival, que no se divide por grado.")
    gender: Gender = Field(description="Género de la categoría.")
    age_label: str = Field(description="División de edad.", examples=["Junior"])
    weight_label: str = Field(description="División de peso.", examples=["48.1–55 kg"])


class CategoryStructureResult(CategoryStructureRead):
    categories: list[CategoryPreview] = Field(
        description="Las categorías que corresponden a la estructura (con `validate_only=true`, las que quedarían)."
    )


class RegistrantRead(BaseModel):
    """Inscrito de una categoría, solo con datos públicos: sin CI, fecha de nacimiento ni peso."""

    model_config = ConfigDict(from_attributes=True)

    athlete_id: int = Field(description="Id del atleta.")
    name: str = Field(description="Nombre del atleta.", examples=["Mateo Quispe Mamani"])
    club: str = Field(description="Nombre del club del atleta.", examples=["Dojang Central"])


class RoundScoreCreate(BaseModel):
    round_number: Int4Id = Field(
        description="Número del round que se está cargando: el siguiente al último guardado (1 si no hay ninguno).",
        examples=[1],
    )
    red_points: Int4 = Field(description="Puntos del lado rojo en este round.", examples=[12])
    blue_points: Int4 = Field(description="Puntos del lado azul en este round.", examples=[5])


class RoundScoreRead(RoundScoreCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Identificador del resultado del round.")
    match_id: int = Field(description="Id del combate al que pertenece el round.")
    round_number: int = Field(
        description="Número del round dentro del combate, desde 1.",
        examples=[1],
    )
    round_winner_id: int | None = Field(description="Atleta que ganó el round: el del lado con más puntos.")


class MatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Identificador del combate.")
    round_number: int = Field(
        description="Ronda de la llave a la que pertenece el combate: 1 es la primera y la última es la final."
    )
    slot: int = Field(description="Posición del combate dentro de su ronda, desde 0, de arriba hacia abajo.")
    athlete_red_id: int | None = Field(
        description="Id del atleta del lado rojo. Es nulo si todavía no se definió (espera a un combate anterior) "
        "o si el combate es un pase directo y este lado queda vacío."
    )
    athlete_red_name: str | None = Field(default=None, description="Nombre del atleta del lado rojo.")
    athlete_blue_id: int | None = Field(
        description="Id del atleta del lado azul. Es nulo si todavía no se definió o si es un pase directo."
    )
    athlete_blue_name: str | None = Field(default=None, description="Nombre del atleta del lado azul.")
    winner_id: int | None = Field(
        description="Id del ganador del combate. Es nulo mientras no termine; en un pase directo, es el atleta que pasa."
    )
    winner_name: str | None = Field(default=None, description="Nombre del ganador del combate.")
    next_match_id: int | None = Field(
        description="Id del combate de la siguiente ronda al que avanza el ganador. Es nulo en la final."
    )
    status: MatchStatus = Field(description="Estado del combate.")
    round_scores: list[RoundScoreRead] = Field(description="Resultado de cada round cargado, en orden.")


class BracketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Identificador de la llave.")
    category_id: int = Field(description="Id de la categoría a la que pertenece la llave.")
    size: int = Field(
        description="Cantidad de lugares de la llave: la potencia de 2 igual o mayor al número de inscritos. "
        "Los lugares que sobran se resuelven con pases directos.",
        examples=[8],
    )
    generated_at: datetime.datetime = Field(description="Fecha y hora (UTC) en que se sorteó la llave.")
    matches: list[MatchRead] = Field(description="Todos los combates de todas las rondas.")


class RegistrationBase(BaseModel):
    athlete_id: Int4Id = Field(description="Id del atleta que se inscribe. El atleta debe existir.")
    category_id: Int4Id = Field(description="Id de la categoría en la que se inscribe. La categoría debe existir.")


class RegistrationCreate(RegistrationBase):
    pass


class RegistrationRead(RegistrationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Identificador de la inscripción.")
    athlete: AthleteRead = Field(description="Datos del atleta inscrito.")
    category: CategoryRead = Field(description="Datos de la categoría.")
