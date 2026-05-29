"""
Servicio de AsignacionOPL: lógica de negocio sobre la capa CRUD.

PK compuesta (id_opl, semana): una OPL puede tener como máximo 2 filas
(reparto entre la semana actual y la siguiente).

Tipos (tipo_asignacion):
- NORMAL: Asignación corriente, reasignable en cada optimización.
- OBLIGATORIA: Debe asignarse completamente (INFACTIBLE si no cabe), reasignable.
- ARRASTRE: Creada al aprobar un split parcial. Siempre es_fija=True e inmutable.

es_fija=True: el solver descuenta su capacidad sin reoptimizarla.

La capa ``crud.planificacion.asignaciones`` ofrece las queries puras; este módulo
añade validaciones de dominio, recálculo de aportes y orquestación.
"""

from datetime import date
from typing import List, Optional
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from src.database.schema import AsignacionOPL, TipoAsignacion
from src.crud.datos_maestros import (
    articulos as articulos_crud,
    operarios as operarios_crud,
    operario_articulo as operario_articulo_crud,
)
from src.crud.planificacion import (
    asignaciones as asignaciones_crud,
    opls as opls_crud,
    repartos as repartos_crud,
)
from src.exceptions import NotFoundError, DomainValidationError, ConflictError


# ─── Cálculo de aportes (lógica pura, sin BD) ───────────────────────────────

def calcular_aportes(
    cantidad: int,
    peso_unitario: float,
    tiempo_planificado: float,
    tiempo_total_teorico: float,
) -> tuple[float, float]:
    """Calcula aportes proporcionales de peso y artículos para una fila de asignación."""
    if tiempo_total_teorico <= 0 or tiempo_planificado <= 0:
        return 0.0, 0.0
    ratio = min(1.0, float(tiempo_planificado) / float(tiempo_total_teorico))
    return float(cantidad) * float(peso_unitario) * ratio, float(cantidad) * ratio


# ─── Lecturas (wrappers a crud, conservados por compatibilidad) ─────────────

def leer_aportes_antes_de(session: Session, semana: date) -> dict[str, dict[str, float]]:
    return asignaciones_crud.sumar_aportes_antes_de(session, semana)


def leer_asignaciones_opl(session: Session, id_opl: str) -> List[AsignacionOPL]:
    return asignaciones_crud.listar_por_opl(session, id_opl)


def leer_asignacion(session: Session, id_opl: str, semana: date) -> Optional[AsignacionOPL]:
    return asignaciones_crud.leer(session, id_opl, semana)


def leer_asignaciones_semana(session: Session, semana: date) -> List[AsignacionOPL]:
    return asignaciones_crud.listar_semana(session, semana)


def leer_ids_opls_asignadas_otras_semanas(session: Session, semana: date) -> set[str]:
    return asignaciones_crud.ids_opls_asignadas_otras_semanas(session, semana)


def leer_asignaciones_por_tipo(
    session: Session, semana: date, tipo: TipoAsignacion,
) -> List[AsignacionOPL]:
    return asignaciones_crud.listar_semana_por_tipo(session, semana, tipo)


def leer_asignaciones_fijas_con_operario_semana(
    session: Session, semana: date,
) -> List[AsignacionOPL]:
    return asignaciones_crud.listar_fijas_con_operario_semana(session, semana)


def leer_asignaciones_obligatorias_semana(session: Session, semana: date) -> List[AsignacionOPL]:
    return asignaciones_crud.listar_obligatorias_semana(session, semana)


# ─── Eliminaciones (wrappers finos sobre crud unificado) ────────────────────

def eliminar_asignaciones_no_fijas_semana(session: Session, semana: date) -> int:
    n = asignaciones_crud.eliminar_semana(session, semana, solo_no_fijas=True)
    session.commit()
    return n


# ─── Lógica de negocio ──────────────────────────────────────────────────────

