import secrets
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer

from app.config import admin_credentials, secret_key

ALGORITHM = "HS256"
TOKEN_TTL = timedelta(hours=8)
# Los relojes de dos instancias (o un reloj que se resincroniza) pueden diferir unos segundos; sin
# margen, un token recién emitido se rechaza como "aún no válido" (iat en el futuro).
CLOCK_SKEW_LEEWAY = timedelta(seconds=30)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def verify_admin_credentials(username: str, password: str) -> bool:
    expected_username, expected_password = admin_credentials()
    username_ok = secrets.compare_digest(username.encode(), expected_username.encode())
    password_ok = secrets.compare_digest(password.encode(), expected_password.encode())
    return username_ok and password_ok


def create_access_token(username: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": username, "iat": now, "exp": now + TOKEN_TTL}
    return jwt.encode(payload, secret_key(), algorithm=ALGORITHM)


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=401, detail=detail, headers={"WWW-Authenticate": "Bearer"})


def require_api_admin(token: str | None = Depends(oauth2_scheme)) -> str:
    if token is None:
        raise _unauthorized("No autenticado: falta el token de acceso")
    try:
        payload = jwt.decode(
            token,
            secret_key(),
            algorithms=[ALGORITHM],
            options={"require": ["exp", "sub"]},
            leeway=CLOCK_SKEW_LEEWAY,
        )
    except jwt.ExpiredSignatureError:
        raise _unauthorized("El token venció; inicia sesión de nuevo") from None
    except jwt.InvalidTokenError:
        raise _unauthorized("Token inválido") from None
    if payload["sub"] != admin_credentials()[0]:
        raise _unauthorized("Token inválido")
    return payload["sub"]


ADMIN_ONLY = [Depends(require_api_admin)]
