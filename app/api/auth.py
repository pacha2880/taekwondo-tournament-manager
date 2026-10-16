from fastapi import APIRouter, Form, HTTPException

from app.api_docs import TAG_AUTH, errors
from app.auth import TOKEN_TTL, create_access_token, verify_admin_credentials
from app.schemas import TokenResponse

router = APIRouter(prefix="/api/v1/auth", tags=[TAG_AUTH])


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Iniciar sesión",
    description="Recibe `username` y `password` como formulario (`application/x-www-form-urlencoded`) y devuelve un token JWT que dura 8 horas. Se envía luego como `Authorization: Bearer <token>`.",
    responses=errors({401: "Usuario o contraseña incorrectos."}),
)
def login(
    username: str = Form(description="Usuario del administrador."),
    password: str = Form(description="Contraseña del administrador."),
):
    if not verify_admin_credentials(username, password):
        raise HTTPException(
            status_code=401,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(
        access_token=create_access_token(username),
        expires_in=int(TOKEN_TTL.total_seconds()),
    )
