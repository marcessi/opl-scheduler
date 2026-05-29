"""
Database initialization logic.
"""

import logging
from src.database.base import Base
from src.database.session import engine
from src.config import DATABASE_URL, ADMIN_BOOTSTRAP_PASSWORD

logger = logging.getLogger(__name__)


def init_db() -> None:
    """
    Initialize database by creating all tables.

    En producción, Alembic gestiona el esquema. Esta función es idempotente:
    `create_all` es no-op si las tablas ya existen. Útil para tests con SQLite
    en memoria y para el primer arranque sin Alembic.
    """
    # Importa el módulo de modelos para registrarlos en la metadata de SQLAlchemy
    import src.database.schema  # noqa: F401

    Base.metadata.create_all(bind=engine)
    seed_admin()

    logger.info("Database initialized: %s", DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else DATABASE_URL)


def seed_admin() -> None:
    """Crea el usuario admin si no existe. Idempotente."""
    from src.database.schema import Usuario
    from src.database.session import SessionLocal
    from src.services.auth import hash_password

    with SessionLocal() as session:
        exists = session.get(Usuario, "admin")
        if exists is None:
            session.add(Usuario(
                username="admin",
                hashed_password=hash_password(ADMIN_BOOTSTRAP_PASSWORD),
            ))
            session.commit()
            logger.info("Usuario 'admin' creado — cambia la contraseña tras el primer login")


def drop_all_tables() -> None:
    """
    Drop all database tables.

    WARNING: This will delete all data. Use only for development/testing.
    """
    import src.database.schema  # noqa: F401

    Base.metadata.drop_all(bind=engine)
    print("[WARNING] All tables dropped")
