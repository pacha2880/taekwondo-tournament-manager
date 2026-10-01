import os

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from app.api import athletes, brackets, categories, clubs, matches, registrations, tournaments
from app.web import admin, public
from app.web.admin import NotAuthenticated

app = FastAPI(title="Torneos de Taekwondo API")
app.add_middleware(SessionMiddleware, secret_key=os.environ.get("SECRET_KEY", "dev-secret-key"))

app.include_router(clubs.router)
app.include_router(athletes.router)
app.include_router(tournaments.router)
app.include_router(categories.router)
app.include_router(registrations.router)
app.include_router(brackets.router)
app.include_router(matches.router)
app.include_router(public.router)
app.include_router(admin.router)


@app.exception_handler(NotAuthenticated)
def redirect_to_login(request: Request, exc: NotAuthenticated):
    return RedirectResponse(url="/admin/login", status_code=303)


@app.get("/health")
def health_check():
    return {"status": "ok"}
