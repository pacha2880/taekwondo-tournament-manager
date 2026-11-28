import enum
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app import clock
from app.database import Base


class TournamentStatus(str, enum.Enum):
    """Estado del torneo. El ciclo avanza en un solo sentido, sin volver atrás: `draft` (en preparación: se edita la
    estructura de categorías y la fecha límite de inscripción), `registration_open` (inscripciones abiertas hasta la
    fecha límite), `weigh_in` (pesaje: las inscripciones ya cerraron; se llega al vencer la fecha límite o con
    `close-registration`), `in_progress` (en curso: se generan las llaves y se cargan resultados) y `finished`
    (finalizado)."""

    DRAFT = "draft"
    REGISTRATION_OPEN = "registration_open"
    WEIGH_IN = "weigh_in"
    IN_PROGRESS = "in_progress"
    FINISHED = "finished"


# Solo SPARRING está implementado; FORMS/BREAKING se agregarían acá con su propio modelo de resultado
# (ver docs/DECISIONS.md). La docstring de abajo es la que ve quien lee /docs.
class Discipline(str, enum.Enum):
    """Modalidad de la categoría. Hoy solo existe `sparring` (combate)."""

    SPARRING = "sparring"


class Gender(str, enum.Enum):
    """Género: `male` (masculino) o `female` (femenino)."""

    MALE = "male"
    FEMALE = "female"


class Grade(str, enum.Enum):
    """Grado del atleta, de menor a mayor: `kup_10` (10mo Kup, cinturón blanco) … `kup_1` (1er Kup, negro-rojo) y
    `dan` (cinturón negro)."""

    KUP_10 = "kup_10"
    KUP_9 = "kup_9"
    KUP_8 = "kup_8"
    KUP_7 = "kup_7"
    KUP_6 = "kup_6"
    KUP_5 = "kup_5"
    KUP_4 = "kup_4"
    KUP_3 = "kup_3"
    KUP_2 = "kup_2"
    KUP_1 = "kup_1"
    DAN = "dan"


class MatchStatus(str, enum.Enum):
    """Estado del combate: `pending` (pendiente: por jugar o esperando a sus atletas), `bye` (pase directo:
    el atleta avanza sin pelear), `finished` (terminado: ya tiene ganador), `walkover` (ganado sin pelear: un lado
    quedó descalificado, o su rival vino de un combate sin ganador; gana el otro y avanza) y `no_contest` (sin
    combate: los dos lados quedaron descalificados o sin atleta; no hay ganador y nadie avanza)."""

    PENDING = "pending"
    BYE = "bye"
    FINISHED = "finished"
    WALKOVER = "walkover"
    NO_CONTEST = "no_contest"


# Combates que ya no cambian: los que no se pelean y los jugados.
FINAL_MATCH_STATUSES = (MatchStatus.BYE, MatchStatus.FINISHED, MatchStatus.WALKOVER, MatchStatus.NO_CONTEST)


class WeighInStatus(str, enum.Enum):
    """Estado del pesaje de una inscripción: `pending` (sin pesar), `failed_first` (no entró en el peso de su categoría
    en el primer pesaje; espera la decisión del admin), `second_allowed` (segundo pesaje habilitado), `cleared`
    (habilitado para competir), `disqualified` (descalificado por peso), `no_show` (no se presentó al pesaje) y
    `not_required` (Festival: no se pesa)."""

    PENDING = "pending"
    FAILED_FIRST = "failed_first"
    SECOND_ALLOWED = "second_allowed"
    CLEARED = "cleared"
    DISQUALIFIED = "disqualified"
    NO_SHOW = "no_show"
    NOT_REQUIRED = "not_required"


def current_status(
    stored_status: TournamentStatus, registration_deadline: datetime | None, now: datetime
) -> TournamentStatus:
    """El pesaje no se guarda: empieza solo cuando vence la fecha límite (UTC sin zona; `now`, con zona UTC)."""
    deadline_passed = registration_deadline is not None and now.replace(tzinfo=None) >= registration_deadline
    if stored_status == TournamentStatus.REGISTRATION_OPEN and deadline_passed:
        return TournamentStatus.WEIGH_IN
    return stored_status


class Club(Base):
    __tablename__ = "clubs"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)

    athletes: Mapped[list["Athlete"]] = relationship(back_populates="club")


class Athlete(Base):
    __tablename__ = "athletes"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    ci: Mapped[str | None] = mapped_column(String(12), unique=True, index=True)
    birth_date: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[Gender] = mapped_column(Enum(Gender), nullable=False)
    grade: Mapped[Grade] = mapped_column(Enum(Grade), nullable=False)
    weight_kg: Mapped[float] = mapped_column(Float, nullable=False)
    height_cm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    club_id: Mapped[int] = mapped_column(ForeignKey("clubs.id"), nullable=False)

    club: Mapped["Club"] = relationship(back_populates="athletes")
    registrations: Mapped[list["Registration"]] = relationship(back_populates="athlete")


