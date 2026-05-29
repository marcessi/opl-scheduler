"""Servicio de Articulo (lecturas puras → delega a crud)."""

from typing import List, Optional
from sqlalchemy.orm import Session
from src.database.schema import Articulo
from src.crud.datos_maestros import articulos as _crud


def leer_articulo(session: Session, referencia: str) -> Optional[Articulo]:
    return _crud.leer(session, referencia)


def leer_articulos_bulk(session: Session, refs: list[str]) -> List[Articulo]:
    return _crud.leer_bulk(session, refs)


def leer_articulos_por_familia(session: Session, familia: str) -> List[Articulo]:
    return _crud.listar_por_familia(session, familia)


def contar_articulos(session: Session) -> int:
    return _crud.contar(session)
