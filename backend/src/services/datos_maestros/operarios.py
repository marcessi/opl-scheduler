"""Servicio de Operario (lecturas puras → delega a crud)."""

from typing import List
from sqlalchemy.orm import Session
from src.database.schema import Operario
from src.crud.datos_maestros import operarios as _crud


def leer_todos_operarios(session: Session) -> List[Operario]:
    """Lista todos los operarios.

    Args:
        session: Sesión de base de datos activa.

    Returns:
        Lista con todos los operarios.
    """
    return _crud.listar(session)


def contar_operarios(session: Session) -> int:
    """Cuenta el total de operarios.

    Args:
        session: Sesión de base de datos activa.

    Returns:
        Número de operarios registrados.
    """
    return _crud.contar(session)
