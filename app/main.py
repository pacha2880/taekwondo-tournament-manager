from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.api import athletes, auth, brackets, categories, category_structure, clubs, matches, registrations, tournaments
from app.api_docs import API_DESCRIPTION, TAG_SYSTEM, TAGS_METADATA
from app.config import check_production_settings, cors_origins
from app.cors import add_cors
from app.errors import add_error_handlers
from app.version import __version__

check_production_settings()

app = FastAPI(
    title="Torneos de Taekwondo API",
    version=__version__,
    description=API_DESCRIPTION,
    openapi_tags=TAGS_METADATA,
    generate_unique_id_function=lambda route: route.name,
)
add_cors(app, cors_origins())
add_error_handlers(app)

app.include_router(auth.router)
app.include_router(clubs.router)
app.include_router(athletes.router)
app.include_router(tournaments.router)
app.include_router(categories.router)
app.include_router(category_structure.router)
app.include_router(registrations.router)
app.include_router(brackets.router)
app.include_router(matches.router)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")


@app.get(
    "/health",
    tags=[TAG_SYSTEM],
    summary="Estado del servicio",
    description="Responde `ok` y la versión desplegada. Sirve para comprobar que un deploy terminó.",
)
def health_check():
    return {"status": "ok", "version": __version__}
