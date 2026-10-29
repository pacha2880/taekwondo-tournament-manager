# Se usa "import datetime" (no "from datetime import date") porque un campo Pydantic llamado
# `date` con tipo `date` y valor por defecto se pisa a sí mismo: la asignación ocurre antes de
# que se evalúe la anotación.
import datetime
import re
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

from app.models import BeltGroup, Discipline, Gender, MatchStatus, TournamentStatus


class ErrorResponse(BaseModel):
    detail: str = Field(description="Mensaje del error, en español.", examples=["Club no encontrado"])


class TokenResponse(BaseModel):
    access_token: str = Field(description="Token JWT para enviar como `Authorization: Bearer <token>`.")
    token_type: str = Field(default="bearer", description="Siempre `bearer`.")
    expires_in: int = Field(description="Segundos que faltan para que el token venza (8 horas).", examples=[28800])


class ClubBase(BaseModel):
    name: str = Field(description="Nombre del club. No puede repetirse.", examples=["Dojang Central"])


class ClubCreate(ClubBase):
    pass


class ClubUpdate(BaseModel):
    name: str | None = Field(default=None, description="Nuevo nombre. No puede repetirse. Si no se envía, no cambia.")


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


class AthleteBase(BaseModel):
    name: str = Field(description="Nombre completo del atleta.", examples=["Mateo Quispe Mamani"])
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
    belt_rank: str = Field(
        description="Cinturón o grado, en texto libre.", examples=["verde", "negro 1er dan"]
    )
    weight_kg: float = Field(description="Peso en kilogramos.", examples=[38.5])
    club_id: int = Field(description="Id del club al que pertenece. El club debe existir.")


class AthleteCreate(AthleteBase):
    pass


class AthleteUpdate(BaseModel):
    name: str | None = Field(default=None, description="Nuevo nombre. Si no se envía, no cambia.")
    ci: NormalizedCi = Field(
        default=None,
        description=(
            "Nuevo CI, con el mismo formato que al crear. Si no se envía, no cambia; `null` o texto vacío "
            "lo borra."
        ),
        json_schema_extra={"pattern": f"^{CI_REGEX}$"},
    )
    birth_date: datetime.date | None = Field(
        default=None, description="Nueva fecha de nacimiento (`YYYY-MM-DD`). Si no se envía, no cambia."
    )
    gender: Gender | None = Field(
        default=None,
        description="Nuevo género. Si no se envía, no cambia. Ver las reglas con inscripciones en la operación.",
    )
    belt_rank: str | None = Field(default=None, description="Nuevo cinturón o grado. Si no se envía, no cambia.")
    weight_kg: float | None = Field(
        default=None,
        description="Nuevo peso en kilogramos. Si no se envía, no cambia. Ver las reglas con inscripciones en la operación.",
    )
    club_id: int | None = Field(
        default=None, description="Id del nuevo club, que debe existir. Si no se envía, no cambia."
    )


class AthleteRead(AthleteBase):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Identificador del atleta.")
    club: ClubRead = Field(description="Club al que pertenece el atleta.")


class TournamentBase(BaseModel):
    name: str = Field(description="Nombre del torneo.", examples=["Copa Cochabamba"])
    date: datetime.date = Field(description="Fecha del torneo (`YYYY-MM-DD`).", examples=["2026-11-15"])
    location: str = Field(description="Lugar donde se realiza.", examples=["Cochabamba, Bolivia"])


class TournamentCreate(TournamentBase):
    pass


class TournamentUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, description="Nuevo nombre. Si no se envía, no cambia.")
    date: datetime.date | None = Field(default=None, description="Nueva fecha (`YYYY-MM-DD`). Si no se envía, no cambia.")
    location: str | None = Field(default=None, description="Nuevo lugar. Si no se envía, no cambia.")


class TournamentRead(TournamentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Identificador del torneo.")
    status: TournamentStatus = Field(description="Estado actual del torneo.")


class CategoryBase(BaseModel):
    tournament_id: int = Field(description="Id del torneo al que pertenece la categoría. El torneo debe existir.")
    discipline: Discipline = Field(
        default=Discipline.SPARRING,
        description="Modalidad. Hoy solo existe `sparring` (combate), que es el valor por defecto.",
    )
    gender: Gender = Field(description="Género de la categoría. Solo se inscriben atletas del mismo género.")
    age_label: str = Field(description="Nombre del rango de edad.", examples=["Cadete"])
    min_age: int = Field(description="Edad mínima, en años.", examples=[12])
    max_age: int | None = Field(
        default=None, description="Edad máxima, en años. Si es nulo, no hay tope.", examples=[14]
    )
    belt_group: BeltGroup = Field(description="Grupo de cinturón de la categoría.")
    weight_label: str = Field(
        description="Nombre del rango de peso, en texto libre. Es lo que se muestra al público.",
        examples=["Hasta 45kg"],
    )
    min_weight: float | None = Field(
        default=None,
        description="Peso mínimo en kg. Si se define, no se inscriben atletas más livianos.",
    )
    max_weight: float | None = Field(
        default=None,
        description="Peso máximo en kg. Si se define, no se inscriben atletas más pesados.",
        examples=[45],
    )
    rounds_to_win: int = Field(
        default=2,
        description="Rounds que hay que ganar para ganar un combate (2 equivale a un combate al mejor de 3).",
    )

    @model_validator(mode="after")
    def check_weight_range(self) -> "CategoryBase":
        if (
            self.min_weight is not None
            and self.max_weight is not None
            and self.min_weight > self.max_weight
        ):
            raise ValueError("min_weight no puede ser mayor que max_weight")
        return self

    @model_validator(mode="after")
    def check_age_range(self) -> "CategoryBase":
        if self.max_age is not None and self.min_age > self.max_age:
            raise ValueError("min_age no puede ser mayor que max_age")
        return self


class CategoryCreate(CategoryBase):
    pass


class CategoryRead(CategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Identificador de la categoría.")


class RoundScoreCreate(BaseModel):
    red_points: int = Field(description="Puntos del lado rojo en este round.", examples=[12])
    blue_points: int = Field(description="Puntos del lado azul en este round.", examples=[5])


class RoundScoreRead(RoundScoreCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Identificador del resultado del round.")
    match_id: int = Field(description="Id del combate al que pertenece el round.")
    round_number: int = Field(
        description="Número del round dentro del combate, desde 1. Lo asigna el servidor en el orden en que se cargan.",
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
    athlete_id: int = Field(description="Id del atleta que se inscribe. El atleta debe existir.")
    category_id: int = Field(description="Id de la categoría en la que se inscribe. La categoría debe existir.")


class RegistrationCreate(RegistrationBase):
    pass


class RegistrationRead(RegistrationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int = Field(description="Identificador de la inscripción.")
    athlete: AthleteRead = Field(description="Datos del atleta inscrito.")
    category: CategoryRead = Field(description="Datos de la categoría.")
