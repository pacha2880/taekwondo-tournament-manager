from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware

from app.api import athletes, auth, brackets, categories, clubs, matches, registrations, tournaments
from app.api_docs import API_DESCRIPTION, TAG_SYSTEM, TAGS_METADATA
from app.config import check_production_settings, cors_origins, secret_key, warn_if_short_secret_key
from app.cors import add_cors
from app.version import __version__
from app.web import admin, public
from app.web.admin import NotAuthenticated

check_production_settings()
warn_if_short_secret_key()

app = FastAPI(
    title="Torneos de Taekwondo API",
    version=__version__,
    description=API_DESCRIPTION,
    openapi_tags=TAGS_METADATA,
    generate_unique_id_function=lambda route: route.name,
)
app.add_middleware(SessionMiddleware, secret_key=secret_key())
add_cors(app, cors_origins())

app.include_router(auth.router)
app.include_router(clubs.router)
app.include_router(athletes.router)
app.include_router(tournaments.router)
app.include_router(categories.router)
app.include_router(registrations.router)
app.include_router(brackets.router)
app.include_router(matches.router)
app.include_router(public.router, include_in_schema=False)
app.include_router(admin.router, include_in_schema=False)


@app.exception_handler(NotAuthenticated)
def redirect_to_login(request: Request, exc: NotAuthenticated):
    return RedirectResponse(url="/admin/login", status_code=303)


@app.get(
    "/health",
    tags=[TAG_SYSTEM],
    summary="Estado del servicio",
    description="Responde `ok` y la versión desplegada. Sirve para comprobar que un deploy terminó.",
)
def health_check():
    return {"status": "ok", "version": __version__}
