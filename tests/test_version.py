import re
from pathlib import Path

from app.version import __version__

SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-((?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\.(?:0|[1-9]\d*|\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?"
    r"(?:\+([0-9a-zA-Z-]+(?:\.[0-9a-zA-Z-]+)*))?$"
)
CHANGELOG = Path(__file__).resolve().parent.parent / "CHANGELOG.md"


def test_version_is_valid_semver():
    assert SEMVER.match(__version__)


def test_changelog_latest_release_matches_version():
    releases = re.findall(r"^## \[(\d+\.\d+\.\d+[^\]]*)\]", CHANGELOG.read_text(), re.MULTILINE)
    assert releases, "CHANGELOG.md no tiene ninguna versión publicada"
    assert releases[0] == __version__


def test_health_reports_version(client):
    resp = client.get("/health")
    assert resp.json() == {"status": "ok", "version": __version__}


def test_root_redirects_to_the_api_docs(client):
    resp = client.get("/", follow_redirects=False)

    assert resp.status_code == 307
    assert resp.headers["location"] == "/docs"
