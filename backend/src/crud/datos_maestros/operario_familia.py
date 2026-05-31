"""CRUD para Operario_Familia (experiencia por familia)."""

from typing import List, Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from src.database.schema import Operario_Familia


def listar_por_operario(session: Session, dni_operario: str) -> List[Operario_Familia]:
    """Lista la experiencia por familia de un operario.

    Args:
        session: Sesión de base de datos activa.
        dni_operario: DNI del operario.

    Returns:
        Lista de relaciones ``Operario_Familia`` del operario.
    """
    return list(session.scalars(
        select(Operario_Familia).where(Operario_Familia.dni_operario == dni_operario)
    ).all())


def listar_bulk(
    session: Session,
    dnis: List[str],
    familias: Optional[List[str]] = None,
) -> List[Operario_Familia]:
    """Lee en bloque la experiencia por familia para varios operarios.

    Args:
        session: Sesión de base de datos activa.
        dnis: DNIs de los operarios a incluir.
        familias: Si se indica, restringe a estas descripciones de familia.

    Returns:
        Lista de relaciones ``Operario_Familia`` que cumplen los filtros.
    """
    stmt = select(Operario_Familia).where(Operario_Familia.dni_operario.in_(dnis))
    if familias is not None:
        stmt = stmt.where(Operario_Familia.familia.in_(familias))
    return list(session.scalars(stmt).all())


def contar(session: Session) -> int:
    """Cuenta el total de relaciones operario-familia.

    Args:
        session: Sesión de base de datos activa.

    Returns:
        Número de filas ``Operario_Familia`` registradas.
    """
    return session.scalar(select(func.count()).select_from(Operario_Familia))
