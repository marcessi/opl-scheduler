"""
Tests para el módulo optimizer.py (resolver) — MVP.
"""

import pytest
from src.database.schema import (
    Familia, Articulo, Operario, Operario_Familia, Operario_Articulo, OPL
)
from src.optimization.cargador_problema import cargar_datos_problema
from src.optimization.solver import resolver, Configuracion


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _base(session, horas_op1=40.0, horas_op2=40.0):
    """
    Inserta: Familia 'Fam' (exp=1), Articulo 'REF' (t=10min/ud),
    Operario OP1 y OP2 con las horas indicadas, ambos cualificados.
    """
    session.add_all([
        Familia(descripcion="Fam", experiencia_requerida=1),
        Articulo(referencia="REF", familia="Fam",
                 descripcion="Art test", peso=1.0, tiempo_estandar=10.0),
        Operario(dni="OP1", nombre_completo="Operario 1", horas_semanales=horas_op1),
        Operario(dni="OP2", nombre_completo="Operario 2", horas_semanales=horas_op2),
        Operario_Familia(dni_operario="OP1", familia="Fam", experiencia=2),
        Operario_Familia(dni_operario="OP2", familia="Fam", experiencia=2),
        Operario_Articulo(ref_articulo="REF", dni_operario="OP1", tiempo_estimado=10.0),
        Operario_Articulo(ref_articulo="REF", dni_operario="OP2", tiempo_estimado=10.0),
    ])
    session.commit()


def _opl(id_, cantidad):
    return OPL(id=id_, ref_articulo="REF", cantidad=cantidad)


def _setup_eficiencia_case(
    session,
    *,
    familia: str,
    ref: str,
    id_opl: str,
    exp_requerida: int,
    exp_op1: int,
    exp_op2: int,
    t_op1: float,
    t_op2: float,
    cantidad: int = 1,
):
    """Configura un caso mínimo con 1 OPL y 2 operarios para testear eficiencia."""
    session.add_all([
        Familia(descripcion=familia, experiencia_requerida=exp_requerida),
        Articulo(
            referencia=ref,
            familia=familia,
            descripcion="Art eficiencia",
            peso=1.0,
            tiempo_estandar=10.0,
        ),
        Operario(dni="OP1", nombre_completo="Operario 1", horas_semanales=40.0),
        Operario(dni="OP2", nombre_completo="Operario 2", horas_semanales=40.0),
        Operario_Familia(dni_operario="OP1", familia=familia, experiencia=exp_op1),
        Operario_Familia(dni_operario="OP2", familia=familia, experiencia=exp_op2),
        Operario_Articulo(ref_articulo=ref, dni_operario="OP1", tiempo_estimado=t_op1),
        Operario_Articulo(ref_articulo=ref, dni_operario="OP2", tiempo_estimado=t_op2),
        OPL(id=id_opl, ref_articulo=ref, cantidad=cantidad),
    ])
    session.commit()


# ─────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────

