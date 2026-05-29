"""Servicio de Operario (lecturas puras → delega a crud)."""

from typing import List
from sqlalchemy.orm import Session
from src.database.schema import Operario
from src.crud.datos_maestros import operarios as _crud


def leer_todos_operarios(session: Session) -> List[Operario]:
    return _crud.listar(session)


def contar_operarios(session: Session) -> int:
    return _crud.contar(session)
