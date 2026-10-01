import os

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from app.web.admin._shared import templates

router = APIRouter()

ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin")


@router.get("/login")
def login_form(request: Request):
    return templates.TemplateResponse(request, "admin/login.html", {"error": None})


@router.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if username != ADMIN_USERNAME or password != ADMIN_PASSWORD:
        return templates.TemplateResponse(
            request,
            "admin/login.html",
            {"error": "Usuario o contraseña incorrectos"},
            status_code=401,
        )
    request.session["is_admin"] = True
    return RedirectResponse(url="/admin", status_code=303)


@router.post("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/admin/login", status_code=303)
