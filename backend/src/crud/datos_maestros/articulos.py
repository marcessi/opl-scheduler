"""CRUD para Articulo."""

from typing import List, Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session, joinedload
from src.database.schema import Articulo


def leer(session: Session, referencia: str) -> Optional[Articulo]:
    return session.scalars(select(Articulo).where(Articulo.referencia == referencia)).first()


def leer_bulk(session: Session, refs: list[str]) -> List[Articulo]:
    """Lectura por lote con familia precargada en una sola query."""
    stmt = (
        select(Articulo)
        .where(Articulo.referencia.in_(refs))
        .options(joinedload(Articulo.familia_obj))
    )
    return list(session.scalars(stmt).unique().all())


def listar_por_familia(session: Session, familia: str) -> List[Articulo]:
    return list(session.scalars(select(Articulo).where(Articulo.familia == familia)).all())


def contar(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(Articulo))
