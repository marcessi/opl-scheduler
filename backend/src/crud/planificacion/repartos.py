"""CRUD para Reparto."""

from datetime import date
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.database.schema import Reparto


def listar(
    session: Session,
    semana: Optional[date] = None,
    antes_de: Optional[date] = None,
    aprobado: Optional[bool] = None,
) -> List[Reparto]:
    stmt = select(Reparto)
    if semana is not None:
        stmt = stmt.where(Reparto.semana == semana)
    if antes_de is not None:
        stmt = stmt.where(Reparto.semana < antes_de)
    if aprobado is not None:
        stmt = stmt.where(Reparto.aprobado == aprobado)
    stmt = stmt.order_by(Reparto.semana)
    return list(session.scalars(stmt).all())


def leer(session: Session, semana: date) -> Optional[Reparto]:
    return session.scalars(select(Reparto).where(Reparto.semana == semana)).first()


def crear(session: Session, semana: date) -> Reparto:
    reparto = Reparto(semana=semana, aprobado=False)
    session.add(reparto)
    session.flush()
    return reparto
