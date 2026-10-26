import re
from pathlib import Path

ADMIN_TEMPLATES = Path(__file__).parent.parent / "app" / "templates" / "admin"
FORMS_WITHOUT_CONFIRMATION = ("/admin/login",)


def test_every_post_form_in_the_admin_asks_for_confirmation():
    missing = []
    for template in sorted(ADMIN_TEMPLATES.glob("*.html")):
        for tag in re.findall(r'<form method="post"[^>]*>', template.read_text()):
            if "data-confirm" not in tag and not any(action in tag for action in FORMS_WITHOUT_CONFIRMATION):
                missing.append(f"{template.name}: {tag}")

    assert missing == [], "los formularios POST del admin deben llevar data-confirm"
