from fastapi import HTTPException, Request
from pydantic import ValidationError


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


def echo_form(**values) -> dict:
    """Valores enviados, para volver a mostrarlos en el formulario si falla (None se muestra vacío)."""
    return {name: "" if value is None else value for name, value in values.items()}
