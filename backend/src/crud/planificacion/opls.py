"""CRUD para OPL."""

from typing import List, Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from src.database.schema import OPL


def leer(session: Session, id: str) -> Optional[OPL]:
    """Lee una OPL por su identificador.

    Args:
        session: Sesión de base de datos activa.
        id: Identificador de la OPL.

    Returns:
        La ``OPL`` encontrada, o ``None`` si no existe.
    """
    return session.scalars(select(OPL).where(OPL.id == id)).first()


def leer_bulk(session: Session, ids: list[str]) -> List[OPL]:
    """Lee varias OPLs en una sola query.

    Args:
        session: Sesión de base de datos activa.
        ids: Lista de identificadores de OPL.

    Returns:
        Lista de las OPLs existentes entre los ids dados (omite los ausentes).
    """
    return list(session.scalars(select(OPL).where(OPL.id.in_(ids))).all())


def listar(session: Session) -> List[OPL]:
    """Lista todas las OPLs.

    Args:
        session: Sesión de base de datos activa.

    Returns:
        Lista con todas las OPLs de la base de datos.
    """
    return list(session.scalars(select(OPL)).all())


def contar(session: Session) -> int:
    """Cuenta el total de OPLs.

    Args:
        session: Sesión de base de datos activa.

    Returns:
        Número de OPLs registradas.
    """
    return session.scalar(select(func.count()).select_from(OPL))


def crear(session: Session, id: str, ref_articulo: str, cantidad: int) -> OPL:
    """Crea una OPL y la vuelca con ``flush`` (sin ``commit``).

    Args:
        session: Sesión de base de datos activa.
        id: Identificador de la nueva OPL.
        ref_articulo: Referencia del artículo asociado.
        cantidad: Número de unidades a producir.

    Returns:
        La instancia ``OPL`` recién creada.
    """
    opl = OPL(id=id, ref_articulo=ref_articulo, cantidad=cantidad)
    session.add(opl)
    session.flush()
    return opl


def siguiente_id_manual(session: Session) -> str:
    """Calcula el siguiente id libre para una OPL creada a mano.

    Las OPLs manuales usan el prefijo ``MAN`` seguido de un contador de 6 dígitos.

    Args:
        session: Sesión de base de datos activa.

    Returns:
        El próximo id disponible con formato ``MANnnnnnn``.
    """
    ids = session.scalars(select(OPL.id).where(OPL.id.like("MAN%"))).all()
    maximo = 0
    for id_ in ids:
        try:
            maximo = max(maximo, int(id_[3:]))
        except (ValueError, IndexError):
            continue
    return f"MAN{maximo + 1:06d}"
