"""Servicio de Operario_Familia (lecturas puras → delega a crud)."""

from typing import List, Optional
from sqlalchemy.orm import Session
from src.database.schema import Operario_Familia
from src.crud.datos_maestros import operario_familia as _crud


def leer_familias_de_operario(session: Session, dni_operario: str) -> List[Operario_Familia]:
    return _crud.listar_por_operario(session, dni_operario)


def leer_operario_familia_bulk(
    session: Session,
    dnis: List[str],
    familias: Optional[List[str]] = None,
) -> List[Operario_Familia]:
    return _crud.listar_bulk(session, dnis, familias)


def contar_operario_familia(session: Session) -> int:
    return _crud.contar(session)
