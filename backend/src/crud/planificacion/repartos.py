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
    """Lista repartos aplicando filtros opcionales, ordenados por semana.

    Args:
        session: Sesión de base de datos activa.
        semana: Si se indica, devuelve solo el reparto de esa semana exacta.
        antes_de: Si se indica, restringe a repartos de semanas anteriores.
        aprobado: Si se indica, filtra por estado de aprobación.

    Returns:
        Lista de repartos que cumplen los filtros, ordenados por semana ascendente.
    """
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
    """Lee el reparto de una semana.

    Args:
        session: Sesión de base de datos activa.
        semana: Lunes ISO de la semana.

    Returns:
        El ``Reparto`` de esa semana, o ``None`` si no existe.
    """
    return session.scalars(select(Reparto).where(Reparto.semana == semana)).first()


def crear(session: Session, semana: date) -> Reparto:
    """Crea un reparto sin aprobar y lo vuelca con ``flush`` (sin ``commit``).

    Args:
        session: Sesión de base de datos activa.
        semana: Lunes ISO de la semana del nuevo reparto.

    Returns:
        El ``Reparto`` recién creado con ``aprobado=False``.
    """
    reparto = Reparto(semana=semana, aprobado=False)
    session.add(reparto)
    session.flush()
    return reparto
