import datetime

from pydantic import BaseModel, ConfigDict

from app.models import BeltGroup, Discipline, Gender, TournamentStatus


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
    rounds_to_win: int = 2


class CategoryCreate(CategoryBase):
    pass


class CategoryRead(CategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int


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
