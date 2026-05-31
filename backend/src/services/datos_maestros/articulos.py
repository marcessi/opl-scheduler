"""Servicio de Articulo (lecturas puras → delega a crud)."""

from typing import List, Optional
from sqlalchemy.orm import Session
from src.database.schema import Articulo
from src.crud.datos_maestros import articulos as _crud


def leer_articulo(session: Session, referencia: str) -> Optional[Articulo]:
    """Lee un artículo por su referencia.

    Args:
        session: Sesión de base de datos activa.
        referencia: Referencia del artículo.

    Returns:
        El ``Articulo`` encontrado, o ``None`` si no existe.
    """
    return _crud.leer(session, referencia)


def leer_articulos_bulk(session: Session, refs: list[str]) -> List[Articulo]:
    """Lee varios artículos en una sola query.

    Args:
        session: Sesión de base de datos activa.
        refs: Lista de referencias de artículo.

    Returns:
        Lista de los artículos existentes entre las referencias dadas.
    """
    return _crud.leer_bulk(session, refs)


def leer_articulos_por_familia(session: Session, familia: str) -> List[Articulo]:
    """Lista los artículos de una familia.

    Args:
        session: Sesión de base de datos activa.
        familia: Descripción de la familia.

    Returns:
        Lista de artículos pertenecientes a esa familia.
    """
    return _crud.listar_por_familia(session, familia)


def contar_articulos(session: Session) -> int:
    """Cuenta el total de artículos.

    Args:
        session: Sesión de base de datos activa.

    Returns:
        Número de artículos registrados.
    """
    return _crud.contar(session)
