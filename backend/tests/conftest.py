"""
Fixtures compartidas para todos los tests.

Usa PostgreSQL (opl_scheduler_test) — requiere la BD levantada via Docker.
Patrón de aislamiento: tablas creadas una vez por sesión de pytest;
entre tests se hace TRUNCATE CASCADE para dejar el estado limpio.
"""

import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.config import TEST_DATABASE_URL
from src.database.base import Base
from src.database.schema import (
    Familia, Articulo, Operario, Operario_Familia, Operario_Articulo, OPL
)

_test_engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)


@pytest.fixture(scope="session", autouse=True)
def _setup_schema():
    """Crea todas las tablas al inicio de la sesión de tests y las elimina al final."""
    Base.metadata.create_all(bind=_test_engine)
    yield
    Base.metadata.drop_all(bind=_test_engine)
    _test_engine.dispose()


@pytest.fixture
def session(_setup_schema):
    """Sesión PostgreSQL limpia por cada test (TRUNCATE CASCADE entre tests)."""
    Session = sessionmaker(
        bind=_test_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )
    sess = Session()

    yield sess

    sess.rollback()
    sess.close()

    # Truncar todas las tablas en orden inverso de dependencias FK
    with _test_engine.connect() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(
                sa.text(f'TRUNCATE TABLE "{table.name}" RESTART IDENTITY CASCADE')
            )
        conn.commit()


@pytest.fixture
def base_data(session):
    """
    Precarga un conjunto mínimo de datos coherentes:
      - Familia: Ensamblaje (exp_requerida=1)
      - Articulo: ART-001 (Ensamblaje, tiempo_estandar=30.0, peso=1.0)
      - Operario 1: 12345678A (40h/semana)
      - Operario 2: 87654321B (40h/semana)
      - Operario_Familia: ambos en Ensamblaje (exp=2)
      - Operario_Articulo: 12345678A->ART-001 (25min), 87654321B->ART-001 (30min)
      - OPL: OPL-001 (ART-001, cantidad=10)

    tiempo_estimado_operario (op1) = 10 * 25 = 250 min
    tiempo_estimado_operario (op2) = 10 * 30 = 300 min
    """
    familia = Familia(descripcion="Ensamblaje", experiencia_requerida=1)
    articulo = Articulo(
        referencia="ART-001", familia="Ensamblaje",
        descripcion="Pieza test", peso=1.0, tiempo_estandar=30.0
    )
    op1 = Operario(dni="12345678A", nombre_completo="Juan Test", horas_semanales=40.0)
    op2 = Operario(dni="87654321B", nombre_completo="Maria Test", horas_semanales=40.0)
    of1 = Operario_Familia(dni_operario="12345678A", familia="Ensamblaje", experiencia=2)
    of2 = Operario_Familia(dni_operario="87654321B", familia="Ensamblaje", experiencia=2)
    oa1 = Operario_Articulo(ref_articulo="ART-001", dni_operario="12345678A", tiempo_estimado=25.0)
    oa2 = Operario_Articulo(ref_articulo="ART-001", dni_operario="87654321B", tiempo_estimado=30.0)
    opl = OPL(id="OPL-001", ref_articulo="ART-001", cantidad=10)

    for obj in [familia, articulo, op1, op2, of1, of2, oa1, oa2, opl]:
        session.add(obj)
    session.commit()

    return session
