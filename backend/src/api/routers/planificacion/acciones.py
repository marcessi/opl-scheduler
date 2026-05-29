"""Endpoints de modificación y aprobación de repartos."""

from datetime import date

from fastapi import APIRouter, Depends

from src.api.routers.planificacion._guards import bloquear_si_solver_activo
from src.api.routers.planificacion._solver_state import SOLVER_STATE
from src.api.schemas import (
    ActualizarAsignacionRequest,
    AnadirAsignacionesRequest,
    AprobarSemanaRequest,
    ErrorOut,
    LimpiarSelectivoOut,
    LimpiarSelectivoRequest,
    RepartoDetalleOut,
    RepartoResumenOut,
)
from src.database import get_session
from src.exceptions import NotFoundError
from src.services.planificacion import (
    asignaciones as asignacion_opl_service,
    vista_reparto,
    repartos_semanales as reparto_service,
)

router = APIRouter(
    prefix="/repartos",
    tags=["repartos"],
    dependencies=[Depends(bloquear_si_solver_activo)],
)


@router.post(
    "/{semana}/asignaciones",
    status_code=201,
    responses={404: {"model": ErrorOut}, 409: {"model": ErrorOut}, 422: {"model": ErrorOut}},
)
def anadir_asignaciones_manuales(semana: date, req: AnadirAsignacionesRequest):
    with get_session() as session:
        n = asignacion_opl_service.crear_asignaciones_manuales(session, semana, req.ids_opls)
        return {"creadas": n}


@router.patch(
    "/{semana}/asignaciones/{id_opl}",
    response_model=RepartoDetalleOut,
    responses={404: {"model": ErrorOut}, 409: {"model": ErrorOut}, 422: {"model": ErrorOut}, 500: {"model": ErrorOut}},
)
def modify_assignment(semana: date, id_opl: str, req: ActualizarAsignacionRequest):
    with get_session() as session:
        reparto = reparto_service.leer_reparto(session, semana)
        if reparto is None:
            raise NotFoundError(f"No existe reparto para la semana {semana}")

        asignacion_opl_service.actualizar_operario_asignacion(
            session,
            id_opl,
            semana,
            req.dni_operario,
            es_fija=req.es_fija,
        )

        SOLVER_STATE.reset_semana(semana)
        return vista_reparto.construir_detalle(session, reparto)


@router.post(
    "/{semana}/limpiar-selectivo",
    response_model=LimpiarSelectivoOut,
    responses={404: {"model": ErrorOut}, 409: {"model": ErrorOut}, 500: {"model": ErrorOut}},
)
def limpiar_selectivo(semana: date, req: LimpiarSelectivoRequest):
    with get_session() as session:
        resultado = asignacion_opl_service.limpiar_selectivo_semana(
            session,
            semana,
            desfijar=req.desfijar,
            normalizar_obligatorias=req.normalizar_obligatorias,
            eliminar_arrastre=req.eliminar_arrastre,
        )
        return LimpiarSelectivoOut(
            semana=semana,
            desfijadas=resultado["desfijadas"],
            normalizadas=resultado["normalizadas"],
            arrastre_eliminados=resultado["arrastre_eliminados"],
        )


@router.post(
    "/{semana}/aprobar",
    response_model=RepartoResumenOut,
    responses={404: {"model": ErrorOut}, 409: {"model": ErrorOut}, 422: {"model": ErrorOut}, 500: {"model": ErrorOut}},
)
def approve_week(semana: date, req: AprobarSemanaRequest):
    with get_session() as session:
        reparto, meta = reparto_service.aprobar_reparto(
            session,
            semana,
            semana_destino=req.semana_destino,
            con_arrastre=req.con_arrastre,
            incluir_no_asignadas_en_arrastre=req.incluir_no_asignadas_en_arrastre,
            forzar_obligatorias_pendientes=req.forzar_obligatorias_pendientes,
            devolver_meta=True,
        )
        SOLVER_STATE.reset_semana(semana)
        resumen = vista_reparto.construir_resumen(session, reparto)
        resumen.modo_aprobacion = meta["modo_aprobacion"]
        resumen.semana_destino = meta["semana_destino"]
        resumen.incluir_no_asignadas_en_arrastre = meta["incluir_no_asignadas_en_arrastre"]
        resumen.obligatorias_forzadas = meta["obligatorias_forzadas"]
        resumen.validacion_errores = meta["validacion_errores"]
        resumen.validacion_advertencias = meta["validacion_advertencias"]
        resumen.limpieza_aplicada = meta["limpieza_aplicada"]
        resumen.no_asignadas_eliminadas_origen = meta["no_asignadas_eliminadas_origen"]
        return resumen
