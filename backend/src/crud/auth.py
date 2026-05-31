"""CRUD para Usuario."""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.database.schema import Usuario


def leer_por_username(session: Session, username: str) -> Optional[Usuario]:
    """Lee un usuario por su nombre de acceso.

    Args:
        session: Sesión de base de datos activa.
        username: Nombre de usuario.

    Returns:
        El ``Usuario`` correspondiente, o ``None`` si no existe.
    """
    return session.scalars(select(Usuario).where(Usuario.username == username)).first()
