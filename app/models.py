import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class TournamentStatus(str, enum.Enum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"


class Discipline(str, enum.Enum):
    """Solo SPARRING está implementado. FORMS/BREAKING se agregarían aquí más
    adelante con su propio modelo de resultado — ver docs/DECISIONS.md."""

    SPARRING = "sparring"


class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"


class BeltGroup(str, enum.Enum):
    COLOR = "color"
    BLACK = "black"


class MatchStatus(str, enum.Enum):
    PENDING = "pending"
    BYE = "bye"
    FINISHED = "finished"


class Club(Base):
    __tablename__ = "clubs"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)

    athletes: Mapped[list["Athlete"]] = relationship(back_populates="club")


class Athlete(Base):
    __tablename__ = "athletes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[Gender] = mapped_column(Enum(Gender), nullable=False)
    belt_rank: Mapped[str] = mapped_column(String(60), nullable=False)
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id"), nullable=False)

    club: Mapped["Club"] = relationship(back_populates="athletes")
    registrations: Mapped[list["Registration"]] = relationship(back_populates="athlete")


class Tournament(Base):
    __tablename__ = "tournaments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    location: Mapped[str] = mapped_column(String(150), nullable=False)
    status: Mapped[TournamentStatus] = mapped_column(
        Enum(TournamentStatus), nullable=False, default=TournamentStatus.DRAFT
    )

    categories: Mapped[list["Category"]] = relationship(
        back_populates="tournament", cascade="all, delete-orphan"
    )


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"), nullable=False)
    discipline: Mapped[Discipline] = mapped_column(
        Enum(Discipline), nullable=False, default=Discipline.SPARRING
    )
    gender: Mapped[Gender] = mapped_column(Enum(Gender), nullable=False)
    age_label: Mapped[str] = mapped_column(String(60), nullable=False)
    min_age: Mapped[int] = mapped_column(Integer, nullable=False)
    max_age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    belt_group: Mapped[BeltGroup] = mapped_column(Enum(BeltGroup), nullable=False)
    weight_label: Mapped[str] = mapped_column(String(60), nullable=False)
    rounds_to_win: Mapped[int] = mapped_column(Integer, nullable=False, default=2)

    tournament: Mapped["Tournament"] = relationship(back_populates="categories")
    registrations: Mapped[list["Registration"]] = relationship(
        back_populates="category", cascade="all, delete-orphan"
    )
    bracket: Mapped["Bracket | None"] = relationship(
        back_populates="category", cascade="all, delete-orphan"
    )


class Registration(Base):
    __tablename__ = "registrations"
    __table_args__ = (UniqueConstraint("athlete_id", "category_id", name="uq_athlete_category"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    athlete_id: Mapped[int] = mapped_column(ForeignKey("athletes.id"), nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)

    athlete: Mapped["Athlete"] = relationship(back_populates="registrations")
    category: Mapped["Category"] = relationship(back_populates="registrations")


class Bracket(Base):
    __tablename__ = "brackets"

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id"), unique=True, nullable=False
    )
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    category: Mapped["Category"] = relationship(back_populates="bracket")
    matches: Mapped[list["Match"]] = relationship(
        back_populates="bracket", cascade="all, delete-orphan"
    )


class Match(Base):
    __tablename__ = "matches"
    __table_args__ = (UniqueConstraint("bracket_id", "round_number", "slot", name="uq_match_slot"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    bracket_id: Mapped[int] = mapped_column(ForeignKey("brackets.id"), nullable=False)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    slot: Mapped[int] = mapped_column(Integer, nullable=False)
    athlete_red_id: Mapped[int | None] = mapped_column(ForeignKey("athletes.id"), nullable=True)
    athlete_blue_id: Mapped[int | None] = mapped_column(ForeignKey("athletes.id"), nullable=True)
    winner_id: Mapped[int | None] = mapped_column(ForeignKey("athletes.id"), nullable=True)
    next_match_id: Mapped[int | None] = mapped_column(ForeignKey("matches.id"), nullable=True)
    status: Mapped[MatchStatus] = mapped_column(
        Enum(MatchStatus), nullable=False, default=MatchStatus.PENDING
    )

    bracket: Mapped["Bracket"] = relationship(back_populates="matches")
    round_scores: Mapped[list["RoundScore"]] = relationship(
        back_populates="match", cascade="all, delete-orphan"
    )


class RoundScore(Base):
    __tablename__ = "round_scores"
    __table_args__ = (UniqueConstraint("match_id", "round_number", name="uq_round_per_match"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), nullable=False)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    red_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    blue_points: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    round_winner_id: Mapped[int | None] = mapped_column(ForeignKey("athletes.id"), nullable=True)

    match: Mapped["Match"] = relationship(back_populates="round_scores")