class Tournament(Base):
    __tablename__ = "tournaments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    location: Mapped[str] = mapped_column(String(150), nullable=False)
    # `weigh_in` nunca se guarda: se calcula al leer (ver `current_status`). La fecha límite va en UTC, sin zona.
    stored_status: Mapped[TournamentStatus] = mapped_column(
        "status", Enum(TournamentStatus), nullable=False, default=TournamentStatus.DRAFT
    )
    registration_deadline: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    categories: Mapped[list["Category"]] = relationship(
        back_populates="tournament", cascade="all, delete-orphan"
    )
    grade_groups: Mapped[list["GradeGroup"]] = relationship(
        back_populates="tournament", cascade="all, delete-orphan", order_by="GradeGroup.position"
    )
    age_divisions: Mapped[list["AgeDivision"]] = relationship(
        back_populates="tournament", cascade="all, delete-orphan", order_by="AgeDivision.position"
    )

    @property
    def status(self) -> TournamentStatus:
        return current_status(self.stored_status, self.registration_deadline, clock.utc_now())


# Estructura de categorías de un torneo (ver docs/DECISIONS.md, 2026-11-16). Grupos de grado y divisiones de edad
# se guardan como cortes: cada uno dice desde dónde empieza y termina donde empieza el siguiente, así que no puede
# haber huecos ni solapes. Las categorías se derivan de la estructura: grupo × género × edad × división de peso.
class GradeGroup(Base):
    __tablename__ = "grade_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    from_grade: Mapped[Grade] = mapped_column(Enum(Grade), nullable=False)

    tournament: Mapped["Tournament"] = relationship(back_populates="grade_groups")


class AgeDivision(Base):
    __tablename__ = "age_divisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    tournament_id: Mapped[int] = mapped_column(ForeignKey("tournaments.id"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    from_age: Mapped[int] = mapped_column(Integer, nullable=False)

    tournament: Mapped["Tournament"] = relationship(back_populates="age_divisions")
    weight_limits: Mapped[list["WeightLimit"]] = relationship(
        back_populates="age_division", cascade="all, delete-orphan", order_by="WeightLimit.position"
    )


class WeightLimit(Base):
    """Límite superior de una división de peso: hasta X kg. La última división de cada edad y género es
    «más de» su último límite, así que N límites dan N + 1 divisiones."""

    __tablename__ = "weight_limits"

    id: Mapped[int] = mapped_column(primary_key=True)
    age_division_id: Mapped[int] = mapped_column(ForeignKey("age_divisions.id"), nullable=False)
    gender: Mapped[Gender] = mapped_column(Enum(Gender), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    upper_limit: Mapped[float] = mapped_column(Float, nullable=False)

    age_division: Mapped["AgeDivision"] = relationship(back_populates="weight_limits")


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
    weight_label: Mapped[str] = mapped_column(String(60), nullable=False)
    min_weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    rounds_to_win: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    # Festival no tiene grupo de grado ni posición de peso.
    grade_group_id: Mapped[int | None] = mapped_column(ForeignKey("grade_groups.id"), nullable=True)
    age_division_id: Mapped[int] = mapped_column(ForeignKey("age_divisions.id"), nullable=False)
    weight_position: Mapped[int | None] = mapped_column(Integer, nullable=True)

    tournament: Mapped["Tournament"] = relationship(back_populates="categories")
    grade_group: Mapped["GradeGroup | None"] = relationship()
    age_division: Mapped["AgeDivision"] = relationship()
    registrations: Mapped[list["Registration"]] = relationship(
        back_populates="category", cascade="all, delete-orphan"
    )
    bracket: Mapped["Bracket | None"] = relationship(
        back_populates="category", cascade="all, delete-orphan"
    )

    @property
    def has_bracket(self) -> bool:
        return self.bracket is not None

    @property
    def grade_group_name(self) -> str | None:
        return self.grade_group.name if self.grade_group else None

    @property
    def name(self) -> str:
        """Nombre completo para mostrar; sin el grupo, dos categorías que solo difieren en él se ven iguales."""
        gender = "Masculino" if self.gender == Gender.MALE else "Femenino"
        parts = [self.grade_group_name, self.age_label, gender, self.weight_label]
        return " · ".join(part for part in parts if part)


class Registration(Base):
    __tablename__ = "registrations"
    __table_args__ = (UniqueConstraint("athlete_id", "category_id", name="uq_athlete_category"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    athlete_id: Mapped[int] = mapped_column(ForeignKey("athletes.id"), nullable=False)
    category_id: Mapped[int] = mapped_column(ForeignKey("categories.id"), nullable=False)
    weigh_in_status: Mapped[WeighInStatus] = mapped_column(
        Enum(WeighInStatus), nullable=False, default=WeighInStatus.PENDING, server_default=WeighInStatus.PENDING.name
    )
    first_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)
    second_weight_kg: Mapped[float | None] = mapped_column(Float, nullable=True)

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
