"""CRUD para Usuario."""

from typing import Optional
from sqlalchemy import select
from sqlalchemy.orm import Session
from src.database.schema import Usuario


def leer_por_username(session: Session, username: str) -> Optional[Usuario]:
    return session.scalars(select(Usuario).where(Usuario.username == username)).first()
