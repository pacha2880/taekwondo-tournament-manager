from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.lifecycle import require_tournament_status
from app.api.tournaments import get_tournament_or_404
from app.api_docs import TAG_CATEGORIES, errors
from app.auth import ADMIN_ONLY
from app.database import get_db
from app.models import Tournament, TournamentStatus
from app.schemas import CategoryStructureRead, CategoryStructureResult, CategoryStructureUpdate
from app.services.category_structure import apply_structure, describe_structure, preview_categories

router = APIRouter(prefix="/api/v1/tournaments", tags=[TAG_CATEGORIES])


def _get_tournament_with_structure(db: Session, tournament_id: int) -> Tournament:
    tournament = get_tournament_or_404(db, tournament_id)
    if not tournament.grade_groups:
        raise HTTPException(status_code=404, detail="Este torneo no tiene estructura de categorías")
    return tournament


@router.get(
    "/{tournament_id}/category-structure",
    response_model=CategoryStructureRead,
    summary="Obtener la estructura de categorías de un torneo",
    description=(
        "Devuelve los grupos de grado, las divisiones de edad y las divisiones de peso del torneo. Sus categorías "
        "(`GET /categories?tournament_id=`) son todas las combinaciones de grupo, género, edad y peso; Festival (la "
        "primera división de edad, fija) es una sola categoría por género. Los torneos creados antes de la 0.8.0 no "
        "tienen estructura: sus categorías se cargaron a mano y responde 404. Es público."
    ),
    responses=errors({404: "El torneo no existe, o no tiene estructura de categorías."}),
)
def get_category_structure(tournament_id: int, db: Session = Depends(get_db)):
    return describe_structure(_get_tournament_with_structure(db, tournament_id))


@router.put(
    "/{tournament_id}/category-structure",
    response_model=CategoryStructureResult,
    dependencies=ADMIN_ONLY,
    summary="Reemplazar la estructura de categorías de un torneo",
    description=(
        "Reemplaza de una vez los grupos de grado y las divisiones de edad y peso (Festival es fijo y no se envía), y "
        "recalcula las categorías: las que siguen correspondiendo conservan su id, y las demás se crean o se borran. "
        "Solo con el torneo en `draft`. Responde 422 si la estructura no es válida, sin cambiar nada: el primer grupo "
        "empieza en `kup_10`, cada grupo y cada edad empieza después del anterior, el último grupo no se puede quitar "
        "(sigue último, con su id), la primera edad empieza en 10, los nombres no se repiten y los pesos van de menor a "
        "mayor. Con `validate_only=true` solo valida y devuelve cómo quedaría, sin guardar (los ids de lo nuevo no son "
        "definitivos). Requiere token."
    ),
    responses=errors(
        {404: "El torneo no existe, o no tiene estructura de categorías.", 409: "El torneo ya empezó."}, auth=True
    ),
)
def update_category_structure(
    tournament_id: int,
    payload: CategoryStructureUpdate,
    validate_only: bool = Query(default=False, description="Si es `true`, valida y devuelve el resultado sin guardarlo."),
    db: Session = Depends(get_db),
):
    tournament = _get_tournament_with_structure(db, tournament_id)
    require_tournament_status(
        tournament, TournamentStatus.DRAFT, "La estructura de categorías solo se cambia antes de iniciar el torneo"
    )
    apply_structure(db, tournament, payload)
    result = {**describe_structure(tournament), "categories": preview_categories(tournament)}
    if validate_only:
        db.rollback()
    else:
        db.commit()
    return result
