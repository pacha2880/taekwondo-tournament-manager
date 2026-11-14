"""Traducción al español de los enums del dominio, para mostrarlos al usuario.

Los enums de `app/models.py` se guardan en inglés a propósito -- son identificadores
internos, no texto para mostrar. Este módulo es el único lugar donde se traducen. Las
plantillas nunca deben usar `.value` directo (ver CLAUDE.md) -- siempre `|es_label`.
"""

from app.models import BeltGroup, Discipline, Gender, Grade, MatchStatus, TournamentStatus

_LABELS: dict[type, dict] = {
    TournamentStatus: {
        TournamentStatus.DRAFT: "Inscripciones abiertas",
        TournamentStatus.IN_PROGRESS: "En curso",
        TournamentStatus.FINISHED: "Finalizado",
    },
    Discipline: {
        Discipline.SPARRING: "Combate",
    },
    Gender: {
        Gender.MALE: "Masculino",
        Gender.FEMALE: "Femenino",
    },
    Grade: {
        Grade.KUP_10: "10mo Kup",
        Grade.KUP_9: "9no Kup",
        Grade.KUP_8: "8vo Kup",
        Grade.KUP_7: "7mo Kup",
        Grade.KUP_6: "6to Kup",
        Grade.KUP_5: "5to Kup",
        Grade.KUP_4: "4to Kup",
        Grade.KUP_3: "3er Kup",
        Grade.KUP_2: "2do Kup",
        Grade.KUP_1: "1er Kup",
        Grade.DAN: "Dan",
    },
    BeltGroup: {
        BeltGroup.COLOR: "Cinturón de color",
        BeltGroup.BLACK: "Cinturón negro",
    },
    MatchStatus: {
        MatchStatus.PENDING: "Pendiente",
        MatchStatus.BYE: "Pase directo",
        MatchStatus.FINISHED: "Finalizado",
    },
}

_TOURNAMENT_STATUS_BADGE = {
    TournamentStatus.DRAFT: "bg-secondary",
    TournamentStatus.IN_PROGRESS: "bg-primary",
    TournamentStatus.FINISHED: "bg-success",
}

_MATCH_STATUS_BADGE = {
    MatchStatus.PENDING: "bg-warning text-dark",
    MatchStatus.BYE: "bg-secondary",
    MatchStatus.FINISHED: "bg-success",
}


def es_label(value) -> str:
    return _LABELS.get(type(value), {}).get(value, str(value))


def tournament_status_badge_class(status: TournamentStatus) -> str:
    return _TOURNAMENT_STATUS_BADGE.get(status, "bg-light text-dark")


def match_status_badge_class(status: MatchStatus) -> str:
    return _MATCH_STATUS_BADGE.get(status, "bg-light text-dark")
