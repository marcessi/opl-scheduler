"""Endpoints de consulta de repartos semanales."""

import io
from datetime import date

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.api.routers.planificacion._solver_state import SOLVER_STATE
from src.api.schemas import (
    EstadoOptimizacionOut,
    ErrorOut,
    RepartoDetalleOut,
    RepartoResumenOut,
)
from src.database import get_session
from src.exceptions import NotFoundError
from src.io.excel_reparto import exportar_reparto_semana as _exportar_reparto_semana
from src.services.planificacion import vista_reparto, repartos_semanales as reparto_service

router = APIRouter(prefix="/repartos", tags=["repartos"])


@router.get("", response_model=list[RepartoResumenOut], responses={500: {"model": ErrorOut}})
def list_repartos():
    with get_session() as session:
        return vista_reparto.listar_resumenes(session)


@router.get("/estado-optimizacion", response_model=EstadoOptimizacionOut, responses={500: {"model": ErrorOut}})
def get_estado_optimizacion():
    return EstadoOptimizacionOut(**SOLVER_STATE.snapshot_estado_global())


@router.get("/{semana}", response_model=RepartoDetalleOut, responses={404: {"model": ErrorOut}, 500: {"model": ErrorOut}})
def get_reparto(semana: date):
    with get_session() as session:
        return vista_reparto.obtener_detalle(session, semana)


@router.get("/{semana}/progreso", responses={500: {"model": ErrorOut}})
def get_optimization_progress(semana: date):
    if SOLVER_STATE.semana != semana:
        return {
            "fase": "SIN_DATOS",
            "estado": "SIN_DATOS",
            "ejecutando": False,
            "terminado": False,
            "inicio_ts": None,
            "error": None,
            "fases": {},
            "config": None,
        }
    return SOLVER_STATE.snapshot_progreso()


@router.get("/{semana}/excel", responses={404: {"model": ErrorOut}, 409: {"model": ErrorOut}, 500: {"model": ErrorOut}})
def export_reparto_excel(semana: date):
    with get_session() as session:
        reparto = reparto_service.leer_reparto(session, semana)
        if reparto is None:
            raise NotFoundError(f"No existe reparto para la semana {semana}")

        buffer = io.BytesIO()
        _exportar_reparto_semana(buffer, session, semana)
        buffer.seek(0)

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=reparto-{semana}.xlsx"},
    )
