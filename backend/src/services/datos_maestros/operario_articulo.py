"""Servicio de Operario_Articulo (lecturas puras → delega a crud)."""

from typing import List, Optional
from sqlalchemy.orm import Session
from src.database.schema import Operario_Articulo
from src.crud.datos_maestros import operario_articulo as _crud


def leer_operario_articulo(
    session: Session, ref_articulo: str, dni_operario: str,
) -> Optional[Operario_Articulo]:
    return _crud.leer(session, ref_articulo, dni_operario)


def leer_articulos_de_operario(session: Session, dni_operario: str) -> List[Operario_Articulo]:
    return _crud.listar_por_operario(session, dni_operario)


def leer_operario_articulo_bulk(
    session: Session,
    dnis: List[str],
    refs_articulos: Optional[List[str]] = None,
) -> List[Operario_Articulo]:
    return _crud.listar_bulk(session, dnis, refs_articulos)


def contar_operario_articulo(session: Session) -> int:
    return _crud.contar(session)
