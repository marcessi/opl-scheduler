"""CRUD para Operario."""

from typing import List, Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from src.database.schema import Operario


def listar(session: Session) -> List[Operario]:
    """Lista todos los operarios.

    Args:
        session: Sesión de base de datos activa.

    Returns:
        Lista con todos los operarios de la base de datos.
    """
    return list(session.scalars(select(Operario)).all())


def leer(session: Session, dni: str) -> Optional[Operario]:
    """Lee un operario por su DNI.

    Args:
        session: Sesión de base de datos activa.
        dni: DNI del operario.

    Returns:
        El ``Operario`` encontrado, o ``None`` si no existe.
    """
    return session.scalars(select(Operario).where(Operario.dni == dni)).first()


def contar(session: Session) -> int:
    """Cuenta el total de operarios.

    Args:
        session: Sesión de base de datos activa.

    Returns:
        Número de operarios registrados.
    """
    return session.scalar(select(func.count()).select_from(Operario))
