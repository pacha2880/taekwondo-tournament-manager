from fastapi import FastAPI

from app.api import athletes, categories, clubs, registrations, tournaments

app = FastAPI(title="Torneos de Taekwondo API")

app.include_router(clubs.router)
app.include_router(athletes.router)
app.include_router(tournaments.router)
app.include_router(categories.router)
app.include_router(registrations.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}