def actualizar_operario_asignacion(
    session: Session,
    id_opl: str,
    semana: date,
    nuevo_dni_operario: Optional[str],
    es_fija: Optional[bool] = None,
) -> None:
    """
    Cambia el operario y/o el flag ``es_fija`` de una asignación.

    ARRASTRE es inmutable.
    Si nuevo_dni_operario es None desasigna la OPL.

    Raises:
        NotFoundError: si la asignación, la OPL o el operario no existen.
        ConflictError: si el reparto ya está aprobado o la asignación es ARRASTRE.
        DomainValidationError: si el operario no está activo o falta capacidad.
    """
    reparto = repartos_crud.leer(session, semana)
    if reparto and reparto.aprobado:
        raise ConflictError(f"El reparto de la semana {semana} ya está aprobado")

    asignacion = asignaciones_crud.leer(session, id_opl, semana)
    if not asignacion:
        raise NotFoundError(f"No existe asignación de OPL '{id_opl}' para la semana {semana}")

    if asignacion.tipo_asignacion == TipoAsignacion.ARRASTRE:
        raise ConflictError(
            f"La asignación '{id_opl}' es un arrastre automático y no puede modificarse manualmente"
        )

    try:
        if nuevo_dni_operario is None:
            asignacion.dni_operario = None
            asignacion.tiempo_estimado_operario = None
            asignacion.tiempo_planificado = asignacion.tiempo_total_teorico
            asignacion.peso_aportado = 0.0
            asignacion.n_articulos_aportados = 0.0
        else:
            operario = operarios_crud.leer(session, nuevo_dni_operario)
            if not operario:
                raise NotFoundError(f"No existe el operario '{nuevo_dni_operario}'")
            if operario.horas_semanales <= 0:
                raise DomainValidationError(
                    f"El operario '{nuevo_dni_operario}' no está activo para reparto semanal (horas_semanales=0)"
                )

            if nuevo_dni_operario == asignacion.dni_operario:
                if es_fija is not None:
                    asignacion.es_fija = es_fija
                session.commit()
                return

            opl = opls_crud.leer(session, id_opl)
            articulo = articulos_crud.leer(session, opl.ref_articulo)
            tiempo_std_total = float(max(1, round(opl.cantidad * articulo.tiempo_estandar)))

            oa = operario_articulo_crud.leer(session, opl.ref_articulo, nuevo_dni_operario)
            if oa is not None:
                t_oa = round(opl.cantidad * oa.tiempo_estimado)
                tiempo_oa_total = float(t_oa) if t_oa > 0 else None
            else:
                tiempo_oa_total = None

            capacidad_min = int(round(operario.horas_semanales * 60))
            carga_actual = asignaciones_crud.sumar_carga_operario_semana(
                session, semana, nuevo_dni_operario, excluir_id_opl=id_opl,
            )
            if carga_actual + int(round(tiempo_std_total)) > capacidad_min:
                raise DomainValidationError(
                    f"OPL '{id_opl}' requiere {int(round(tiempo_std_total))} min en "
                    f"{operario.nombre_completo} ({nuevo_dni_operario}), pero solo quedan "
                    f"{capacidad_min - carga_actual} min disponibles esta semana "
                    f"(capacidad {capacidad_min} / usado {carga_actual})."
                )

            asignacion.dni_operario = nuevo_dni_operario
            asignacion.tiempo_planificado = tiempo_std_total
            asignacion.tiempo_estimado_operario = (
                tiempo_oa_total if tiempo_oa_total is not None else tiempo_std_total
            )
            peso_aportado, n_art_aportados = calcular_aportes(
                cantidad=opl.cantidad,
                peso_unitario=articulo.peso,
                tiempo_planificado=asignacion.tiempo_planificado,
                tiempo_total_teorico=asignacion.tiempo_total_teorico,
            )
            asignacion.peso_aportado = peso_aportado
            asignacion.n_articulos_aportados = n_art_aportados

        if es_fija is not None:
            asignacion.es_fija = es_fija

        if reparto is not None:
            reparto.estado_base = None
            reparto.estado_eficiencia = None
            reparto.estado_equidad_peso = None
            reparto.estado_equidad_articulos = None
            reparto.cota_eficiencia = None
            reparto.valor_eficiencia = None

        session.commit()
    except IntegrityError as e:
        session.rollback()
        raise ConflictError(
            f"No se pudo actualizar la asignacion de OPL '{id_opl}': {e.orig}"
        ) from e


def crear_asignaciones_manuales(
    session: Session, semana: date, ids_opls: list[str],
) -> int:
    """Crea AsignacionOPL sin operario (tipo NORMAL) para OPLs sin reparto en esa semana.

    Crea el Reparto si no existe. Omite silenciosamente OPLs que ya tienen asignación.
    """
    reparto = repartos_crud.leer(session, semana)
    if reparto is None:
        reparto = repartos_crud.crear(session, semana)
    elif reparto.aprobado:
        raise ConflictError(f"El reparto de la semana {semana} ya está aprobado")

    creadas = 0
    for id_opl in ids_opls:
        if asignaciones_crud.leer(session, id_opl, semana) is not None:
            continue
        opl = opls_crud.leer(session, id_opl)
        if not opl:
            raise NotFoundError(f"OPL '{id_opl}' no encontrada")
        tiempo_teorico = float(max(1, round(opl.cantidad * opl.articulo.tiempo_estandar)))
        asignaciones_crud.anadir(session, AsignacionOPL(
            id_opl=id_opl,
            semana=semana,
            dni_operario=None,
            tipo_asignacion=TipoAsignacion.NORMAL,
            es_fija=False,
            tiempo_planificado=tiempo_teorico,
            tiempo_total_teorico=tiempo_teorico,
            peso_aportado=0.0,
            n_articulos_aportados=0.0,
        ))
        creadas += 1
    session.commit()
    return creadas


def limpiar_selectivo_semana(
    session: Session,
    semana: date,
    *,
    desfijar: bool = False,
    normalizar_obligatorias: bool = False,
    eliminar_arrastre: bool = False,
) -> dict[str, int]:
    """Aplica toggles de limpieza sobre las asignaciones de una semana.

    Orquesta los CRUDs y hace ``commit`` único. Valida que el reparto exista y no
    esté aprobado (el endpoint llamante hace la validación previa, pero conviene
    salvaguardarla aquí).

    Returns:
        Dict con contadores: ``desfijadas``, ``normalizadas``, ``arrastre_eliminados``.
    """
    reparto = repartos_crud.leer(session, semana)
    if reparto is None:
        raise NotFoundError(f"No existe reparto para la semana {semana}")
    if reparto.aprobado:
        raise ConflictError(f"El reparto de la semana {semana} ya está aprobado")

    desfijadas = asignaciones_crud.desfijar_semana(session, semana) if desfijar else 0
    normalizadas = (
        asignaciones_crud.normalizar_obligatorias_semana(session, semana)
        if normalizar_obligatorias else 0
    )
    arrastre_eliminados = (
        asignaciones_crud.eliminar_semana(session, semana, solo_tipo=TipoAsignacion.ARRASTRE)
        if eliminar_arrastre else 0
    )

    session.commit()
    return {
        "desfijadas": desfijadas,
        "normalizadas": normalizadas,
        "arrastre_eliminados": arrastre_eliminados,
    }
