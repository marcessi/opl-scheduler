"""
Tests para el módulo validator.py.
"""

import pytest
from src.database.schema import (
    Familia, Articulo, Operario, Operario_Familia, Operario_Articulo, OPL, AsignacionOPL, Reparto, TipoAsignacion
)
from datetime import date
from src.optimization.cargador_problema import cargar_datos_problema
from src.optimization.validacion import validar_opls, validar_datos_problema


class TestValidarOpls:

    def test_opl_inexistente(self, base_data):
        resultado = validar_opls(base_data, ["NO-EXISTE"])
        assert not resultado.valido
        assert any("NO-EXISTE" in e for e in resultado.errores)

    def test_valido_con_datos_correctos(self, base_data):
        resultado = validar_opls(base_data, ["OPL-001"])
        assert resultado.valido
        assert resultado.errores == []

    def test_sin_operarios_registrados(self, session):
        """Sin operarios en BD la validacion falla."""
        session.add(Familia(descripcion="F", experiencia_requerida=1))
        session.add(Articulo(
            referencia="ART-X", familia="F",
            descripcion="test", peso=1.0, tiempo_estandar=10.0
        ))
        session.add(OPL(id="OPL-X", ref_articulo="ART-X", cantidad=1))
        session.commit()

        resultado = validar_opls(session, ["OPL-X"])
        assert not resultado.valido
        assert any("operarios" in e.lower() for e in resultado.errores)

    def test_solo_operarios_con_horas_cero_falla(self, session):
        """Si todos los operarios tienen 0h, se consideran inactivos para validar reparto."""
        session.add(Familia(descripcion="F", experiencia_requerida=1))
        session.add(Articulo(
            referencia="ART-Z0", familia="F",
            descripcion="test", peso=1.0, tiempo_estandar=10.0
        ))
        session.add(Operario(dni="00000000Z", nombre_completo="Inactivo", horas_semanales=0.0))
        session.add(OPL(id="OPL-Z0", ref_articulo="ART-Z0", cantidad=1))
        session.commit()

        resultado = validar_opls(session, ["OPL-Z0"])
        assert not resultado.valido
        assert any("activos" in e.lower() for e in resultado.errores)

    def test_multiple_opls_valido(self, session):
        """Múltiples OPLs válidas pasan la validación."""
        session.add(Familia(descripcion="F", experiencia_requerida=1))
        session.add(Articulo(
            referencia="ART-M", familia="F",
            descripcion="test", peso=1.0, tiempo_estandar=10.0
        ))
        session.add(Operario(dni="55555555A", nombre_completo="Op Multi", horas_semanales=40.0))
        session.add(OPL(id="OPL-M1", ref_articulo="ART-M", cantidad=5))
        session.add(OPL(id="OPL-M2", ref_articulo="ART-M", cantidad=3))
        session.commit()

        resultado = validar_opls(session, ["OPL-M1", "OPL-M2"])
        assert resultado.valido

    def test_obligatoria_sin_operario_familia_es_valida(self, session):
        """Una OBLIGATORIA sin Operario_Familia ya no falla: todo operario activo es candidato."""
        semana = date(2025, 1, 6)

        session.add(Familia(descripcion="F", experiencia_requerida=2))
        session.add(Articulo(
            referencia="ART-OBL", familia="F",
            descripcion="test", peso=1.0, tiempo_estandar=10.0
        ))
        session.add(Operario(dni="OP-OBL", nombre_completo="Sin familia", horas_semanales=40.0))
        session.add(OPL(id="OPL-OBL", ref_articulo="ART-OBL", cantidad=2))
        session.add(Reparto(semana=semana, aprobado=False))
        session.add(AsignacionOPL(
            id_opl="OPL-OBL",
            semana=semana,
            dni_operario=None,
            tipo_asignacion=TipoAsignacion.OBLIGATORIA,
            tiempo_planificado=20.0,
            tiempo_estimado_operario=None,
            tiempo_total_teorico=20.0,
        ))
        session.commit()

        datos = cargar_datos_problema(session, [], semana)
        resultado = validar_datos_problema(datos)

        assert resultado.valido
