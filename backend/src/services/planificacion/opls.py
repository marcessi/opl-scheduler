"""Servicio de OPL (lecturas puras → delega a crud)."""

from typing import List, Optional
from sqlalchemy.orm import Session
from src.database.schema import OPL
from src.crud.planificacion import opls as _crud
from src.services.datos_maestros import articulos as articulo_service
from src.exceptions import NotFoundError


def leer_opl(session: Session, id: str) -> Optional[OPL]:
    return _crud.leer(session, id)


def leer_opls_bulk(session: Session, ids: list[str]) -> List[OPL]:
    return _crud.leer_bulk(session, ids)


def leer_todas_opls(session: Session) -> List[OPL]:
    return _crud.listar(session)


def contar_opls(session: Session) -> int:
    return _crud.contar(session)


def crear_opl_manual(session: Session, ref_articulo: str, cantidad: int) -> OPL:
    if articulo_service.leer_articulo(session, ref_articulo) is None:
        raise NotFoundError(f"Articulo '{ref_articulo}' no existe")
    id = _crud.siguiente_id_manual(session)
    opl = _crud.crear(session, id, ref_articulo, cantidad)
    session.commit()
    return opl
