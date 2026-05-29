"""
Tests para services.planificacion.asignaciones.
"""

from datetime import date

import pytest
from sqlalchemy import select

from src.database.schema import Articulo, AsignacionOPL, OPL, Operario, Operario_Articulo, Reparto, TipoAsignacion
from src.exceptions import ConflictError, DomainValidationError, NotFoundError
from src.services.planificacion import asignaciones as asignacion_opl_service


SEMANA_1 = date(2025, 2, 3)
DNI_OP1 = "12345678A"
DNI_OP2 = "87654321B"
OPL_ID = "OPL-001"


def _crear_asignacion(
    session,
    *,
    id_opl: str,
    semana: date,
    dni_operario: str | None,
    tipo: TipoAsignacion,
    tiempo_planificado: float,
    tiempo_estimado_operario: float | None,
    tiempo_total_teorico: float,
    es_fija: bool = False,
) -> AsignacionOPL:
    fila = AsignacionOPL(
        id_opl=id_opl,
        semana=semana,
        dni_operario=dni_operario,
        tipo_asignacion=tipo,
        es_fija=es_fija,
        tiempo_planificado=tiempo_planificado,
        tiempo_estimado_operario=tiempo_estimado_operario,
        tiempo_total_teorico=tiempo_total_teorico,
    )
    session.add(fila)
    session.commit()
    return fila


class TestRead:

    def test_read_opl_assignments_empty(self, base_data):
        result = asignacion_opl_service.leer_asignaciones_opl(base_data, OPL_ID)
        assert result == []

    def test_read_assignment_not_found(self, base_data):
        result = asignacion_opl_service.leer_asignacion(base_data, OPL_ID, SEMANA_1)
        assert result is None

    def test_read_week_assignments_empty(self, base_data):
        result = asignacion_opl_service.leer_asignaciones_semana(base_data, SEMANA_1)
        assert result == []

    def test_read_assignments_by_type(self, base_data):
        base_data.add(Reparto(semana=SEMANA_1, aprobado=False))
        _crear_asignacion(
            base_data,
            id_opl=OPL_ID,
            semana=SEMANA_1,
            dni_operario=DNI_OP1,
            tipo=TipoAsignacion.ARRASTRE,
            tiempo_planificado=100.0,
            tiempo_estimado_operario=250.0,
            tiempo_total_teorico=300.0,
        )

        arrastres = asignacion_opl_service.leer_asignaciones_por_tipo(base_data, SEMANA_1, TipoAsignacion.ARRASTRE)
        assert len(arrastres) == 1


