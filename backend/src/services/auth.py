"""Servicio de autenticación: hash de contraseñas y generación/verificación de JWT."""

from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from src.config import JWT_SECRET_KEY, JWT_ALGORITHM, JWT_EXPIRE_MINUTES
from src.crud.auth import leer_por_username
from src.database.schema import Usuario
from src.exceptions import AuthenticationError


def hash_password(plain: str) -> str:
    """Genera el hash bcrypt de una contraseña en claro.

    Args:
        plain: Contraseña en texto plano.

    Returns:
        Hash bcrypt (con salt incorporado) listo para almacenar.
    """
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    """Comprueba si una contraseña en claro coincide con su hash bcrypt.

    Args:
        plain: Contraseña en texto plano a verificar.
        hashed: Hash bcrypt almacenado.

    Returns:
        ``True`` si la contraseña coincide, ``False`` en caso contrario.
    """
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def authenticate_user(session: Session, username: str, password: str) -> Usuario:
    """Verifica credenciales y devuelve el usuario. Lanza AuthenticationError si son incorrectas."""
    user = leer_por_username(session, username)
    if not user or not verify_password(password, user.hashed_password):
        raise AuthenticationError("Usuario o contraseña incorrectos")
    return user


def create_access_token(username: str) -> str:
    """Crea un JWT firmado para un usuario con expiración configurada.

    Args:
        username: Nombre de usuario que se guarda en el claim ``sub``.

    Returns:
        El token JWT codificado.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {"sub": username, "exp": expire}
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[str]:
    """Devuelve el username del token o None si es inválido/expirado."""
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None
