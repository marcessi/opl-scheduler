"""Servicio de Operario_Familia (lecturas puras → delega a crud)."""

from typing import List, Optional
from sqlalchemy.orm import Session
from src.database.schema import Operario_Familia
from src.crud.datos_maestros import operario_familia as _crud


def leer_familias_de_operario(session: Session, dni_operario: str) -> List[Operario_Familia]:
    """Lista la experiencia por familia de un operario.

    Args:
        session: Sesión de base de datos activa.
        dni_operario: DNI del operario.

    Returns:
        Lista de relaciones ``Operario_Familia`` del operario.
    """
    return _crud.listar_por_operario(session, dni_operario)


def leer_operario_familia_bulk(
    session: Session,
    dnis: List[str],
    familias: Optional[List[str]] = None,
) -> List[Operario_Familia]:
    """Lee en bloque la experiencia por familia de varios operarios.

    Args:
        session: Sesión de base de datos activa.
        dnis: DNIs de los operarios a incluir.
        familias: Si se indica, restringe a estas descripciones de familia.

    Returns:
        Lista de relaciones ``Operario_Familia`` que cumplen los filtros.
    """
    return _crud.listar_bulk(session, dnis, familias)


def contar_operario_familia(session: Session) -> int:
    """Cuenta el total de relaciones operario-familia.

    Args:
        session: Sesión de base de datos activa.

    Returns:
        Número de filas ``Operario_Familia`` registradas.
    """
    return _crud.contar(session)
