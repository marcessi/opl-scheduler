"""CRUD para Familia."""

from typing import List, Optional
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from src.database.schema import Familia


def listar(session: Session) -> List[Familia]:
    return list(session.scalars(select(Familia)).all())


def leer(session: Session, descripcion: str) -> Optional[Familia]:
    return session.scalars(select(Familia).where(Familia.descripcion == descripcion)).first()


def contar(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(Familia))
