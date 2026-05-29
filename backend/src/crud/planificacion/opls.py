"""CRUD para OPL."""

from typing import List, Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from src.database.schema import OPL


def leer(session: Session, id: str) -> Optional[OPL]:
    return session.scalars(select(OPL).where(OPL.id == id)).first()


def leer_bulk(session: Session, ids: list[str]) -> List[OPL]:
    return list(session.scalars(select(OPL).where(OPL.id.in_(ids))).all())


def listar(session: Session) -> List[OPL]:
    return list(session.scalars(select(OPL)).all())


def contar(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(OPL))


def crear(session: Session, id: str, ref_articulo: str, cantidad: int) -> OPL:
    opl = OPL(id=id, ref_articulo=ref_articulo, cantidad=cantidad)
    session.add(opl)
    session.flush()
    return opl


def siguiente_id_manual(session: Session) -> str:
    ids = session.scalars(select(OPL.id).where(OPL.id.like("MAN%"))).all()
    maximo = 0
    for id_ in ids:
        try:
            maximo = max(maximo, int(id_[3:]))
        except (ValueError, IndexError):
            continue
    return f"MAN{maximo + 1:06d}"