class TestUpdate:

    def test_update_worker(self, base_data):
        base_data.add(Reparto(semana=SEMANA_1, aprobado=False))
        _crear_asignacion(
            base_data,
            id_opl=OPL_ID,
            semana=SEMANA_1,
            dni_operario=DNI_OP1,
            tipo=TipoAsignacion.NORMAL,
            tiempo_planificado=250.0,
            tiempo_estimado_operario=250.0,
            tiempo_total_teorico=300.0,
        )

        asignacion_opl_service.actualizar_operario_asignacion(base_data, OPL_ID, SEMANA_1, DNI_OP2)
        a = asignacion_opl_service.leer_asignacion(base_data, OPL_ID, SEMANA_1)
        assert a.dni_operario == DNI_OP2
        assert a.tiempo_estimado_operario == 300.0
        assert a.peso_aportado == 10.0
        assert a.n_articulos_aportados == 10.0

    def test_update_worker_not_found_raises_error(self, base_data):
        base_data.add(Reparto(semana=SEMANA_1, aprobado=False))
        _crear_asignacion(
            base_data,
            id_opl=OPL_ID,
            semana=SEMANA_1,
            dni_operario=DNI_OP1,
            tipo=TipoAsignacion.NORMAL,
            tiempo_planificado=250.0,
            tiempo_estimado_operario=250.0,
            tiempo_total_teorico=300.0,
        )

        with pytest.raises(NotFoundError, match="operario"):
            asignacion_opl_service.actualizar_operario_asignacion(base_data, OPL_ID, SEMANA_1, "NODNIX")

    def test_update_worker_zero_hours_raises_error(self, base_data):
        base_data.add(Reparto(semana=SEMANA_1, aprobado=False))
        _crear_asignacion(
            base_data,
            id_opl=OPL_ID,
            semana=SEMANA_1,
            dni_operario=DNI_OP1,
            tipo=TipoAsignacion.NORMAL,
            tiempo_planificado=250.0,
            tiempo_estimado_operario=250.0,
            tiempo_total_teorico=300.0,
        )

        op2 = base_data.get(Operario, DNI_OP2)
        op2.horas_semanales = 0.0
        base_data.commit()

        with pytest.raises(DomainValidationError, match="no está activo"):
            asignacion_opl_service.actualizar_operario_asignacion(base_data, OPL_ID, SEMANA_1, DNI_OP2)

    def test_update_assignment_not_found_raises_error(self, base_data):
        with pytest.raises(NotFoundError, match="OPL-001"):
            asignacion_opl_service.actualizar_operario_asignacion(base_data, OPL_ID, SEMANA_1, DNI_OP1)

    def test_update_worker_uses_operario_articulo_when_valid(self, base_data):
        """Al reasignar, planifica en estándar y conserva estimado específico de operario."""
        base_data.add(Reparto(semana=SEMANA_1, aprobado=False))
        _crear_asignacion(
            base_data,
            id_opl=OPL_ID,
            semana=SEMANA_1,
            dni_operario=DNI_OP2,
            tipo=TipoAsignacion.NORMAL,
            tiempo_planificado=300.0,
            tiempo_estimado_operario=300.0,
            tiempo_total_teorico=300.0,
        )
        # DNI_OP1 tiene Operario_Articulo.tiempo_estimado=25 (<tiempo_estandar=30).
        # Debe consumir 10*30=300 en planificado (capacidad estándar)
        # y guardar 10*25=250 como tiempo estimado de operario.
        asignacion_opl_service.actualizar_operario_asignacion(base_data, OPL_ID, SEMANA_1, DNI_OP1)
        a = asignacion_opl_service.leer_asignacion(base_data, OPL_ID, SEMANA_1)
        assert a.dni_operario == DNI_OP1
        assert a.tiempo_planificado == 300.0
        assert a.tiempo_estimado_operario == 250.0

    def test_unassign_sets_operario_to_none_and_preserves_teorico(self, base_data):
        """Desasignar pone dni=None, tiempo_estimado=None, tiempo_planificado=teorico."""
        base_data.add(Reparto(semana=SEMANA_1, aprobado=False))
        _crear_asignacion(
            base_data,
            id_opl=OPL_ID,
            semana=SEMANA_1,
            dni_operario=DNI_OP1,
            tipo=TipoAsignacion.NORMAL,
            tiempo_planificado=250.0,
            tiempo_estimado_operario=250.0,
            tiempo_total_teorico=300.0,
        )

        asignacion_opl_service.actualizar_operario_asignacion(base_data, OPL_ID, SEMANA_1, None)
        a = asignacion_opl_service.leer_asignacion(base_data, OPL_ID, SEMANA_1)
        assert a.dni_operario is None
        assert a.tiempo_estimado_operario is None
        # tiempo_planificado debe conservar el valor teórico (no 0) para drag correcto
        assert a.tiempo_planificado == 300.0
        assert a.peso_aportado == 0.0
        assert a.n_articulos_aportados == 0.0

    def test_reassign_small_times_never_persists_zero_estimated_time(self, base_data):
        """Si los redondeos dan 0, la reasignación debe guardar al menos 1 min para cumplir CHECK."""
        base_data.add(Reparto(semana=SEMANA_1, aprobado=False))
        _crear_asignacion(
            base_data,
            id_opl=OPL_ID,
            semana=SEMANA_1,
            dni_operario=DNI_OP1,
            tipo=TipoAsignacion.NORMAL,
            tiempo_planificado=250.0,
            tiempo_estimado_operario=250.0,
            tiempo_total_teorico=300.0,
        )

        articulo = base_data.get(Articulo, "ART-001")
        articulo.tiempo_estandar = 0.01  # 10 * 0.01 = 0.1 -> round = 0
        oa_op2 = base_data.scalars(
            select(Operario_Articulo).where(
                Operario_Articulo.ref_articulo == "ART-001",
                Operario_Articulo.dni_operario == DNI_OP2,
            )
        ).first()
        oa_op2.tiempo_estimado = 0.01  # también redondea a 0 y debe ignorarse
        base_data.commit()

        asignacion_opl_service.actualizar_operario_asignacion(base_data, OPL_ID, SEMANA_1, DNI_OP2)
        a = asignacion_opl_service.leer_asignacion(base_data, OPL_ID, SEMANA_1)

        assert a.dni_operario == DNI_OP2
        assert a.tiempo_planificado >= 1.0
        assert a.tiempo_estimado_operario >= 1.0


