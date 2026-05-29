"""
Tests para services.planificacion.repartos_semanales.

Cubre: leer_reparto, aplicar_resultado y aprobar_reparto.

Flujo:
  datos = cargar_datos_problema(session, ids_opls_normales, semana)
  resultado = resolver(datos, config)
  aplicar_resultado(session, semana, datos, resultado)  ← crea el Reparto
  aprobar_reparto(session, semana, semana_destino)      ← genera fijas en semana destino
"""

from datetime import date, timedelta
import pytest

from src.services.planificacion import repartos_semanales as reparto_service
from src.services.planificacion import asignaciones as asignacion_opl_service
from src.exceptions import NotFoundError, DomainValidationError, ConflictError
from src.database.schema import AsignacionOPL, OPL, Operario_Articulo, Reparto, TipoAsignacion
from src.optimization.cargador_problema import cargar_datos_problema
from src.optimization.solver import resolver, Configuracion, ResultadoAsignacion

SEMANA = date(2025, 2, 3)   # lunes
SEMANA_SIG = SEMANA + timedelta(days=7)

DNI_OP1 = "12345678A"
DNI_OP2 = "87654321B"
OPL_ID = "OPL-001"


# ─────────────────────────────────────────────────────────────────────────────
# Lectura
# ─────────────────────────────────────────────────────────────────────────────

class TestReadWeeklyPlan:

    def test_read_weekly_plan_not_found(self, base_data):
        assert reparto_service.leer_reparto(base_data, SEMANA) is None

    def test_read_existing_weekly_plan(self, base_data):
        base_data.add(Reparto(semana=SEMANA, aprobado=False))
        base_data.commit()
        r = reparto_service.leer_reparto(base_data, SEMANA)
        assert r is not None
        assert r.semana == SEMANA


# ─────────────────────────────────────────────────────────────────────────────
# Aplicar resultado
# ─────────────────────────────────────────────────────────────────────────────

