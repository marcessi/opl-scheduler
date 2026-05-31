"""Endpoints de autenticación: login y perfil del usuario actual."""

from fastapi import APIRouter, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from src.database import get_session
from src.exceptions import AuthenticationError
from src.services.auth import authenticate_user, create_access_token, decode_access_token

router = APIRouter(prefix="/auth", tags=["auth"])
_bearer = HTTPBearer()


# ── Schemas Pydantic ───────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    """Cuerpo de la petición de login con las credenciales del usuario."""

    username: str
    password: str


class TokenResponse(BaseModel):
    """Respuesta del login con el JWT emitido y su tipo (siempre ``bearer``)."""

    access_token: str
    token_type: str = "bearer"


# ── Dependencia reutilizable ───────────────────────────────────────────────

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(_bearer)) -> str:
    """Valida el Bearer token y devuelve el username. Lanza AuthenticationError si es inválido."""
    username = decode_access_token(credentials.credentials)
    if not username:
        raise AuthenticationError("Token inválido o expirado")
    return username


# ── Endpoints ──────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    """Autentica al usuario y devuelve un JWT.

    Args:
        body: Credenciales (usuario y contraseña).

    Returns:
        ``TokenResponse`` con el access token.

    Raises:
        AuthenticationError: si las credenciales son incorrectas (→ 401).
    """
    with get_session() as session:
        user = authenticate_user(session, body.username, body.password)
    return TokenResponse(access_token=create_access_token(user.username))


@router.get("/me")
def me(username: str = Depends(get_current_user)):
    """Devuelve el usuario asociado al token de la petición.

    Args:
        username: Usuario extraído del Bearer token por la dependencia.

    Returns:
        ``{"username": <usuario>}``.
    """
    return {"username": username}
