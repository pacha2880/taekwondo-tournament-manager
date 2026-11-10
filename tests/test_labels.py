import pytest

from app.models import TournamentStatus
from app.web.labels import es_label, tournament_status_badge_class


@pytest.mark.parametrize(
    "status,expected",
    [
        (TournamentStatus.DRAFT, "bg-secondary"),
        (TournamentStatus.IN_PROGRESS, "bg-primary"),
        (TournamentStatus.FINISHED, "bg-success"),
    ],
)
def test_tournament_status_badge_class(status, expected):
    assert tournament_status_badge_class(status) == expected


def test_every_tournament_status_has_its_own_badge_color():
    colors = {tournament_status_badge_class(status) for status in TournamentStatus}
    assert len(colors) == len(TournamentStatus)


def test_draft_tournament_is_shown_as_open_registrations():
    assert es_label(TournamentStatus.DRAFT) == "Inscripciones abiertas"
