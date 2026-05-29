"""Construye los DTOs ``RepartoResumenOut`` y ``RepartoDetalleOut``.

Consulta los datos necesarios en una sola query con joins
(ver :func:`crud.planificacion.asignaciones.leer_detalle_semana`).
"""

from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from src.api.schemas import AsignacionDetalleOut, RepartoDetalleOut, RepartoResumenOut
from src.crud.planificacion import asignaciones as asignaciones_crud, repartos as repartos_crud
from src.database.schema import Reparto, TipoAsignacion
from src.exceptions import NotFoundError


def construir_resumen(session: Session, reparto: Reparto) -> RepartoResumenOut:
    asigs = asignaciones_crud.listar_semana(session, reparto.semana)
    n_asignadas = sum(1 for a in asigs if a.dni_operario is not None)
    n_pendientes = sum(1 for a in asigs if a.dni_operario is None)
    return RepartoResumenOut(
        semana=reparto.semana,
        aprobado=reparto.aprobado,
        fecha_aprobacion=reparto.fecha_aprobacion,
        n_asignadas=n_asignadas,
        n_pendientes=n_pendientes,
        estado_base=reparto.estado_base,
        estado_eficiencia=reparto.estado_eficiencia,
        estado_equidad_peso=reparto.estado_equidad_peso,
        estado_equidad_articulos=reparto.estado_equidad_articulos,
        perfil=reparto.perfil,
    )


def construir_detalle(session: Session, reparto: Reparto) -> RepartoDetalleOut:
    filas = asignaciones_crud.leer_detalle_semana(session, reparto.semana)

    asignaciones: list[AsignacionDetalleOut] = []
    for (
        asig, opl, articulo, exp_requerida, exp_operario, nombre_operario,
    ) in sorted(
        filas, key=lambda r: (r[0].tipo_asignacion == TipoAsignacion.ARRASTRE, r[0].id_opl)
    ):
        es_optima: Optional[bool]
        if asig.dni_operario and exp_requerida is not None:
            es_optima = (exp_operario if exp_operario is not None else -1) >= exp_requerida
        else:
            es_optima = None

        asignaciones.append(AsignacionDetalleOut(
            id_opl=asig.id_opl,
            ref_articulo=opl.ref_articulo if opl else "?",
            nombre_articulo=articulo.descripcion if articulo else "",
            ref_familia=articulo.familia if articulo else "",
            cantidad=opl.cantidad if opl else 0,
            tipo_asignacion=asig.tipo_asignacion.value,
            es_fija=asig.es_fija,
            dni_operario=asig.dni_operario,
            nombre_operario=nombre_operario,
            tiempo_planificado=asig.tiempo_planificado,
            tiempo_total_teorico=asig.tiempo_total_teorico,
            es_optima=es_optima,
        ))

    return RepartoDetalleOut(
        semana=reparto.semana,
        aprobado=reparto.aprobado,
        fecha_aprobacion=reparto.fecha_aprobacion,
        estado_base=reparto.estado_base,
        estado_eficiencia=reparto.estado_eficiencia,
        estado_equidad_peso=reparto.estado_equidad_peso,
        estado_equidad_articulos=reparto.estado_equidad_articulos,
        asignaciones=asignaciones,
    )


def obtener_detalle(session: Session, semana: date) -> RepartoDetalleOut:
    """Devuelve el ``RepartoDetalleOut`` de una semana.

    Levanta :class:`NotFoundError` si no existe Reparto para esa semana.
    """
    reparto = repartos_crud.leer(session, semana)
    if reparto is None:
        raise NotFoundError(f"No existe reparto para la semana {semana}")
    return construir_detalle(session, reparto)


def listar_resumenes(session: Session) -> list[RepartoResumenOut]:
    """Devuelve el resumen de todos los repartos ordenados por semana."""
    return [construir_resumen(session, r) for r in repartos_crud.listar(session)]