class TestApplyResult:

    def test_creates_weekly_plan_automatically(self, base_data):
        """aplicar_resultado crea el Reparto si no existe."""
        datos = cargar_datos_problema(base_data, [OPL_ID])
        resultado = resolver(datos, Configuracion())
        reparto_service.aplicar_resultado(base_data, SEMANA, datos, resultado)

        r = reparto_service.leer_reparto(base_data, SEMANA)
        assert r is not None
        assert r.aprobado is False

    def test_applies_regular_assignment(self, base_data):
        """Tras aplicar resultado, la OPL aparece asignada en BD."""
        datos = cargar_datos_problema(base_data, [OPL_ID])
        resultado = resolver(datos, Configuracion())
        reparto_service.aplicar_resultado(base_data, SEMANA, datos, resultado)

        a = asignacion_opl_service.leer_asignacion(base_data, OPL_ID, SEMANA)
        assert a is not None
        assert a.tipo_asignacion == TipoAsignacion.NORMAL
        assert a.dni_operario in [DNI_OP1, DNI_OP2]

    def test_cleans_previous_non_fixed_assignments(self, base_data):
        """Re-aplicar resultado elimina el resultado anterior (no los bloqueados)."""
        datos = cargar_datos_problema(base_data, [OPL_ID])
        resultado = resolver(datos, Configuracion())

        reparto_service.aplicar_resultado(base_data, SEMANA, datos, resultado)
        reparto_service.aplicar_resultado(base_data, SEMANA, datos, resultado)

        # Sólo debe quedar 1 fila no-fija (no duplicados)
        todas = asignacion_opl_service.leer_asignaciones_semana(base_data, SEMANA)
        no_bloqueadas = [a for a in todas if not a.es_fija]
        assert len(no_bloqueadas) == 1

    def test_applies_mandatory_assignment_filling_worker(self, base_data):
        """Para OPLs obligatorias, se rellena el operario en la fila fija existente."""
        # Crear fila obligatoria (stub fija=True, obligatoria=True, dni=None) para SEMANA
        base_data.add(Reparto(semana=SEMANA, aprobado=False))
        base_data.add(AsignacionOPL(
            id_opl=OPL_ID, semana=SEMANA,
            dni_operario=None, tipo_asignacion=TipoAsignacion.OBLIGATORIA,
            tiempo_planificado=250.0, tiempo_estimado_operario=None,
            tiempo_total_teorico=300.0,
        ))
        base_data.commit()

        datos = cargar_datos_problema(base_data, [], SEMANA)
        resultado = resolver(datos, Configuracion())
        assert resultado.estado == "OPTIMA"

        reparto_service.aplicar_resultado(base_data, SEMANA, datos, resultado)

        a = asignacion_opl_service.leer_asignacion(base_data, OPL_ID, SEMANA)
        assert a.tipo_asignacion == TipoAsignacion.OBLIGATORIA  # sigue siendo obligatoria
        assert a.dni_operario is not None             # y tiene operario
        assert a.tiempo_estimado_operario is not None

    def test_apply_result_skips_ids_already_fixed_same_week(self, base_data):
        """Si una OPL ya está bloqueada en la semana, aplicar_resultado no debe duplicarla."""
        base_data.add(Reparto(semana=SEMANA, aprobado=False))
        base_data.add(AsignacionOPL(
            id_opl=OPL_ID,
            semana=SEMANA,
            dni_operario=DNI_OP1,
            tipo_asignacion=TipoAsignacion.ARRASTRE,
            es_fija=True,
            tiempo_planificado=250.0,
            tiempo_estimado_operario=250.0,
            tiempo_total_teorico=300.0,
        ))
        base_data.commit()

        datos = cargar_datos_problema(base_data, [OPL_ID], SEMANA)
        resultado = resolver(datos, Configuracion())

        reparto_service.aplicar_resultado(base_data, SEMANA, datos, resultado)

        filas_semana = asignacion_opl_service.leer_asignaciones_semana(base_data, SEMANA)
        filas_opl = [a for a in filas_semana if a.id_opl == OPL_ID]

        assert len(filas_opl) == 1
        assert filas_opl[0].tipo_asignacion == TipoAsignacion.ARRASTRE

    def test_unassigned_creates_placeholder(self, base_data):
        """OPL normal no asignada genera fila placeholder fija=False, dni=None."""
        resultado_sin_asignar = ResultadoAsignacion(
            estado="OPTIMA",
            estado_base="OPTIMA",
            estado_eficiencia="NO_EJECUTADA",
            estado_equidad_peso="NO_EJECUTADA",
            estado_equidad_articulos="NO_EJECUTADA",
            asignaciones={},
            tiempos_asignados={},
            no_asignadas=[OPL_ID],
            cargas={},
        )
        datos = cargar_datos_problema(base_data, [OPL_ID])
        reparto_service.aplicar_resultado(base_data, SEMANA, datos, resultado_sin_asignar)

        a = asignacion_opl_service.leer_asignacion(base_data, OPL_ID, SEMANA)
        assert a is not None
        assert a.tipo_asignacion == TipoAsignacion.NORMAL
        assert a.dni_operario is None

    def test_does_not_apply_when_infeasible(self, base_data):
        """Si el resultado es INFACTIBLE no se crea ninguna asignacion ni Reparto."""
        resultado_falso = ResultadoAsignacion(
            estado="INFACTIBLE",
            estado_base="INFACTIBLE",
            estado_eficiencia="NO_EJECUTADA",
            estado_equidad_peso="NO_EJECUTADA",
            estado_equidad_articulos="NO_EJECUTADA",
            asignaciones={}, tiempos_asignados={},
            no_asignadas=[], cargas={},
        )
        datos = cargar_datos_problema(base_data, [OPL_ID])
        reparto_service.aplicar_resultado(base_data, SEMANA, datos, resultado_falso)

        assert asignacion_opl_service.leer_asignacion(base_data, OPL_ID, SEMANA) is None
        assert reparto_service.leer_reparto(base_data, SEMANA) is None

    def test_approved_weekly_plan_raises_error(self, base_data):
        """No se puede re-aplicar resultado sobre un reparto ya aprobado."""
        # Crear y aprobar reparto manualmente
        base_data.add(Reparto(semana=SEMANA, aprobado=True))
        base_data.commit()

        datos = cargar_datos_problema(base_data, [OPL_ID])
        resultado = resolver(datos, Configuracion())
        with pytest.raises(ConflictError, match="aprobado"):
            reparto_service.aplicar_resultado(base_data, SEMANA, datos, resultado)

    def test_apply_result_uses_operario_time_when_available(self, base_data):
        """tiempo_estimado_operario debe usar tiempo de Operario_Articulo cuando es válido."""
        datos = cargar_datos_problema(base_data, [OPL_ID])
        resultado = ResultadoAsignacion(
            estado="OPTIMA",
            estado_base="OPTIMA",
            estado_eficiencia="NO_EJECUTADA",
            estado_equidad_peso="NO_EJECUTADA",
            estado_equidad_articulos="NO_EJECUTADA",
            asignaciones={OPL_ID: DNI_OP1},
            tiempos_asignados={OPL_ID: 200},
            no_asignadas=[],
            cargas={DNI_OP1: 200},
        )

        reparto_service.aplicar_resultado(base_data, SEMANA, datos, resultado)

        a = asignacion_opl_service.leer_asignacion(base_data, OPL_ID, SEMANA)
        assert a is not None
        assert a.dni_operario == DNI_OP1
        assert a.tiempo_estimado_operario == 250.0

    def test_apply_result_falls_back_to_standard_when_operario_time_missing(self, base_data):
        """Sin Operario_Articulo válido, tiempo_estimado_operario usa estándar de artículo."""
        datos = cargar_datos_problema(base_data, [OPL_ID])
        resultado = ResultadoAsignacion(
            estado="OPTIMA",
            estado_base="OPTIMA",
            estado_eficiencia="NO_EJECUTADA",
            estado_equidad_peso="NO_EJECUTADA",
            estado_equidad_articulos="NO_EJECUTADA",
            asignaciones={OPL_ID: DNI_OP2},
            tiempos_asignados={OPL_ID: 200},
            no_asignadas=[],
            cargas={DNI_OP2: 200},
        )

        reparto_service.aplicar_resultado(base_data, SEMANA, datos, resultado)

        a = asignacion_opl_service.leer_asignacion(base_data, OPL_ID, SEMANA)
        assert a is not None
        assert a.dni_operario == DNI_OP2
        assert a.tiempo_estimado_operario == 300.0


