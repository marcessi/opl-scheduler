"""CRUD para Operario_Articulo (tiempos por artículo)."""

from typing import List, Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from src.database.schema import Operario_Articulo


def leer(session: Session, ref_articulo: str, dni_operario: str) -> Optional[Operario_Articulo]:
    return session.scalars(
        select(Operario_Articulo).where(
            Operario_Articulo.ref_articulo == ref_articulo,
            Operario_Articulo.dni_operario == dni_operario,
        )
    ).first()


def listar_por_operario(session: Session, dni_operario: str) -> List[Operario_Articulo]:
    return list(session.scalars(
        select(Operario_Articulo).where(Operario_Articulo.dni_operario == dni_operario)
    ).all())


def listar_bulk(
    session: Session,
    dnis: List[str],
    refs_articulos: Optional[List[str]] = None,
) -> List[Operario_Articulo]:
    stmt = select(Operario_Articulo).where(Operario_Articulo.dni_operario.in_(dnis))
    if refs_articulos is not None:
        stmt = stmt.where(Operario_Articulo.ref_articulo.in_(refs_articulos))
    return list(session.scalars(stmt).all())


def contar(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(Operario_Articulo))
