"""Traducción al español de los enums del dominio, para mostrarlos al usuario.

Los enums de `app/models.py` se guardan en inglés a propósito -- son identificadores
internos, no texto para mostrar. Este módulo es el único lugar donde se traducen. Las
plantillas nunca deben usar `.value` directo (ver CLAUDE.md) -- siempre `|es_label`.
"""

from app.models import BeltGroup, Discipline, Gender, MatchStatus, TournamentStatus

_LABELS: dict[type, dict] = {
    TournamentStatus: {
        TournamentStatus.DRAFT: "Borrador",
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

_MATCH_STATUS_BADGE = {
    MatchStatus.PENDING: "bg-warning text-dark",
    MatchStatus.BYE: "bg-secondary",
    MatchStatus.FINISHED: "bg-success",
}


def es_label(value) -> str:
    return _LABELS.get(type(value), {}).get(value, str(value))


def match_status_badge_class(status: MatchStatus) -> str:
    return _MATCH_STATUS_BADGE.get(status, "bg-light text-dark")