class TestCapacityCheck:
    """Verificación de capacidad en asignación manual."""

    def test_asignar_supera_capacidad_lanza_error(self, base_data):
        """OPL que necesita más minutos de los disponibles → DomainValidationError, row sin cambio."""
        base_data.add(Reparto(semana=SEMANA_1, aprobado=False))
        # OP2 tiene 40h = 2400 min. OPL-HEAVY: 81 uds * 30 min/ud = 2430 min > 2400.
        base_data.add(OPL(id="OPL-HEAVY", ref_articulo="ART-001", cantidad=81))
        base_data.commit()
        _crear_asignacion(
            base_data,
            id_opl="OPL-HEAVY",
            semana=SEMANA_1,
            dni_operario=None,
            tipo=TipoAsignacion.NORMAL,
            tiempo_planificado=2430.0,
            tiempo_estimado_operario=None,
            tiempo_total_teorico=2430.0,
        )

        with pytest.raises(DomainValidationError, match="solo quedan"):
            asignacion_opl_service.actualizar_operario_asignacion(base_data, "OPL-HEAVY", SEMANA_1, DNI_OP2)

        a = asignacion_opl_service.leer_asignacion(base_data, "OPL-HEAVY", SEMANA_1)
        assert a.dni_operario is None

    def test_asignar_cabe_exacto_tiene_exito(self, base_data):
        """OPL que usa exactamente la capacidad disponible → éxito."""
        base_data.add(Reparto(semana=SEMANA_1, aprobado=False))
        # OP2: 2400 min. OPL-EXACT: 80 uds * 30 min/ud = 2400 min.
        base_data.add(OPL(id="OPL-EXACT", ref_articulo="ART-001", cantidad=80))
        base_data.commit()
        _crear_asignacion(
            base_data,
            id_opl="OPL-EXACT",
            semana=SEMANA_1,
            dni_operario=None,
            tipo=TipoAsignacion.NORMAL,
            tiempo_planificado=2400.0,
            tiempo_estimado_operario=None,
            tiempo_total_teorico=2400.0,
        )

        asignacion_opl_service.actualizar_operario_asignacion(base_data, "OPL-EXACT", SEMANA_1, DNI_OP2)
        a = asignacion_opl_service.leer_asignacion(base_data, "OPL-EXACT", SEMANA_1)
        assert a.dni_operario == DNI_OP2

    def test_toggle_es_fija_mismo_operario_no_comprueba_capacidad(self, base_data):
        """Toggle de es_fija con mismo operario no realiza check de capacidad."""
        base_data.add(Reparto(semana=SEMANA_1, aprobado=False))
        # Insertar fila con tiempo artificialmente enorme para simular operario sobrecargado.
        _crear_asignacion(
            base_data,
            id_opl=OPL_ID,
            semana=SEMANA_1,
            dni_operario=DNI_OP1,
            tipo=TipoAsignacion.NORMAL,
            tiempo_planificado=9999.0,
            tiempo_estimado_operario=9999.0,
            tiempo_total_teorico=9999.0,
        )

        # Solo cambiar es_fija → no debe fallar por capacidad.
        asignacion_opl_service.actualizar_operario_asignacion(
            base_data, OPL_ID, SEMANA_1, DNI_OP1, es_fija=True
        )
        a = asignacion_opl_service.leer_asignacion(base_data, OPL_ID, SEMANA_1)
        assert a.es_fija is True

    def test_desasignar_no_requiere_capacidad(self, base_data):
        """Desasignar (None) nunca lanza error de capacidad."""
        base_data.add(Reparto(semana=SEMANA_1, aprobado=False))
        _crear_asignacion(
            base_data,
            id_opl=OPL_ID,
            semana=SEMANA_1,
            dni_operario=DNI_OP1,
            tipo=TipoAsignacion.NORMAL,
            tiempo_planificado=250.0,
            tiempo_estimado_operario=250.0,
            tiempo_total_teorico=250.0,
        )

        asignacion_opl_service.actualizar_operario_asignacion(base_data, OPL_ID, SEMANA_1, None)
        a = asignacion_opl_service.leer_asignacion(base_data, OPL_ID, SEMANA_1)
        assert a.dni_operario is None


