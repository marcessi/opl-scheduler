"""CRUD para Familia."""

from typing import List, Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from src.database.schema import Familia


def listar(session: Session) -> List[Familia]:
    """Lista todas las familias.

    Args:
        session: Sesión de base de datos activa.

    Returns:
        Lista con todas las familias de la base de datos.
    """
    return list(session.scalars(select(Familia)).all())


def leer(session: Session, descripcion: str) -> Optional[Familia]:
    """Lee una familia por su descripción (clave primaria).

    Args:
        session: Sesión de base de datos activa.
        descripcion: Descripción de la familia.

    Returns:
        La ``Familia`` encontrada, o ``None`` si no existe.
    """
    return session.scalars(select(Familia).where(Familia.descripcion == descripcion)).first()


def contar(session: Session) -> int:
    """Cuenta el total de familias.

    Args:
        session: Sesión de base de datos activa.

    Returns:
        Número de familias registradas.
    """
    return session.scalar(select(func.count()).select_from(Familia))
