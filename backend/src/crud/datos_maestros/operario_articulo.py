"""CRUD para Operario_Articulo (tiempos por artículo)."""

from typing import List, Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from src.database.schema import Operario_Articulo


def leer(session: Session, ref_articulo: str, dni_operario: str) -> Optional[Operario_Articulo]:
    """Lee la relación operario-artículo (tiempo específico) por su clave compuesta.

    Args:
        session: Sesión de base de datos activa.
        ref_articulo: Referencia del artículo.
        dni_operario: DNI del operario.

    Returns:
        El ``Operario_Articulo`` correspondiente, o ``None`` si no existe.
    """
    return session.scalars(
        select(Operario_Articulo).where(
            Operario_Articulo.ref_articulo == ref_articulo,
            Operario_Articulo.dni_operario == dni_operario,
        )
    ).first()


def listar_por_operario(session: Session, dni_operario: str) -> List[Operario_Articulo]:
    """Lista todos los tiempos por artículo definidos para un operario.

    Args:
        session: Sesión de base de datos activa.
        dni_operario: DNI del operario.

    Returns:
        Lista de relaciones ``Operario_Articulo`` del operario.
    """
    return list(session.scalars(
        select(Operario_Articulo).where(Operario_Articulo.dni_operario == dni_operario)
    ).all())


def listar_bulk(
    session: Session,
    dnis: List[str],
    refs_articulos: Optional[List[str]] = None,
) -> List[Operario_Articulo]:
    """Lee en bloque las relaciones operario-artículo para varios operarios.

    Args:
        session: Sesión de base de datos activa.
        dnis: DNIs de los operarios a incluir.
        refs_articulos: Si se indica, restringe a estas referencias de artículo.

    Returns:
        Lista de relaciones ``Operario_Articulo`` que cumplen los filtros.
    """
    stmt = select(Operario_Articulo).where(Operario_Articulo.dni_operario.in_(dnis))
    if refs_articulos is not None:
        stmt = stmt.where(Operario_Articulo.ref_articulo.in_(refs_articulos))
    return list(session.scalars(stmt).all())


def contar(session: Session) -> int:
    """Cuenta el total de relaciones operario-artículo.

    Args:
        session: Sesión de base de datos activa.

    Returns:
        Número de filas ``Operario_Articulo`` registradas.
    """
    return session.scalar(select(func.count()).select_from(Operario_Articulo))
