"""
Tests para el módulo loader.py (cargar_datos_problema).
"""

import pytest
from datetime import date
from src.optimization.cargador_problema import cargar_datos_problema

LUNES = date(2025, 1, 6)


class TestCargarDatosProblema:

    def test_dimensiones(self, base_data):
        datos = cargar_datos_problema(base_data, ["OPL-001"])
        assert datos.n_opls == 1
        assert datos.n_operarios == 2

    def test_ids_opls(self, base_data):
        datos = cargar_datos_problema(base_data, ["OPL-001"])
        assert datos.ids_opls == ["OPL-001"]

    def test_capacidades_en_minutos(self, base_data):
        # Los 2 operarios tienen 40h/semana = 2400 min cada uno
        datos = cargar_datos_problema(base_data, ["OPL-001"])
        assert datos.capacidades == [2400, 2400]

    def test_tiempos_articulo_valores_correctos(self, base_data):
        """tiempos_articulo[i] = cantidad * tiempo_estandar, igual para todos los operarios."""
        datos = cargar_datos_problema(base_data, ["OPL-001"])
        # ART-001: tiempo_estandar=30.0, cantidad=10 → 10 * 30 = 300 min
        assert datos.tiempos_articulo[0] == 300

    def test_tiempos_articulo_usa_tiempo_estandar(self, session):
        """tiempos_articulo usa siempre el tiempo_estandar del artículo, no el del operario."""
        from src.database.schema import Familia, Articulo, Operario, Operario_Familia, OPL
        session.add(Familia(descripcion="F", experiencia_requerida=1))
        session.add(Articulo(
            referencia="ART-X", familia="F",
            descripcion="test", peso=1.0, tiempo_estandar=20.0
        ))
        session.add(Operario(dni="11111111A", nombre_completo="Sin Skills", horas_semanales=40.0))
        session.add(Operario_Familia(dni_operario="11111111A", familia="F", experiencia=1))
        session.add(OPL(id="OPL-X", ref_articulo="ART-X", cantidad=5))
        session.commit()

        datos = cargar_datos_problema(session, ["OPL-X"])
        # tiempo = 5 * 20.0 = 100
        assert datos.tiempos_articulo[0] == 100

    def test_cualificados_con_experiencia_suficiente(self, base_data):
        """Par (i, j) en cualificados si exp >= exp_requerida."""
        datos = cargar_datos_problema(base_data, ["OPL-001"])
        # Ambos operarios tienen exp=2, familia require=1 -> cualificados
        idx_op1 = datos.dnis_operarios.index("12345678A")
        idx_op2 = datos.dnis_operarios.index("87654321B")
        assert (0, idx_op1) in datos.cualificados
        assert (0, idx_op2) in datos.cualificados

    def test_sin_operario_familia_usa_experiencia_minima(self, session):
        """Sin Operario_Familia, el par es asignable con experiencia=1 y no entra en cualificados."""
        from src.database.schema import Familia, Articulo, Operario, OPL
        session.add(Familia(descripcion="F", experiencia_requerida=1))
        session.add(Articulo(
            referencia="ART-Y", familia="F",
            descripcion="test", peso=1.0, tiempo_estandar=10.0
        ))
        session.add(Operario(dni="22222222B", nombre_completo="Sin Familia", horas_semanales=40.0))
        session.add(OPL(id="OPL-Y", ref_articulo="ART-Y", cantidad=1))
        session.commit()

        datos = cargar_datos_problema(session, ["OPL-Y"])
        assert datos.experiencias[(0, 0)] == 1
        assert (0, 0) not in datos.cualificados

    def test_operario_articulo_sin_operario_familia_es_asignable_no_cualificado(self, session):
        """Sin Operario_Familia el par es asignable (exp=1) y no entra en cualificados; Operario_Articulo sigue aplicando al tiempo."""
        from src.database.schema import Familia, Articulo, Operario, Operario_Articulo, OPL
        session.add(Familia(descripcion="F", experiencia_requerida=1))
        session.add(Articulo(
            referencia="ART-AF", familia="F",
            descripcion="test", peso=1.0, tiempo_estandar=10.0
        ))
        session.add(Operario(dni="55555555E", nombre_completo="Solo Articulo", horas_semanales=40.0))
        session.add(Operario_Articulo(ref_articulo="ART-AF", dni_operario="55555555E", tiempo_estimado=8.0))
        session.add(OPL(id="OPL-AF", ref_articulo="ART-AF", cantidad=1))
        session.commit()

        datos = cargar_datos_problema(session, ["OPL-AF"])
        assert datos.experiencias[(0, 0)] == 1
        assert (0, 0) not in datos.cualificados
        assert datos.tiempos_operario[(0, 0)] == 8

    def test_tiempo_operario_mayor_que_estandar_se_conserva(self, session):
        """Si tiempo_estimado operario > estándar, se conserva en tiempos_operario (la persistencia no filtra)."""
        from src.database.schema import Familia, Articulo, Operario, Operario_Familia, Operario_Articulo, OPL
        session.add(Familia(descripcion="F", experiencia_requerida=1))
        session.add(Articulo(
            referencia="ART-T", familia="F",
            descripcion="test", peso=1.0, tiempo_estandar=10.0
        ))
        session.add(Operario(dni="44444444D", nombre_completo="Dato Erroneo", horas_semanales=40.0))
        session.add(Operario_Familia(dni_operario="44444444D", familia="F", experiencia=3))
        session.add(Operario_Articulo(ref_articulo="ART-T", dni_operario="44444444D", tiempo_estimado=15.0))
        session.add(OPL(id="OPL-T", ref_articulo="ART-T", cantidad=2))
        session.commit()

        datos = cargar_datos_problema(session, ["OPL-T"])
        # Estándar: 2 * 10 = 20. El tiempo de operario (30) ahora se conserva.
        assert datos.tiempos_articulo[0] == 20
        assert datos.tiempos_operario[(0, 0)] == 30

    def test_cualificados_excluye_exp_insuficiente(self, session):
        """Operario con exp < exp_requerida NO está en cualificados."""
        from src.database.schema import Familia, Articulo, Operario, Operario_Familia, Operario_Articulo, OPL
        session.add(Familia(descripcion="F", experiencia_requerida=3))
        session.add(Articulo(
            referencia="ART-Z", familia="F",
            descripcion="test", peso=1.0, tiempo_estandar=10.0
        ))
        session.add(Operario(dni="33333333C", nombre_completo="Poca Exp", horas_semanales=40.0))
        session.add(Operario_Familia(dni_operario="33333333C", familia="F", experiencia=2))
        session.add(Operario_Articulo(ref_articulo="ART-Z", dni_operario="33333333C", tiempo_estimado=15.0))
        session.add(OPL(id="OPL-Z", ref_articulo="ART-Z", cantidad=1))
        session.commit()

        datos = cargar_datos_problema(session, ["OPL-Z"])
        assert (0, 0) in datos.experiencias     # puede trabajar
        assert (0, 0) not in datos.cualificados  # no es optimo

    def test_familia_experiencia_1_considera_optimo_exp_1_o_mayor(self, session):
        """Si la familia requiere 1, exp=1 y exp=4 son cualificados."""
        from src.database.schema import Familia, Articulo, Operario, Operario_Familia, OPL
        session.add(Familia(descripcion="F1", experiencia_requerida=1))
        session.add(Articulo(
            referencia="ART-F1", familia="F1",
            descripcion="test", peso=1.0, tiempo_estandar=10.0
        ))
        session.add(Operario(dni="OP-F1A", nombre_completo="Exp 1", horas_semanales=40.0))
        session.add(Operario(dni="OP-F1B", nombre_completo="Exp 4", horas_semanales=40.0))
        session.add(Operario_Familia(dni_operario="OP-F1A", familia="F1", experiencia=1))
        session.add(Operario_Familia(dni_operario="OP-F1B", familia="F1", experiencia=4))
        session.add(OPL(id="OPL-F1", ref_articulo="ART-F1", cantidad=1))
        session.commit()

        datos = cargar_datos_problema(session, ["OPL-F1"])
        j_a = datos.dnis_operarios.index("OP-F1A")
        j_b = datos.dnis_operarios.index("OP-F1B")
        assert (0, j_a) in datos.cualificados
        assert (0, j_b) in datos.cualificados

    def test_familia_experiencia_4_solo_considera_optimo_exp_4(self, session):
        """Si la familia requiere 4, exp=3 no cualifica y exp=4 sí cualifica."""
        from src.database.schema import Familia, Articulo, Operario, Operario_Familia, OPL
        session.add(Familia(descripcion="F4", experiencia_requerida=4))
        session.add(Articulo(
            referencia="ART-F4", familia="F4",
            descripcion="test", peso=1.0, tiempo_estandar=10.0
        ))
        session.add(Operario(dni="OP-F4A", nombre_completo="Exp 3", horas_semanales=40.0))
        session.add(Operario(dni="OP-F4B", nombre_completo="Exp 4", horas_semanales=40.0))
        session.add(Operario_Familia(dni_operario="OP-F4A", familia="F4", experiencia=3))
        session.add(Operario_Familia(dni_operario="OP-F4B", familia="F4", experiencia=4))
        session.add(OPL(id="OPL-F4", ref_articulo="ART-F4", cantidad=1))
        session.commit()

        datos = cargar_datos_problema(session, ["OPL-F4"])
        j_a = datos.dnis_operarios.index("OP-F4A")
        j_b = datos.dnis_operarios.index("OP-F4B")
        assert (0, j_a) not in datos.cualificados
        assert (0, j_b) in datos.cualificados

    def test_cantidades(self, base_data):
        datos = cargar_datos_problema(base_data, ["OPL-001"])
        assert datos.cantidades == [10]

    def test_lista_vacia_devuelve_problema_vacio(self, base_data):
        datos = cargar_datos_problema(base_data, [])
        assert datos.n_opls == 0

    def test_obligatorias_vacias_sin_semana(self, base_data):
        """Sin semana, no se cargan obligatorias."""
        datos = cargar_datos_problema(base_data, ["OPL-001"])
        assert datos.obligatorias == set()

    def test_obligatorias_cargadas_con_semana(self, session):
        """Con semana, las filas obligatorias se añaden como OPLs extra."""
        from src.database.schema import Familia, Articulo, Operario, OPL, AsignacionOPL, Reparto, TipoAsignacion
        session.add(Familia(descripcion="F", experiencia_requerida=1))
        session.add(Articulo(
            referencia="ART-OB", familia="F",
            descripcion="test", peso=1.0, tiempo_estandar=10.0
        ))
        session.add(Operario(dni="OP-OB", nombre_completo="Op Obligatoria", horas_semanales=40.0))
        session.add(OPL(id="OPL-OB", ref_articulo="ART-OB", cantidad=1))
        session.add(Reparto(semana=LUNES, aprobado=False))
        session.add(AsignacionOPL(
            id_opl="OPL-OB", semana=LUNES,
            dni_operario=None, tipo_asignacion=TipoAsignacion.OBLIGATORIA,
            es_fija=False,
            tiempo_planificado=10.0, tiempo_estimado_operario=None,
            tiempo_total_teorico=10.0,
        ))
        session.commit()

        datos = cargar_datos_problema(session, [], LUNES)
        assert datos.n_opls == 1
        assert datos.ids_opls == ["OPL-OB"]
        assert 0 in datos.obligatorias

    def test_fija_con_operario_descuenta_capacidad(self, session):
        """Una asignación es_fija=True con operario reduce la capacidad disponible."""
        from src.database.schema import (
            Familia, Articulo, Operario, Operario_Articulo, OPL, AsignacionOPL, Reparto, TipoAsignacion
        )
        session.add(Familia(descripcion="F", experiencia_requerida=1))
        session.add(Articulo(
            referencia="ART-FC", familia="F",
            descripcion="test", peso=1.0, tiempo_estandar=10.0
        ))
        op = Operario(dni="OP-FC", nombre_completo="Op Fija", horas_semanales=40.0)
        session.add(op)
        session.add(Operario_Articulo(ref_articulo="ART-FC", dni_operario="OP-FC", tiempo_estimado=10.0))
        session.add(OPL(id="OPL-FC", ref_articulo="ART-FC", cantidad=1))
        session.add(Reparto(semana=LUNES, aprobado=False))
        session.add(AsignacionOPL(
            id_opl="OPL-FC", semana=LUNES,
            dni_operario="OP-FC", tipo_asignacion=TipoAsignacion.ARRASTRE,
            es_fija=True,
            tiempo_planificado=100.0, tiempo_estimado_operario=10.0,
            tiempo_total_teorico=10.0,
        ))
        session.commit()

        datos = cargar_datos_problema(session, [], LUNES)
        # Capacidad base: 40*60=2400; menos 100 del arrastre fijo
        idx = datos.dnis_operarios.index("OP-FC")
        assert datos.capacidades[idx] == 2300

    def test_operarios_con_horas_cero_no_entran_en_reparto(self, session):
        """Operarios con 0h se guardan en BD pero no se incluyen en el problema semanal."""
        from src.database.schema import Familia, Articulo, Operario, Operario_Familia, OPL
        session.add(Familia(descripcion="F", experiencia_requerida=1))
        session.add(Articulo(
            referencia="ART-0H", familia="F",
            descripcion="test", peso=1.0, tiempo_estandar=10.0
        ))
        session.add(Operario(dni="OP-0H", nombre_completo="No Disponible", horas_semanales=0.0))
        session.add(Operario_Familia(dni_operario="OP-0H", familia="F", experiencia=3))
        session.add(OPL(id="OPL-0H", ref_articulo="ART-0H", cantidad=1))
        session.commit()

        datos = cargar_datos_problema(session, ["OPL-0H"])
        assert datos.n_operarios == 0
        assert datos.dnis_operarios == []
        assert datos.capacidades == []
