"""Endpoints for repartos optimization and progress."""

import logging
import multiprocessing
import os
import threading
from datetime import date
from queue import Empty

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from src.api.schemas import (
    AsignacionItemOut,
    CargaOperarioOut,
    ErrorOut,
    MetricasOut,
    OptimizarSemanaRequest,
    PerfilDelta,
    ResultadoOut,
)
from src.api.routers.planificacion._solver_state import SOLVER_STATE
from src.database import get_session
from src.exceptions import ConflictError, DomainValidationError, NotFoundError
from src.optimization import validacion as validator
from src.optimization.cargador_problema import cargar_datos_problema
from src.optimization.solver import Configuracion
from src.optimization.solver_worker import ejecutar_solver_en_subproceso
from src.services.datos_maestros import operarios as operario_service
from src.services.planificacion import (
    asignaciones as asignacion_opl_service,
    opls as opl_service,
    repartos_semanales as reparto_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/repartos", tags=["repartos"])

# Subproceso con spawn para aislar OR-Tools del proceso uvicorn.
_MP_CTX = multiprocessing.get_context("spawn")

_DELTAS_PERFIL: dict[PerfilDelta, tuple[float, float]] = {
    PerfilDelta.produccion: (0.02, 0.03),
    PerfilDelta.balanceado: (0.05, 0.05),
    PerfilDelta.personas: (0.10, 0.05),
}

BASE_CAP_SEG = 60.0
BASE_REAL_SEG = 20.0

PESOS_TIEMPO_POR_MODO: dict[PerfilDelta, dict[str, float]] = {
    PerfilDelta.produccion: {
        "eficiencia": 1.00,
        "equidad_peso": 0.00,
        "equidad_articulos": 0.00,
    },
    PerfilDelta.balanceado: {
        "eficiencia": 0.60,
        "equidad_peso": 0.40,
        "equidad_articulos": 0.00,
    },
    PerfilDelta.personas: {
        "eficiencia": 0.15,
        "equidad_peso": 0.50,
        "equidad_articulos": 0.35,
    },
}


def _num_search_workers() -> int:
    try:
        return max(0, int(os.environ.get("SOLVER_NUM_WORKERS", "4")))
    except ValueError:
        return 4


def _repartir_tiempo(total_seg: int, modo: PerfilDelta) -> dict[str, float]:
    restante = max(0.0, total_seg - BASE_REAL_SEG)
    pesos = PESOS_TIEMPO_POR_MODO[modo]
    suma = sum(w for w in pesos.values() if w > 0) or 1.0
    return {
        "base": BASE_CAP_SEG,
        "eficiencia": restante * pesos["eficiencia"] / suma if pesos["eficiencia"] > 0 else 0.0,
        "equidad_peso": restante * pesos["equidad_peso"] / suma if pesos["equidad_peso"] > 0 else 0.0,
        "equidad_articulos": (
            restante * pesos["equidad_articulos"] / suma if pesos["equidad_articulos"] > 0 else 0.0
        ),
    }


def _construir_config(req: OptimizarSemanaRequest) -> Configuracion:
    total_seg = req.tiempo_maximo_min * 60
    reparto = _repartir_tiempo(total_seg, req.perfil)
    delta_eff, delta_eq_peso = _DELTAS_PERFIL[req.perfil]
    return Configuracion(
        nivel_eficiencia=1 if reparto["eficiencia"] > 0 else 0,
        time_limit_base=reparto["base"],
        time_limit_eficiencia=reparto["eficiencia"],
        nivel_equidad_peso=1 if reparto["equidad_peso"] > 0 else 0,
        time_limit_equidad_peso=reparto["equidad_peso"],
        nivel_equidad_articulos=1 if reparto["equidad_articulos"] > 0 else 0,
        time_limit_equidad_articulos=reparto["equidad_articulos"],
        num_search_workers=_num_search_workers(),
        delta_eficiencia=delta_eff,
        delta_equidad_peso=delta_eq_peso,
    )


@router.post(
    "/{semana}/optimizar",
    responses={
        202: {},
        400: {"model": ErrorOut},
        409: {"model": ErrorOut},
        422: {"model": ErrorOut},
        500: {"model": ErrorOut},
    },
)
def optimize_week(semana: date, req: OptimizarSemanaRequest):
    """Lanza la optimización de una semana en un subproceso (respuesta 202).

    Valida que no haya otra optimización en curso ni semanas anteriores sin
    aprobar, filtra las OPLs ya comprometidas en otras semanas y arranca el
    solver en segundo plano; el progreso se consulta aparte.

    Args:
        semana: Lunes ISO de la semana a optimizar.
        req: Parámetros (OPLs, presupuesto de tiempo y perfil).

    Raises:
        ConflictError: si ya hay una optimización activa o la semana anterior
            sigue pendiente de aprobación.
    """
    if SOLVER_STATE.is_running():
        raise ConflictError(
            f"Ya hay una optimización en curso para la semana {SOLVER_STATE.semana}"
        )

    with get_session() as session:
        pendiente_anterior = reparto_service.leer_reparto_anterior_pendiente(session, semana)
        if pendiente_anterior is not None:
            raise ConflictError(
                f"No se puede optimizar la semana {semana}: la semana anterior {pendiente_anterior.semana} no está aprobada"
            )

        if req.ids_opls is None:
            ids_normales = [opl.id for opl in opl_service.leer_todas_opls(session)]
        else:
            ids_normales = req.ids_opls

        ids_ya_repartidas_otras_semanas = asignacion_opl_service.leer_ids_opls_asignadas_otras_semanas(session, semana)
        ids_normales = [id_opl for id_opl in ids_normales if id_opl not in ids_ya_repartidas_otras_semanas]

        fijas_semana = {
            a.id_opl
            for a in asignacion_opl_service.leer_asignaciones_fijas_con_operario_semana(session, semana)
        }
        ids_normales = [id_opl for id_opl in ids_normales if id_opl not in fijas_semana]

        # Las OBLIGATORIAS de la semana ya las añade el cargador al final del
        # problema; si llegan también en `ids_normales`, entran al modelo dos
        # veces (variables x/p/m duplicadas) y el solver consume capacidad
        # fantasma asignando ambas copias. Filtrar aquí evita el duplicado.
        obligatorias_semana = {
            a.id_opl
            for a in asignacion_opl_service.leer_asignaciones_obligatorias_semana(session, semana)
        }
        ids_normales = [id_opl for id_opl in ids_normales if id_opl not in obligatorias_semana]

        validacion_previa = validator.validar_opls(session, ids_normales)
        if not validacion_previa.valido:
            raise DomainValidationError("; ".join(validacion_previa.errores))

        datos = cargar_datos_problema(session, ids_normales, semana)

        validacion = validator.validar_datos_problema(datos)
        if not validacion.valido:
            raise DomainValidationError("; ".join(validacion.errores))

        nombres_por_dni = {op.dni: op.nombre_completo for op in operario_service.leer_todos_operarios(session)}

    config = _construir_config(req)

    config_resumen = {
        "ids_opls": ids_normales,
        "n_opls": len(ids_normales),
        "perfil": req.perfil.value,
        "tiempo_maximo_min": req.tiempo_maximo_min,
        "tiempo_estimado_seg": req.tiempo_maximo_min * 60,
    }
    fases_activas = {
        "eficiencia": config.nivel_eficiencia > 0,
        "equidad_peso": config.nivel_equidad_peso > 0,
        "equidad_articulos": config.nivel_equidad_articulos > 0,
    }

    cola_progreso = _MP_CTX.Queue()
    proceso = _MP_CTX.Process(
        target=ejecutar_solver_en_subproceso,
        args=(datos, config, cola_progreso),
        daemon=True,
    )
    proceso.start()

    SOLVER_STATE.iniciar(semana, proceso, config_resumen, fases_activas)

    supervisor = threading.Thread(
        target=_supervisar_solver,
        args=(semana, proceso, cola_progreso, datos, nombres_por_dni, req.perfil.value),
        daemon=True,
    )
    supervisor.start()

    return JSONResponse(status_code=202, content={"mensaje": "Optimización iniciada"})


@router.post(
    "/{semana}/cancelar",
    responses={200: {}, 409: {"model": ErrorOut}, 500: {"model": ErrorOut}},
)
def cancel_optimization(semana: date):
    """Cancela la optimización en curso de una semana sin guardar resultados.

    Mata el subproceso del solver. Como el resultado sólo se persiste cuando el
    solver termina con éxito, abortar antes deja la BD intacta y la app vuelve al
    estado previo al lanzamiento.

    Args:
        semana: Lunes ISO de la semana cuya optimización se cancela.

    Raises:
        ConflictError: si no hay ninguna optimización en curso para esa semana.
    """
    if not SOLVER_STATE.is_running() or SOLVER_STATE.semana != semana:
        raise ConflictError(f"No hay optimización en curso para la semana {semana}")

    proceso = SOLVER_STATE.solicitar_cancelacion()
    if proceso is not None and proceso.is_alive():
        proceso.terminate()

    return JSONResponse(status_code=200, content={"mensaje": "Optimización cancelada"})


def _supervisar_solver(
    semana: date,
    proceso,
    cola_progreso,
    datos,
    nombres_por_dni: dict[str, str],
    perfil: str,
) -> None:
    """Lee mensajes de la cola y vigila la salud del subproceso del solver."""
    resultado = None
    try:
        while True:
            try:
                msg = cola_progreso.get(timeout=1.0)
            except Empty:
                if not proceso.is_alive():
                    if resultado is None:
                        if SOLVER_STATE.cancelado:
                            SOLVER_STATE.finalizar_cancelado()
                        else:
                            SOLVER_STATE.finalizar_error(
                                "El proceso del solver terminó inesperadamente"
                            )
                    return
                continue

            tipo = msg.get("tipo")
            if tipo == "fase":
                SOLVER_STATE.actualizar_fase(msg["fase"], msg["estado"])
            elif tipo == "ok":
                resultado = msg["resultado"]
                break
            elif tipo == "error":
                SOLVER_STATE.finalizar_error(msg.get("mensaje") or "Error desconocido del solver")
                return

        # Persistir y construir respuesta fuera del subproceso.
        try:
            resultado_out = _construir_resultado_out(datos, resultado, nombres_por_dni)
            resultado_dict = resultado_out.model_dump()

            with get_session() as session:
                reparto_service.aplicar_resultado(session, semana, datos, resultado, perfil)

            SOLVER_STATE.finalizar_exito(resultado_dict)
        except Exception as e:  # noqa: BLE001
            logger.exception("Fallo al aplicar resultado del solver")
            SOLVER_STATE.finalizar_error(f"Error aplicando resultado: {e}")
    finally:
        try:
            if proceso.is_alive():
                proceso.join(timeout=5)
        except Exception:
            pass


@router.get(
    "/{semana}/resultado",
    response_model=ResultadoOut,
    responses={404: {"model": ErrorOut}, 409: {"model": ErrorOut}},
)
def get_optimization_result(semana: date):
    """Devuelve el resultado de la última optimización de una semana.

    Args:
        semana: Lunes ISO de la semana.

    Returns:
        El resultado (``ResultadoOut``) con asignaciones, cargas y métricas.

    Raises:
        ConflictError: si la optimización de esa semana sigue en curso.
        NotFoundError: si no hay resultado cacheado para la semana.
    """
    if SOLVER_STATE.is_running() and SOLVER_STATE.semana == semana:
        raise ConflictError("La optimización aún está en curso")

    resultado = SOLVER_STATE.get_resultado(semana)
    if resultado is None:
        raise NotFoundError(f"No hay resultado de optimización para la semana {semana}")
    return resultado


def _construir_resultado_out(datos, resultado, nombres_por_dni) -> ResultadoOut:
    n_optimas = 0
    exps_no_opt = []
    tiempos_real = []

    n_art_op: dict[str, float] = {}
    peso_op: dict[str, float] = {}

    asignaciones_out = []
    for id_opl, dni in resultado.asignaciones.items():
        i = datos.ids_opls.index(id_opl)
        j = datos.dnis_operarios.index(dni)
        t_std = datos.tiempos_articulo[i]
        t_op = datos.tiempos_operario.get((i, j))
        t_real = t_std if t_op is None or t_op <= 0 or t_op > t_std else t_op
        if (i, j) in datos.cualificados:
            n_optimas += 1
        else:
            exps_no_opt.append(datos.experiencias.get((i, j), 0))
        tiempos_real.append(t_real)
        asignaciones_out.append(AsignacionItemOut(
            id_opl=id_opl,
            nombre_operario=nombres_por_dni.get(dni, dni),
            dni_operario=dni,
            tiempo_min=t_std,
        ))
        proporcion = resultado.tiempos_asignados[id_opl] / t_std if t_std > 0 else 1.0
        n_art_op[dni] = n_art_op.get(dni, 0.0) + proporcion * datos.cantidades[i]
        peso_op[dni]  = peso_op.get(dni, 0.0)  + proporcion * datos.pesos[i]

    media_exp = round(sum(exps_no_opt) / len(exps_no_opt), 2) if exps_no_opt else None
    media_t_real = round(sum(tiempos_real) / len(tiempos_real), 1) if tiempos_real else None

    sin_candidato = []
    sin_capacidad = []
    for id_opl in resultado.no_asignadas:
        i = datos.ids_opls.index(id_opl)
        if any((i, j) in datos.cualificados for j in range(datos.n_operarios)):
            sin_capacidad.append(id_opl)
        else:
            sin_candidato.append(id_opl)

    total_asignado = sum(resultado.cargas.values())
    total_capacidad = sum(datos.capacidades)
    pct_global = int(total_asignado / total_capacidad * 100) if total_capacidad else 0

    cargas_out = []
    for j, dni in enumerate(datos.dnis_operarios):
        carga = resultado.cargas.get(dni, 0)
        capacidad = datos.capacidades[j]
        pct = int(carga / capacidad * 100) if capacidad else 0
        cargas_out.append(CargaOperarioOut(
            nombre=nombres_por_dni.get(dni, dni),
            dni=dni,
            carga_min=carga,
            capacidad_min=capacidad,
            pct_utilizacion=pct,
            n_articulos=round(n_art_op.get(dni, 0.0), 1),
            peso_kg=round(peso_op.get(dni, 0.0), 2),
        ))

    n_normales = datos.n_opls - len(datos.obligatorias)

    return ResultadoOut(
        estado=resultado.estado,
        estado_base=resultado.estado_base,
        estado_eficiencia=resultado.estado_eficiencia,
        estado_equidad_peso=resultado.estado_equidad_peso,
        estado_equidad_articulos=resultado.estado_equidad_articulos,
        asignaciones=asignaciones_out,
        no_asignadas_sin_capacidad=sin_capacidad,
        no_asignadas_sin_candidato=sin_candidato,
        cargas=cargas_out,
        metricas=MetricasOut(
            n_opls_totales=n_normales,
            n_asignadas=len(resultado.asignaciones),
            n_optimas=n_optimas,
            media_exp_no_optimos=media_exp,
            media_tiempo_real=media_t_real,
            total_asignado_min=total_asignado,
            total_capacidad_min=total_capacidad,
            pct_utilizacion_global=pct_global,
        ),
    )
