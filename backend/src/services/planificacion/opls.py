"""Servicio de OPL (lecturas puras → delega a crud)."""

from typing import List, Optional
from sqlalchemy.orm import Session
from src.database.schema import OPL
from src.crud.planificacion import opls as _crud
from src.services.datos_maestros import articulos as articulo_service
from src.exceptions import NotFoundError


def leer_opl(session: Session, id: str) -> Optional[OPL]:
    """Lee una OPL por su identificador.

    Args:
        session: Sesión de base de datos activa.
        id: Identificador de la OPL.

    Returns:
        La ``OPL`` encontrada, o ``None`` si no existe.
    """
    return _crud.leer(session, id)


def leer_opls_bulk(session: Session, ids: list[str]) -> List[OPL]:
    """Lee varias OPLs en una sola query.

    Args:
        session: Sesión de base de datos activa.
        ids: Lista de identificadores de OPL.

    Returns:
        Lista de las OPLs existentes entre los ids dados.
    """
    return _crud.leer_bulk(session, ids)


def leer_todas_opls(session: Session) -> List[OPL]:
    """Lista todas las OPLs.

    Args:
        session: Sesión de base de datos activa.

    Returns:
        Lista con todas las OPLs.
    """
    return _crud.listar(session)


def contar_opls(session: Session) -> int:
    """Cuenta el total de OPLs.

    Args:
        session: Sesión de base de datos activa.

    Returns:
        Número de OPLs registradas.
    """
    return _crud.contar(session)


def crear_opl_manual(session: Session, ref_articulo: str, cantidad: int) -> OPL:
    """Crea una OPL manual validando que el artículo exista, y hace ``commit``.

    El id se autogenera con el prefijo ``MAN`` (ver
    :func:`crud.planificacion.opls.siguiente_id_manual`).

    Args:
        session: Sesión de base de datos activa.
        ref_articulo: Referencia del artículo a producir.
        cantidad: Número de unidades.

    Returns:
        La ``OPL`` recién creada.

    Raises:
        NotFoundError: si el artículo indicado no existe.
    """
    if articulo_service.leer_articulo(session, ref_articulo) is None:
        raise NotFoundError(f"Articulo '{ref_articulo}' no existe")
    id = _crud.siguiente_id_manual(session)
    opl = _crud.crear(session, id, ref_articulo, cantidad)
    session.commit()
    return opl