class TestResolver:

    def test_sin_opls_devuelve_optima(self, session):
        """Sin OPLs el solver devuelve OPTIMA con todos los campos vacíos."""
        datos = cargar_datos_problema(session, [])
        resultado = resolver(datos, Configuracion())

        assert resultado.estado == "OPTIMA"
        assert resultado.asignaciones == {}
        assert resultado.no_asignadas == []

    def test_asigna_opl_cuando_cabe(self, session):
        """Una OPL cuyo tiempo cabe en la capacidad del operario queda asignada."""
        _base(session)  # OP1 y OP2: 40h = 2400 min
        session.add(_opl("OPL-1", cantidad=1))  # 1 * 10 = 10 min
        session.commit()

        datos = cargar_datos_problema(session, ["OPL-1"])
        resultado = resolver(datos, Configuracion())

        assert resultado.estado == "OPTIMA"
        assert "OPL-1" in resultado.asignaciones
        assert resultado.no_asignadas == []

    def test_opl_no_asignada_si_no_cabe(self, session):
        """Si no cabe completa, puede asignarse parcialmente para rellenar capacidad."""
        _base(session, horas_op1=1.0, horas_op2=1.0)  # 60 min cada uno
        session.add(_opl("OPL-1", cantidad=10))        # 10 * 10 = 100 min — no cabe
        session.commit()

        datos = cargar_datos_problema(session, ["OPL-1"])
        resultado = resolver(datos, Configuracion())

        assert "OPL-1" in resultado.asignaciones
        assert resultado.tiempos_asignados["OPL-1"] == 60
        assert "OPL-1" not in resultado.no_asignadas

    def test_maximiza_opls_asignadas(self, session):
        """Con parciales activas, puede usar hueco residual y asignar también una tercera OPL."""
        # 5 ud * 10 min = 50 min por OPL; capacidad = 60 min → 1 OPL por operario
        _base(session, horas_op1=1.0, horas_op2=1.0)
        session.add_all([_opl("A", 5), _opl("B", 5), _opl("C", 5)])
        session.commit()

        datos = cargar_datos_problema(session, ["A", "B", "C"])
        resultado = resolver(datos, Configuracion())

        assert resultado.estado == "OPTIMA"
        assert len(resultado.asignaciones) == 3
        assert len(resultado.no_asignadas) == 0
        assert sum(1 for t in resultado.tiempos_asignados.values() if t < 50) == 1
        assert max(resultado.cargas.values()) <= 60

    def test_cargas_no_superan_capacidad(self, session):
        """La carga acumulada de cada operario nunca supera su capacidad."""
        _base(session)  # 40h = 2400 min por operario
        session.add_all([_opl("A", 100), _opl("B", 100), _opl("C", 100)])
        session.commit()

        datos = cargar_datos_problema(session, ["A", "B", "C"])
        resultado = resolver(datos, Configuracion())

        for j, dni in enumerate(datos.dnis_operarios):
            carga = resultado.cargas.get(dni, 0)
            assert carga <= datos.capacidades[j], (
                f"{dni}: carga {carga} min > capacidad {datos.capacidades[j]} min"
            )

    def test_operario_sin_operario_familia_es_asignable_con_exp_minima(self, session):
        """Sin Operario_Familia, el operario sigue siendo candidato (exp=1, no cualificado)."""
        session.add_all([
            Familia(descripcion="Fam", experiencia_requerida=1),
            Articulo(referencia="REF", familia="Fam",
                     descripcion="Art", peso=1.0, tiempo_estandar=10.0),
            Operario(dni="OP1", nombre_completo="Sin exp", horas_semanales=40.0),
        ])
        session.commit()
        session.add(_opl("OPL-1", cantidad=1))
        session.commit()

        datos = cargar_datos_problema(session, ["OPL-1"])
        assert datos.experiencias[(0, 0)] == 1
        assert (0, 0) not in datos.cualificados

        resultado = resolver(datos, Configuracion())
        assert resultado.asignaciones["OPL-1"] == "OP1"
        assert "OPL-1" not in resultado.no_asignadas

    def test_eficiencia_tiempo_operario_mayor_al_estandar_usa_estandar(self, session):
        """Si tiempo_operario > estándar, se toma estándar para decidir eficiencia."""
        _setup_eficiencia_case(
            session,
            familia="FamE4",
            ref="REFE4",
            id_opl="OPL-E4",
            exp_requerida=3,
            exp_op1=4,
            exp_op2=4,
            t_op1=12.0,
            t_op2=8.0,
        )

        # OP1: 12 (>10 estándar) -> se corrige a 10; OP2: 8 -> gana OP2.
        datos = cargar_datos_problema(session, ["OPL-E4"])
        resultado = resolver(datos, Configuracion(nivel_eficiencia=100))

        assert resultado.estado in {"OPTIMA", "FACTIBLE"}
        assert resultado.asignaciones["OPL-E4"] == "OP2"

    def test_eficiencia_prioriza_asignacion_optima(self, session):
        """Eficiencia prioriza operario cualificado aunque otro sea más rápido."""
        _setup_eficiencia_case(
            session,
            familia="FamE1",
            ref="REFE1",
            id_opl="OPL-E1",
            exp_requerida=4,
            exp_op1=4,
            exp_op2=3,
            t_op1=20.0,
            t_op2=5.0,
        )

        datos = cargar_datos_problema(session, ["OPL-E1"])
        resultado = resolver(datos, Configuracion(nivel_eficiencia=100))

        assert resultado.estado in {"OPTIMA", "FACTIBLE"}
        assert resultado.asignaciones["OPL-E1"] == "OP1"

    def test_eficiencia_desempata_optimas_por_velocidad(self, session):
        """Entre operarios cualificados, eficiencia elige al más rápido."""
        _setup_eficiencia_case(
            session,
            familia="FamE2",
            ref="REFE2",
            id_opl="OPL-E2",
            exp_requerida=3,
            exp_op1=4,
            exp_op2=4,
            t_op1=15.0,
            t_op2=7.0,
        )

        datos = cargar_datos_problema(session, ["OPL-E2"])
        resultado = resolver(datos, Configuracion(nivel_eficiencia=100))

        assert resultado.estado in {"OPTIMA", "FACTIBLE"}
        assert resultado.asignaciones["OPL-E2"] == "OP2"

    def test_eficiencia_sin_optimos_prioriza_experiencia_sobre_velocidad(self, session):
        """Si nadie es óptimo, eficiencia prioriza mayor experiencia y luego velocidad."""
        _setup_eficiencia_case(
            session,
            familia="FamE3",
            ref="REFE3",
            id_opl="OPL-E3",
            exp_requerida=4,
            exp_op1=3,
            exp_op2=2,
            t_op1=20.0,
            t_op2=5.0,
        )

        datos = cargar_datos_problema(session, ["OPL-E3"])
        resultado = resolver(datos, Configuracion(nivel_eficiencia=100))

        assert resultado.estado in {"OPTIMA", "FACTIBLE"}
        assert resultado.asignaciones["OPL-E3"] == "OP1"
