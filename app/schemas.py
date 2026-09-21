import datetime

from pydantic import BaseModel, ConfigDict, model_validator

from app.models import BeltGroup, Discipline, Gender, MatchStatus, TournamentStatus


class ClubBase(BaseModel):
    name: str


class ClubCreate(ClubBase):
    pass


class ClubRead(ClubBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


class AthleteBase(BaseModel):
    name: str
    birth_date: datetime.date
    gender: Gender
    belt_rank: str
    weight_kg: float
    club_id: int


class AthleteCreate(AthleteBase):
    pass


class AthleteRead(AthleteBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    club: ClubRead


class TournamentBase(BaseModel):
    name: str
    date: datetime.date
    location: str


class TournamentCreate(TournamentBase):
    pass


class TournamentUpdate(BaseModel):
    name: str | None = None
    date: datetime.date | None = None
    location: str | None = None
    status: TournamentStatus | None = None


class TournamentRead(TournamentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    status: TournamentStatus


class CategoryBase(BaseModel):
    tournament_id: int
    discipline: Discipline = Discipline.SPARRING
    gender: Gender
    age_label: str
    min_age: int
    max_age: int | None = None
    belt_group: BeltGroup
    weight_label: str
    min_weight: float | None = None
    max_weight: float | None = None
    rounds_to_win: int = 2

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

    id: int


class MatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    round_number: int
    slot: int
    athlete_red_id: int | None
    athlete_blue_id: int | None
    winner_id: int | None
    next_match_id: int | None
    status: MatchStatus


class BracketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: int
    size: int
    generated_at: datetime.datetime
    matches: list[MatchRead]


class RegistrationBase(BaseModel):
    athlete_id: int
    category_id: int


class RegistrationCreate(RegistrationBase):
    pass


class RegistrationRead(RegistrationBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    athlete: AthleteRead
    category: CategoryRead
