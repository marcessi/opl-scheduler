"""Tests para la creación manual de OPLs (services.planificacion.opls)."""

import pytest

from src.exceptions import NotFoundError
from src.services.planificacion import opls as opl_service


def test_crear_opl_manual_genera_ids_correlativos(base_data):
    session = base_data

    opl1 = opl_service.crear_opl_manual(session, "ART-001", 5)
    assert opl1.id == "MAN000001"
    assert opl1.ref_articulo == "ART-001"
    assert opl1.cantidad == 5

    opl2 = opl_service.crear_opl_manual(session, "ART-001", 3)
    assert opl2.id == "MAN000002"


def test_crear_opl_manual_ignora_ids_no_manuales(base_data):
    session = base_data
    # base_data ya tiene OPL-001; no debe interferir con la numeración MAN
    opl = opl_service.crear_opl_manual(session, "ART-001", 1)
    assert opl.id == "MAN000001"


def test_crear_opl_manual_articulo_inexistente(base_data):
    session = base_data
    with pytest.raises(NotFoundError):
        opl_service.crear_opl_manual(session, "NO-EXISTE", 5)
