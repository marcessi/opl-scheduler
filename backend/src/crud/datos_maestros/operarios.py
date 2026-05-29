"""CRUD para Operario."""

from typing import List, Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from src.database.schema import Operario


def listar(session: Session) -> List[Operario]:
    return list(session.scalars(select(Operario)).all())


def leer(session: Session, dni: str) -> Optional[Operario]:
    return session.scalars(select(Operario).where(Operario.dni == dni)).first()


def contar(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(Operario))
