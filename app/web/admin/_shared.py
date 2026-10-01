from fastapi import HTTPException, Request
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from app.web.labels import es_label, match_status_badge_class

templates = Jinja2Templates(directory="app/templates")
templates.env.filters["es_label"] = es_label
templates.env.filters["match_status_badge_class"] = match_status_badge_class


class NotAuthenticated(Exception):
    pass


def require_admin(request: Request) -> None:
    if not request.session.get("is_admin"):
        raise NotAuthenticated()


def error_message(exc: Exception) -> str:
    if isinstance(exc, HTTPException):
        return exc.detail
    if isinstance(exc, ValidationError):
        return "; ".join(
            f"{e['loc'][-1]}: {e['msg']}" if e["loc"] else e["msg"] for e in exc.errors()
        )
    return str(exc)
