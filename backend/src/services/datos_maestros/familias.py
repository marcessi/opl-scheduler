"""Servicio de Familia (lecturas puras → delega a crud).

La lógica vive en :mod:`src.crud.datos_maestros.familias`.
"""

from typing import List
from sqlalchemy.orm import Session
from src.database.schema import Familia
from src.crud.datos_maestros import familias as _crud


def leer_todas_familias(session: Session) -> List[Familia]:
    """Lista todas las familias.

    Args:
        session: Sesión de base de datos activa.

    Returns:
        Lista con todas las familias.
    """
    return _crud.listar(session)


def contar_familias(session: Session) -> int:
    """Cuenta el total de familias.

    Args:
        session: Sesión de base de datos activa.

    Returns:
        Número de familias registradas.
    """
    return _crud.contar(session)
