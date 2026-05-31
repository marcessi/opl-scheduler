"""Servicio de Operario_Articulo (lecturas puras → delega a crud)."""

from typing import List, Optional
from sqlalchemy.orm import Session
from src.database.schema import Operario_Articulo
from src.crud.datos_maestros import operario_articulo as _crud


def leer_operario_articulo(
    session: Session, ref_articulo: str, dni_operario: str,
) -> Optional[Operario_Articulo]:
    """Lee el tiempo específico de un operario para un artículo.

    Args:
        session: Sesión de base de datos activa.
        ref_articulo: Referencia del artículo.
        dni_operario: DNI del operario.

    Returns:
        El ``Operario_Articulo`` correspondiente, o ``None`` si no existe.
    """
    return _crud.leer(session, ref_articulo, dni_operario)


def leer_articulos_de_operario(session: Session, dni_operario: str) -> List[Operario_Articulo]:
    """Lista los tiempos por artículo definidos para un operario.

    Args:
        session: Sesión de base de datos activa.
        dni_operario: DNI del operario.

    Returns:
        Lista de relaciones ``Operario_Articulo`` del operario.
    """
    return _crud.listar_por_operario(session, dni_operario)


def leer_operario_articulo_bulk(
    session: Session,
    dnis: List[str],
    refs_articulos: Optional[List[str]] = None,
) -> List[Operario_Articulo]:
    """Lee en bloque los tiempos por artículo de varios operarios.

    Args:
        session: Sesión de base de datos activa.
        dnis: DNIs de los operarios a incluir.
        refs_articulos: Si se indica, restringe a estas referencias de artículo.

    Returns:
        Lista de relaciones ``Operario_Articulo`` que cumplen los filtros.
    """
    return _crud.listar_bulk(session, dnis, refs_articulos)


def contar_operario_articulo(session: Session) -> int:
    """Cuenta el total de relaciones operario-artículo.

    Args:
        session: Sesión de base de datos activa.

    Returns:
        Número de filas ``Operario_Articulo`` registradas.
    """
    return _crud.contar(session)
