"""
Tests para los servicios de lectura de datos_maestros y planificacion.opls.
"""

from src.database.schema import OPL
from src.services.datos_maestros import (
    operario_familia as operario_familia_service,
    operario_articulo as operario_articulo_service,
)
from src.services.planificacion import opls as opl_service


# ─────────────────────────────────────────────────────────────────────────────
# operario_familia_service
# ─────────────────────────────────────────────────────────────────────────────

class TestOperarioFamiliaService:

    def test_leer_familias_de_operario(self, base_data):
        familias = operario_familia_service.leer_familias_de_operario(
            base_data, "12345678A"
        )
        assert len(familias) >= 1
        assert any(f.familia == "Ensamblaje" for f in familias)


# ─────────────────────────────────────────────────────────────────────────────
# operario_articulo_service
# ─────────────────────────────────────────────────────────────────────────────

class TestOperarioArticuloService:

    def test_leer(self, base_data):
        oa = operario_articulo_service.leer_operario_articulo(
            base_data, "ART-001", "12345678A"
        )
        assert oa is not None
        assert oa.tiempo_estimado == 25.0

    def test_leer_inexistente_retorna_none(self, base_data):
        assert operario_articulo_service.leer_operario_articulo(
            base_data, "ART-001", "NOEXISTE"
        ) is None

    def test_leer_articulos_de_operario(self, base_data):
        arts = operario_articulo_service.leer_articulos_de_operario(
            base_data, "12345678A"
        )
        assert len(arts) == 1
        assert arts[0].ref_articulo == "ART-001"


# ─────────────────────────────────────────────────────────────────────────────
# opl_service
# ─────────────────────────────────────────────────────────────────────────────

class TestOplService:
    def test_leer_opl(self, base_data):
        opl = opl_service.leer_opl(base_data, "OPL-001")
        assert opl is not None
        assert opl.ref_articulo == "ART-001"

    def test_leer_inexistente_retorna_none(self, base_data):
        assert opl_service.leer_opl(base_data, "NO-EXISTE") is None

    def test_leer_todas_opls(self, base_data):
        base_data.add(OPL(id="OPL-XYZ", ref_articulo="ART-001", cantidad=3))
        base_data.commit()

        opls = opl_service.leer_todas_opls(base_data)
        ids = {o.id for o in opls}
        assert "OPL-001" in ids
        assert "OPL-XYZ" in ids

    def test_contar_opls(self, base_data):
        base_data.add(OPL(id="OPL-XYZ", ref_articulo="ART-001", cantidad=3))
        base_data.commit()

        assert opl_service.contar_opls(base_data) == 2