# ─────────────────────────────────────────────────────────────────────────────
# Aprobación
# ─────────────────────────────────────────────────────────────────────────────

class TestApproveWeeklyPlan:

    def test_approve_weekly_plan_marks_approved(self, base_data):
        """aprobar_reparto marca el Reparto como aprobado."""
        datos = cargar_datos_problema(base_data, [OPL_ID])
        resultado = resolver(datos, Configuracion())
        reparto_service.aplicar_resultado(base_data, SEMANA, datos, resultado)

        r = reparto_service.aprobar_reparto(base_data, SEMANA, semana_destino=SEMANA_SIG)
        assert r.aprobado is True
        assert r.fecha_aprobacion is not None

    def test_does_not_generate_fixed_for_complete_opl(self, base_data):
        """OPL completada al 100% esta semana → no genera fija la semana siguiente."""
        base_data.add(Reparto(semana=SEMANA, aprobado=False))
        base_data.add(AsignacionOPL(
            id_opl=OPL_ID, semana=SEMANA,
            dni_operario=DNI_OP1, tipo_asignacion=TipoAsignacion.NORMAL,
            tiempo_planificado=300.0, tiempo_estimado_operario=300.0,
            tiempo_total_teorico=300.0,
        ))
        base_data.commit()
        reparto_service.aprobar_reparto(base_data, SEMANA, semana_destino=SEMANA_SIG)

        fila_sig = asignacion_opl_service.leer_asignacion(base_data, OPL_ID, SEMANA_SIG)
        assert fila_sig is None

    def test_generates_arrastre_with_worker_for_split(self, base_data):
        """OPL asignada parcialmente → ARRASTRE CON operario la semana siguiente."""
        base_data.add(Reparto(semana=SEMANA, aprobado=False))
        # tiempo_planificado=200 < tiempo_total_teorico=300 → split restante=100
        base_data.add(AsignacionOPL(
            id_opl=OPL_ID, semana=SEMANA,
            dni_operario=DNI_OP1, tipo_asignacion=TipoAsignacion.NORMAL,
            tiempo_planificado=200.0, tiempo_estimado_operario=300.0,
            tiempo_total_teorico=300.0,
        ))
        base_data.commit()
        reparto_service.aprobar_reparto(base_data, SEMANA, semana_destino=SEMANA_SIG)

        fila_sig = asignacion_opl_service.leer_asignacion(base_data, OPL_ID, SEMANA_SIG)
        assert fila_sig is not None
        assert fila_sig.tipo_asignacion == TipoAsignacion.ARRASTRE
        assert fila_sig.es_fija is True
        assert fila_sig.dni_operario == DNI_OP1
        assert abs(fila_sig.tiempo_planificado - 100.0) < 0.01  # 300 - 200

    def test_generates_arrastre_preserving_estimado_operario(self, base_data):
        """El ARRASTRE debe conservar tiempo_estimado_operario de origen (no el teórico estándar)."""
        base_data.add(Reparto(semana=SEMANA, aprobado=False))
        base_data.add(AsignacionOPL(
            id_opl=OPL_ID,
            semana=SEMANA,
            dni_operario=DNI_OP1,
            tipo_asignacion=TipoAsignacion.NORMAL,
            tiempo_planificado=200.0,
            tiempo_estimado_operario=250.0,
            tiempo_total_teorico=300.0,
        ))
        base_data.commit()

        reparto_service.aprobar_reparto(base_data, SEMANA, semana_destino=SEMANA_SIG)

        fila_sig = asignacion_opl_service.leer_asignacion(base_data, OPL_ID, SEMANA_SIG)
        assert fila_sig is not None
        assert fila_sig.tipo_asignacion == TipoAsignacion.ARRASTRE
        assert fila_sig.tiempo_estimado_operario == 250.0

    def test_approve_with_existing_destination_week_updates_carryover(self, base_data):
        """Si el reparto destino existe y no está aprobado, se permite actualizar arrastre."""
        base_data.add(Reparto(semana=SEMANA, aprobado=False))
        base_data.add(Reparto(semana=SEMANA_SIG, aprobado=False))

        base_data.add(AsignacionOPL(
            id_opl=OPL_ID,
            semana=SEMANA,
            dni_operario=DNI_OP1,
            tipo_asignacion=TipoAsignacion.NORMAL,
            tiempo_planificado=200.0,
            tiempo_estimado_operario=300.0,
            tiempo_total_teorico=300.0,
        ))
        base_data.commit()

        r = reparto_service.aprobar_reparto(base_data, SEMANA, semana_destino=SEMANA_SIG)
        assert r.aprobado is True

        fila_sig = asignacion_opl_service.leer_asignacion(base_data, OPL_ID, SEMANA_SIG)
        assert fila_sig is not None
        assert fila_sig.tipo_asignacion == TipoAsignacion.ARRASTRE
        assert fila_sig.es_fija is True
        assert fila_sig.dni_operario == DNI_OP1
        assert abs(fila_sig.tiempo_planificado - 100.0) < 0.01

    def test_approve_allows_custom_destination_week(self, base_data):
        """Permite aprobar con arrastre a una semana destino distinta de semana+7."""
        semana_custom = SEMANA + timedelta(days=14)

        base_data.add(Reparto(semana=SEMANA, aprobado=False))
        base_data.add(AsignacionOPL(
            id_opl=OPL_ID,
            semana=SEMANA,
            dni_operario=DNI_OP1,
            tipo_asignacion=TipoAsignacion.NORMAL,
            tiempo_planificado=150.0,
            tiempo_estimado_operario=250.0,
            tiempo_total_teorico=300.0,
        ))
        base_data.commit()

        reparto_service.aprobar_reparto(base_data, SEMANA, semana_destino=semana_custom)

        fila_custom = asignacion_opl_service.leer_asignacion(base_data, OPL_ID, semana_custom)
        fila_sig = asignacion_opl_service.leer_asignacion(base_data, OPL_ID, SEMANA_SIG)
        assert fila_custom is not None
        assert fila_custom.tipo_asignacion == TipoAsignacion.ARRASTRE
        assert fila_custom.es_fija is True
        assert fila_sig is None

    def test_approve_split_uses_first_week_snapshot(self, base_data):
        """Evita fallo por redondeo cuando la semana 1 viene del solver en minutos enteros."""
        opl = base_data.get(OPL, OPL_ID)
        assert opl is not None

        # Forzamos un tiempo unitario decimal actual (total 366.2 para 10 uds)
        oa = base_data.get(Operario_Articulo, (opl.ref_articulo, DNI_OP1))
        oa.tiempo_estimado = 36.62
        base_data.commit()

        base_data.add(Reparto(semana=SEMANA, aprobado=False))
        base_data.add(AsignacionOPL(
            id_opl=OPL_ID,
            semana=SEMANA,
            dni_operario=DNI_OP1,
            tipo_asignacion=TipoAsignacion.NORMAL,
            tiempo_planificado=366.0,
            tiempo_estimado_operario=732.0,
            tiempo_total_teorico=732.0,
        ))
        base_data.commit()

        reparto_service.aprobar_reparto(base_data, SEMANA, semana_destino=SEMANA_SIG)
        fila_sig = asignacion_opl_service.leer_asignacion(base_data, OPL_ID, SEMANA_SIG)

        assert fila_sig is not None
        assert fila_sig.tipo_asignacion == TipoAsignacion.ARRASTRE
        assert fila_sig.es_fija is True
        assert fila_sig.dni_operario == DNI_OP1
        assert abs(fila_sig.tiempo_planificado - 366.0) < 0.01

    def test_normal_unassigned_deleted_on_approve(self, base_data):
        """OPL sin asignar se elimina en origen y se arrastra como OBLIGATORIA a la semana destino."""
        base_data.add(Reparto(semana=SEMANA, aprobado=False))
        base_data.add(AsignacionOPL(
            id_opl=OPL_ID, semana=SEMANA,
            dni_operario=None, tipo_asignacion=TipoAsignacion.NORMAL,
            tiempo_planificado=300.0, tiempo_estimado_operario=None,
            tiempo_total_teorico=300.0,
        ))
        base_data.commit()
        reparto_service.aprobar_reparto(base_data, SEMANA, semana_destino=SEMANA_SIG)

        # Placeholder NORMAL eliminado de la semana actual
        fila_actual = asignacion_opl_service.leer_asignacion(base_data, OPL_ID, SEMANA)
        assert fila_actual is None

        # Se crea OBLIGATORIA en semana siguiente
        fila_sig = asignacion_opl_service.leer_asignacion(base_data, OPL_ID, SEMANA_SIG)
        assert fila_sig is not None
        assert fila_sig.tipo_asignacion == TipoAsignacion.OBLIGATORIA
        assert fila_sig.es_fija is False
        assert fila_sig.dni_operario is None
        assert abs(fila_sig.tiempo_planificado - 300.0) < 0.01

    def test_normal_unassigned_deleted_no_next_week_carryover(self, base_data):
        """NORMAL sin asignar se borra al aprobar y aparece como OBLIGATORIA en la semana siguiente."""
        base_data.add(Reparto(semana=SEMANA, aprobado=False))
        base_data.add(AsignacionOPL(
            id_opl=OPL_ID,
            semana=SEMANA,
            dni_operario=None,
            tipo_asignacion=TipoAsignacion.NORMAL,
            tiempo_planificado=300.0,
            tiempo_estimado_operario=None,
            tiempo_total_teorico=300.0,
        ))
        base_data.commit()

        reparto_service.aprobar_reparto(base_data, SEMANA, semana_destino=SEMANA_SIG)

        # NORMAL eliminada de semana actual
        assert asignacion_opl_service.leer_asignacion(base_data, OPL_ID, SEMANA) is None
        # Aparece como OBLIGATORIA en semana siguiente y el loader la incluye.
        fila_sig = asignacion_opl_service.leer_asignacion(base_data, OPL_ID, SEMANA_SIG)
        assert fila_sig is not None
        assert fila_sig.tipo_asignacion == TipoAsignacion.OBLIGATORIA
        assert fila_sig.dni_operario is None

        datos_semana_sig = cargar_datos_problema(base_data, [], SEMANA_SIG)
        assert datos_semana_sig.n_opls == 1
        assert datos_semana_sig.ids_opls == [OPL_ID]
        assert 0 in datos_semana_sig.obligatorias

    def test_mandatory_complete_does_not_generate_carryover(self, base_data):
        """Una OPL obligatoria completada no genera arrastre a semana+1."""
        base_data.add(Reparto(semana=SEMANA, aprobado=False))
        base_data.add(AsignacionOPL(
            id_opl=OPL_ID,
            semana=SEMANA,
            dni_operario=DNI_OP1,
            tipo_asignacion=TipoAsignacion.OBLIGATORIA,
            tiempo_planificado=300.0,
            tiempo_estimado_operario=300.0,
            tiempo_total_teorico=300.0,
        ))
        base_data.commit()

        reparto_service.aprobar_reparto(base_data, SEMANA, semana_destino=SEMANA_SIG)
        fila_sig = asignacion_opl_service.leer_asignacion(base_data, OPL_ID, SEMANA_SIG)
        assert fila_sig is None

    def test_carryover_only_partials_when_excluding_unassigned(self, base_data):
        """Con arrastre y excluir no asignadas, solo se arrastran parciales."""
        base_data.add(Reparto(semana=SEMANA, aprobado=False))
        base_data.add(OPL(id="OPL-002", ref_articulo="ART-001", cantidad=4))
        base_data.add(AsignacionOPL(
            id_opl="OPL-002",
            semana=SEMANA,
            dni_operario=None,
            tipo_asignacion=TipoAsignacion.NORMAL,
            tiempo_planificado=0.0,
            tiempo_estimado_operario=None,
            tiempo_total_teorico=120.0,
        ))
        base_data.add(AsignacionOPL(
            id_opl=OPL_ID,
            semana=SEMANA,
            dni_operario=DNI_OP1,
            tipo_asignacion=TipoAsignacion.NORMAL,
            tiempo_planificado=200.0,
            tiempo_estimado_operario=300.0,
            tiempo_total_teorico=300.0,
        ))
        base_data.commit()

        reparto_service.aprobar_reparto(
            base_data,
            SEMANA,
            semana_destino=SEMANA_SIG,
            con_arrastre=True,
            incluir_no_asignadas_en_arrastre=False,
        )

        fila_sig_parcial = asignacion_opl_service.leer_asignacion(base_data, OPL_ID, SEMANA_SIG)
        fila_sig_no_asignada = asignacion_opl_service.leer_asignacion(base_data, "OPL-002", SEMANA_SIG)
        fila_origen_no_asignada = asignacion_opl_service.leer_asignacion(base_data, "OPL-002", SEMANA)

        assert fila_sig_parcial is not None
        assert fila_sig_parcial.tipo_asignacion == TipoAsignacion.ARRASTRE
        assert fila_sig_no_asignada is None
        assert fila_origen_no_asignada is None

    @pytest.mark.parametrize(
        "con_arrastre,incluir_no_asignadas",
        [
            (False, False),
            (True, False),
            (True, True),
        ],
    )
    def test_approve_without_obligatorias_allows_any_mode(self, base_data, con_arrastre, incluir_no_asignadas):
        """Sin obligatorias pendientes, aprobar funciona con cualquier combinacion."""
        base_data.add(Reparto(semana=SEMANA, aprobado=False))
        base_data.add(AsignacionOPL(
            id_opl=OPL_ID,
            semana=SEMANA,
            dni_operario=DNI_OP1,
            tipo_asignacion=TipoAsignacion.NORMAL,
            tiempo_planificado=300.0,
            tiempo_estimado_operario=300.0,
            tiempo_total_teorico=300.0,
        ))
        base_data.commit()

        reparto_service.aprobar_reparto(
            base_data,
            SEMANA,
            semana_destino=SEMANA_SIG,
            con_arrastre=con_arrastre,
            incluir_no_asignadas_en_arrastre=incluir_no_asignadas,
        )

        fila_sig = asignacion_opl_service.leer_asignacion(base_data, OPL_ID, SEMANA_SIG)
        assert fila_sig is None

    def test_approve_without_carryover_force_does_not_touch_destination(self, base_data):
        """Sin arrastre + forzado no debe tocar la semana destino."""
        base_data.add(Reparto(semana=SEMANA, aprobado=False))
        base_data.add(Reparto(semana=SEMANA_SIG, aprobado=False))

        # Semana origen con obligatoria inconsistente para forzar validación.
        base_data.add(AsignacionOPL(
            id_opl=OPL_ID,
            semana=SEMANA,
            dni_operario=None,
            tipo_asignacion=TipoAsignacion.OBLIGATORIA,
            tiempo_planificado=300.0,
            tiempo_estimado_operario=None,
            tiempo_total_teorico=300.0,
        ))

        # Semana destino con una fila (no debe limpiarse).
        base_data.add(AsignacionOPL(
            id_opl=OPL_ID,
            semana=SEMANA_SIG,
            dni_operario=None,
            tipo_asignacion=TipoAsignacion.NORMAL,
            tiempo_planificado=0.0,
            tiempo_estimado_operario=None,
            tiempo_total_teorico=120.0,
        ))
        base_data.commit()

        with pytest.raises(DomainValidationError):
            reparto_service.aprobar_reparto(base_data, SEMANA, semana_destino=None, con_arrastre=False)

        reparto, meta = reparto_service.aprobar_reparto(
            base_data,
            SEMANA,
            semana_destino=SEMANA_SIG,
            con_arrastre=False,
            forzar_obligatorias_pendientes=True,
            devolver_meta=True,
        )
        assert reparto.aprobado is True
        assert meta["modo_aprobacion"] == "sin_arrastre"
        assert meta["limpieza_aplicada"] is False

        assert asignacion_opl_service.leer_asignacion(base_data, OPL_ID, SEMANA) is None

        filas_destino = asignacion_opl_service.leer_asignaciones_semana(base_data, SEMANA_SIG)
        assert len(filas_destino) == 1

    def test_approve_with_carryover_blocks_when_validation_has_errors(self, base_data):
        """Con arrastre debe bloquear aprobación si hay errores de validación."""
        base_data.add(Reparto(semana=SEMANA, aprobado=False))
        base_data.add(AsignacionOPL(
            id_opl=OPL_ID,
            semana=SEMANA,
            dni_operario=None,
            tipo_asignacion=TipoAsignacion.OBLIGATORIA,
            tiempo_planificado=300.0,
            tiempo_estimado_operario=None,
            tiempo_total_teorico=300.0,
        ))
        base_data.commit()

        with pytest.raises(DomainValidationError, match="obligatoria"):
            reparto_service.aprobar_reparto(
                base_data,
                SEMANA,
                semana_destino=SEMANA_SIG,
                con_arrastre=True,
            )

    def test_force_without_carryover_does_not_reset_destination(self, base_data):
        """Sin arrastre + forzado no debe resetear asignaciones existentes."""
        base_data.add(Reparto(semana=SEMANA, aprobado=False))
        base_data.add(Reparto(semana=SEMANA_SIG, aprobado=False))

        # Error en origen para habilitar camino de forzado sin arrastre.
        base_data.add(AsignacionOPL(
            id_opl=OPL_ID,
            semana=SEMANA,
            dni_operario=None,
            tipo_asignacion=TipoAsignacion.OBLIGATORIA,
            tiempo_planificado=300.0,
            tiempo_estimado_operario=None,
            tiempo_total_teorico=300.0,
        ))

        base_data.add(OPL(id="OPL-002", ref_articulo="ART-001", cantidad=4))
        base_data.add(OPL(id="OPL-003", ref_articulo="ART-001", cantidad=4))
        base_data.add(OPL(id="OPL-004", ref_articulo="ART-001", cantidad=4))

        # ARRASTRE: debe conservarse tal cual
        base_data.add(AsignacionOPL(
            id_opl="OPL-002",
            semana=SEMANA_SIG,
            dni_operario=DNI_OP1,
            tipo_asignacion=TipoAsignacion.ARRASTRE,
            es_fija=True,
            tiempo_planificado=100.0,
            tiempo_estimado_operario=200.0,
            tiempo_total_teorico=240.0,
        ))
        # OBLIGATORIA: debe mantenerse tal cual
        base_data.add(AsignacionOPL(
            id_opl="OPL-003",
            semana=SEMANA_SIG,
            dni_operario=DNI_OP2,
            tipo_asignacion=TipoAsignacion.OBLIGATORIA,
            es_fija=False,
            tiempo_planificado=80.0,
            tiempo_estimado_operario=200.0,
            tiempo_total_teorico=240.0,
        ))
        # NORMAL: debe mantenerse tal cual
        base_data.add(AsignacionOPL(
            id_opl="OPL-004",
            semana=SEMANA_SIG,
            dni_operario=None,
            tipo_asignacion=TipoAsignacion.NORMAL,
            es_fija=False,
            tiempo_planificado=0.0,
            tiempo_estimado_operario=None,
            tiempo_total_teorico=240.0,
        ))
        base_data.commit()

        reparto_service.aprobar_reparto(
            base_data,
            SEMANA,
            semana_destino=SEMANA_SIG,
            con_arrastre=False,
            forzar_obligatorias_pendientes=True,
        )

        filas_destino = asignacion_opl_service.leer_asignaciones_semana(base_data, SEMANA_SIG)
        assert len(filas_destino) == 3
        ids = {f.id_opl for f in filas_destino}
        assert ids == {"OPL-002", "OPL-003", "OPL-004"}

        arrastre = next(f for f in filas_destino if f.id_opl == "OPL-002")
        assert arrastre.tipo_asignacion == TipoAsignacion.ARRASTRE
        assert arrastre.es_fija is True
        assert arrastre.dni_operario == DNI_OP1

        obligatoria = next(f for f in filas_destino if f.id_opl == "OPL-003")
        assert obligatoria.tipo_asignacion == TipoAsignacion.OBLIGATORIA
        assert obligatoria.es_fija is False
        assert obligatoria.dni_operario == DNI_OP2

    def test_next_week_uses_new_times_only_for_new_opls(self, base_data):
        """
        Si se aprueba una parcial y luego cambian tiempos de montaje,
        la fija de arrastre mantiene su snapshot antiguo y solo las nuevas OPL
        usan los tiempos actuales de BD.
        """
        base_data.add(Reparto(semana=SEMANA, aprobado=False))
        # Semana 1: parcial con snapshot antiguo (tiempo_estandar=30 min/ud -> total 300)
        base_data.add(AsignacionOPL(
            id_opl=OPL_ID,
            semana=SEMANA,
            dni_operario=DNI_OP1,
            tipo_asignacion=TipoAsignacion.NORMAL,
            tiempo_planificado=100.0,
            tiempo_estimado_operario=300.0,
            tiempo_total_teorico=300.0,
        ))
        base_data.commit()

        reparto_service.aprobar_reparto(base_data, SEMANA, semana_destino=SEMANA_SIG)

        # Arrastre a semana siguiente: restante = tiempo_total_teorico - tiempo_planificado = 300-100 = 200
        fija_sig = asignacion_opl_service.leer_asignacion(base_data, OPL_ID, SEMANA_SIG)
        assert fija_sig is not None
        assert fija_sig.tipo_asignacion == TipoAsignacion.ARRASTRE
        assert fija_sig.es_fija is True
        assert fija_sig.dni_operario == DNI_OP1
        assert abs(fija_sig.tiempo_planificado - 200.0) < 0.01
        assert abs(fija_sig.tiempo_estimado_operario - 300.0) < 0.01

        # Cambio de tiempo en BD antes de optimizar semana siguiente (20 min/ud -> total 200)
        opl = base_data.get(OPL, OPL_ID)
        oa = base_data.get(Operario_Articulo, (opl.ref_articulo, DNI_OP1))
        oa.tiempo_estimado = 20.0
        base_data.commit()

        # Nueva OPL que sí entra al algoritmo en semana siguiente
        base_data.add(OPL(id="OPL-002", ref_articulo=opl.ref_articulo, cantidad=10))
        base_data.commit()

        datos_semana_sig = cargar_datos_problema(base_data, ["OPL-002"], SEMANA_SIG)
        i_new = datos_semana_sig.ids_opls.index("OPL-002")
        j_op1 = datos_semana_sig.dnis_operarios.index(DNI_OP1)

        # La nueva OPL usa el tiempo actualizado de BD.
        assert datos_semana_sig.tiempos_operario.get((i_new, j_op1)) == 200

        resultado_semana_sig = resolver(datos_semana_sig, Configuracion())
        reparto_service.aplicar_resultado(base_data, SEMANA_SIG, datos_semana_sig, resultado_semana_sig)

        # El arrastre no se recalcula con tiempos nuevos; conserva snapshot antiguo.
        fija_sig_tras_opt = asignacion_opl_service.leer_asignacion(base_data, OPL_ID, SEMANA_SIG)
        assert fija_sig_tras_opt is not None
        assert fija_sig_tras_opt.tipo_asignacion == TipoAsignacion.ARRASTRE
        assert fija_sig_tras_opt.es_fija is True
        assert abs(fija_sig_tras_opt.tiempo_planificado - 200.0) < 0.01
        assert abs(fija_sig_tras_opt.tiempo_estimado_operario - 300.0) < 0.01

    def test_missing_weekly_plan_raises_error(self, base_data):
        with pytest.raises(NotFoundError, match="existe"):
            reparto_service.aprobar_reparto(base_data, SEMANA, semana_destino=SEMANA_SIG)

    def test_already_approved_raises_error(self, base_data):
        base_data.add(Reparto(semana=SEMANA, aprobado=False))
        base_data.add(AsignacionOPL(
            id_opl=OPL_ID, semana=SEMANA,
            dni_operario=DNI_OP1, tipo_asignacion=TipoAsignacion.NORMAL,
            tiempo_planificado=250.0, tiempo_estimado_operario=250.0,
            tiempo_total_teorico=300.0,
        ))
        base_data.commit()
        reparto_service.aprobar_reparto(base_data, SEMANA, semana_destino=SEMANA_SIG)
        with pytest.raises(ConflictError, match="aprobado"):
            reparto_service.aprobar_reparto(base_data, SEMANA, semana_destino=SEMANA_SIG)

    def test_without_applied_result_raises_error(self, base_data):
        """Aprobar sin haber aplicado resultado (no hay filas fija=False) lanza error."""
        base_data.add(Reparto(semana=SEMANA, aprobado=False))
        base_data.commit()
        with pytest.raises(DomainValidationError, match="asignaciones"):
            reparto_service.aprobar_reparto(base_data, SEMANA, semana_destino=SEMANA_SIG)


    def test_without_carryover_requires_destination_week(self, base_data):
        """Sin arrastre, semana_destino sigue siendo obligatoria."""
        base_data.add(Reparto(semana=SEMANA, aprobado=False))
        base_data.add(AsignacionOPL(
            id_opl=OPL_ID,
            semana=SEMANA,
            dni_operario=DNI_OP1,
            tipo_asignacion=TipoAsignacion.NORMAL,
            tiempo_planificado=250.0,
            tiempo_estimado_operario=250.0,
            tiempo_total_teorico=300.0,
        ))
        base_data.commit()

        with pytest.raises(DomainValidationError, match="Semana destino"):
            reparto_service.aprobar_reparto(
                base_data,
                SEMANA,
                semana_destino=None,
                con_arrastre=False,
                devolver_meta=True,
            )


    def test_with_carryover_requires_destination_week(self, base_data):
        """Con arrastre activo, semana_destino debe indicarse explícitamente."""
        base_data.add(Reparto(semana=SEMANA, aprobado=False))
        base_data.add(AsignacionOPL(
            id_opl=OPL_ID,
            semana=SEMANA,
            dni_operario=DNI_OP1,
            tipo_asignacion=TipoAsignacion.NORMAL,
            tiempo_planificado=150.0,
            tiempo_estimado_operario=250.0,
            tiempo_total_teorico=300.0,
        ))
        base_data.commit()

        with pytest.raises(DomainValidationError, match="Semana destino"):
            reparto_service.aprobar_reparto(base_data, SEMANA, semana_destino=None)

