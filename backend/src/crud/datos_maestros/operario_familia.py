"""CRUD para Operario_Familia (experiencia por familia)."""

from typing import List, Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from src.database.schema import Operario_Familia


def listar_por_operario(session: Session, dni_operario: str) -> List[Operario_Familia]:
    return list(session.scalars(
        select(Operario_Familia).where(Operario_Familia.dni_operario == dni_operario)
    ).all())


def listar_bulk(
    session: Session,
    dnis: List[str],
    familias: Optional[List[str]] = None,
) -> List[Operario_Familia]:
    stmt = select(Operario_Familia).where(Operario_Familia.dni_operario.in_(dnis))
    if familias is not None:
        stmt = stmt.where(Operario_Familia.familia.in_(familias))
    return list(session.scalars(stmt).all())


def contar(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(Operario_Familia))
