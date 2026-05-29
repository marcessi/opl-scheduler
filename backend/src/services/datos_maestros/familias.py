"""Servicio de Familia (lecturas puras → delega a crud).

La lógica vive en :mod:`src.crud.datos_maestros.familias`.
"""

from typing import List
from sqlalchemy.orm import Session
from src.database.schema import Familia
from src.crud.datos_maestros import familias as _crud


def leer_todas_familias(session: Session) -> List[Familia]:
    return _crud.listar(session)


def contar_familias(session: Session) -> int:
    return _crud.contar(session)