class TestInvalidaEstadosSolver:
    """Edición manual invalida los estados del solver en Reparto."""

    def test_edicion_manual_invalida_estados(self, base_data):
        """PATCH operario debe poner estado_base/eficiencia/equidad_* a None."""
        reparto = Reparto(
            semana=SEMANA_1,
            aprobado=False,
            estado_base="OPTIMA",
            estado_eficiencia="NO_EJECUTADA",
            estado_equidad_peso="NO_EJECUTADA",
            estado_equidad_articulos="NO_EJECUTADA",
        )
        base_data.add(reparto)
        _crear_asignacion(
            base_data,
            id_opl=OPL_ID,
            semana=SEMANA_1,
            dni_operario=DNI_OP1,
            tipo=TipoAsignacion.NORMAL,
            tiempo_planificado=250.0,
            tiempo_estimado_operario=250.0,
            tiempo_total_teorico=300.0,
        )

        asignacion_opl_service.actualizar_operario_asignacion(base_data, OPL_ID, SEMANA_1, DNI_OP2)

        base_data.refresh(reparto)
        assert reparto.estado_base is None
        assert reparto.estado_eficiencia is None
        assert reparto.estado_equidad_peso is None
        assert reparto.estado_equidad_articulos is None

    def test_arrastre_sigue_siendo_inmutable(self, base_data):
        """Filas ARRASTRE lanzan ConflictError antes de llegar al check de capacidad."""
        base_data.add(Reparto(semana=SEMANA_1, aprobado=False))
        _crear_asignacion(
            base_data,
            id_opl=OPL_ID,
            semana=SEMANA_1,
            dni_operario=DNI_OP1,
            tipo=TipoAsignacion.ARRASTRE,
            es_fija=True,
            tiempo_planificado=100.0,
            tiempo_estimado_operario=250.0,
            tiempo_total_teorico=300.0,
        )

        with pytest.raises(ConflictError, match="arrastre"):
            asignacion_opl_service.actualizar_operario_asignacion(base_data, OPL_ID, SEMANA_1, DNI_OP2)

    def test_opl_en_reparto_aprobado_es_inmutable(self, base_data):
        """Fila NORMAL en reparto aprobado lanza ConflictError vía reparto.aprobado."""
        base_data.add(Reparto(semana=SEMANA_1, aprobado=True))
        _crear_asignacion(
            base_data,
            id_opl=OPL_ID,
            semana=SEMANA_1,
            dni_operario=DNI_OP1,
            tipo=TipoAsignacion.NORMAL,
            es_fija=True,
            tiempo_planificado=200.0,
            tiempo_estimado_operario=300.0,
            tiempo_total_teorico=300.0,
        )

        with pytest.raises(ConflictError, match="aprobado"):
            asignacion_opl_service.actualizar_operario_asignacion(base_data, OPL_ID, SEMANA_1, DNI_OP2)


class TestCleanupNoFijas:

    def test_cleanup_only_removes_normal_and_obligatoria(self, base_data):
        base_data.add(Reparto(semana=SEMANA_1, aprobado=False))
        base_data.add(OPL(id="OPL-OBL", ref_articulo="ART-001", cantidad=3))
        base_data.add(OPL(id="OPL-FIJA", ref_articulo="ART-001", cantidad=4))
        base_data.commit()

        _crear_asignacion(
            base_data,
            id_opl=OPL_ID,
            semana=SEMANA_1,
            dni_operario=DNI_OP1,
            tipo=TipoAsignacion.NORMAL,
            tiempo_planificado=100.0,
            tiempo_estimado_operario=250.0,
            tiempo_total_teorico=300.0,
        )
        _crear_asignacion(
            base_data,
            id_opl="OPL-OBL",
            semana=SEMANA_1,
            dni_operario=None,
            tipo=TipoAsignacion.OBLIGATORIA,
            tiempo_planificado=90.0,
            tiempo_estimado_operario=None,
            tiempo_total_teorico=90.0,
        )
        _crear_asignacion(
            base_data,
            id_opl="OPL-FIJA",
            semana=SEMANA_1,
            dni_operario=DNI_OP2,
            tipo=TipoAsignacion.ARRASTRE,
            es_fija=True,
            tiempo_planificado=50.0,
            tiempo_estimado_operario=80.0,
            tiempo_total_teorico=120.0,
        )

        eliminadas = asignacion_opl_service.eliminar_asignaciones_no_fijas_semana(base_data, SEMANA_1)
        assert eliminadas == 2

        restantes = asignacion_opl_service.leer_asignaciones_semana(base_data, SEMANA_1)
        assert len(restantes) == 1
        assert restantes[0].tipo_asignacion == TipoAsignacion.ARRASTRE


