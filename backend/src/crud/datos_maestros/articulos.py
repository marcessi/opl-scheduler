"""CRUD para Articulo."""

from typing import List, Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session, joinedload
from src.database.schema import Articulo


def leer(session: Session, referencia: str) -> Optional[Articulo]:
    """Lee un artículo por su referencia.

    Args:
        session: Sesión de base de datos activa.
        referencia: Referencia del artículo.

    Returns:
        El ``Articulo`` encontrado, o ``None`` si no existe.
    """
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
    """Lista los artículos de una familia.

    Args:
        session: Sesión de base de datos activa.
        familia: Descripción de la familia.

    Returns:
        Lista de artículos pertenecientes a esa familia.
    """
    return list(session.scalars(select(Articulo).where(Articulo.familia == familia)).all())


def contar(session: Session) -> int:
    """Cuenta el total de artículos.

    Args:
        session: Sesión de base de datos activa.

    Returns:
        Número de artículos registrados.
    """
    return session.scalar(select(func.count()).select_from(Articulo))
