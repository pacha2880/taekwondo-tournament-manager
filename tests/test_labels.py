import pytest

from app.models import TournamentStatus
from app.web.labels import tournament_status_badge_class


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
