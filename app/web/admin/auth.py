from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse

from app.auth import verify_admin_credentials
from app.web.templating import templates

router = APIRouter()


@router.get("/login")
def login_form(request: Request):
    return templates.TemplateResponse(request, "admin/login.html", {"error": None})


@router.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    if not verify_admin_credentials(username, password):
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
