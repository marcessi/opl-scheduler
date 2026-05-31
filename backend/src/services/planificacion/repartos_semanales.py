"""
Servicio del ciclo de vida de un Reparto semanal.

Flujo:
  1. datos = optimizer.cargar_datos_problema(session, ids_opls_normales, semana)
  2. resultado = optimizer.resolver(datos, config)
  3. aplicar_resultado(session, semana, datos, resultado)  -- puede repetirse
  4. aprobar_reparto(session, semana, semana_destino)      -- genera arrastres

OPLs incluidas en el reparto quedan registradas en AsignacionOPL (es_fija=False):
- Asignadas:    dni_operario=DNI
- No asignadas: dni_operario=None  (placeholder; convertidas en obligatorias al arrastrar)
"""

from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from src.database.schema import AsignacionOPL, Reparto, TipoAsignacion
from src.crud.datos_maestros import articulos as articulos_crud
from src.crud.planificacion import (
    asignaciones as asignaciones_crud,
    opls as opls_crud,
    repartos as repartos_crud,
)
from src.services.planificacion import asignaciones as asignacion_opl_service
from src.optimization.cargador_problema import ProblemaAsignacion
from src.optimization.solver import ResultadoAsignacion
from src.exceptions import NotFoundError, DomainValidationError, ConflictError


# ─── Lectura (wrappers a crud) ──────────────────────────────────────────────

def leer_repartos(
    session: Session,
    semana: date = None,
    antes_de: date = None,
    aprobado: bool = None,
) -> list[Reparto]:
    """Lista repartos aplicando filtros opcionales.

    Args:
        session: Sesión de base de datos activa.
        semana: Si se indica, devuelve solo el reparto de esa semana.
        antes_de: Si se indica, restringe a semanas anteriores.
        aprobado: Si se indica, filtra por estado de aprobación.

    Returns:
        Lista de repartos que cumplen los filtros, ordenados por semana.
    """
    return repartos_crud.listar(session, semana=semana, antes_de=antes_de, aprobado=aprobado)


def leer_reparto(session: Session, semana: date) -> Optional[Reparto]:
    """Lee el reparto de una semana.

    Args:
        session: Sesión de base de datos activa.
        semana: Lunes ISO de la semana.

    Returns:
        El ``Reparto`` de esa semana, o ``None`` si no existe.
    """
    return repartos_crud.leer(session, semana)


def leer_reparto_anterior_pendiente(session: Session, semana_objetivo: date) -> Optional[Reparto]:
    """Retorna el reparto inmediatamente anterior sin aprobar, si existe."""
    anteriores = repartos_crud.listar(session, antes_de=semana_objetivo)
    if not anteriores:
        return None
    anterior_inmediato = anteriores[-1]
    if not anterior_inmediato.aprobado:
        return anterior_inmediato
    return None


# ─── Aplicar resultado del optimizer ────────────────────────────────────────

def aplicar_resultado(
    session: Session,
    semana: date,
    datos: ProblemaAsignacion,
    resultado: ResultadoAsignacion,
    perfil: Optional[str] = None,
) -> None:
    """Persiste el resultado del optimizer en AsignacionOPL.

    Crea el Reparto si no existe. Solo persiste si el estado es OPTIMA o FACTIBLE.
    """
    if resultado.estado not in ("OPTIMA", "FACTIBLE"):
        return

    reparto = repartos_crud.leer(session, semana)
    if reparto is None:
        reparto = repartos_crud.crear(session, semana)
    elif reparto.aprobado:
        raise ConflictError(f"El reparto de la semana {semana} ya está aprobado")

    reparto.estado_base              = resultado.estado_base
    reparto.estado_eficiencia        = resultado.estado_eficiencia
    reparto.estado_equidad_peso      = resultado.estado_equidad_peso
    reparto.estado_equidad_articulos = resultado.estado_equidad_articulos
    reparto.cota_eficiencia          = resultado.cota_eficiencia
    reparto.valor_eficiencia         = resultado.valor_eficiencia
    if perfil is not None:
        reparto.perfil = perfil

    asignacion_opl_service.eliminar_asignaciones_no_fijas_semana(session, semana)

    existentes_semana = {
        a.id_opl: a
        for a in asignaciones_crud.listar_semana(session, semana)
    }

    id_a_idx_opl = {id_opl: i for i, id_opl in enumerate(datos.ids_opls)}
    dni_a_idx_op = {dni: j for j, dni in enumerate(datos.dnis_operarios)}

    for id_opl, dni_asignado in resultado.asignaciones.items():
        i = id_a_idx_opl[id_opl]
        j = dni_a_idx_op[dni_asignado]
        tiempo_total_para_op = datos.tiempos_operario.get((i, j), datos.tiempos_articulo[i])
        tiempo_esta_semana = resultado.tiempos_asignados[id_opl]
        peso_unitario = datos.pesos[i] / datos.cantidades[i]
        peso_aportado, n_art_aportados = asignacion_opl_service.calcular_aportes(
            cantidad=datos.cantidades[i],
            peso_unitario=peso_unitario,
            tiempo_planificado=tiempo_esta_semana,
            tiempo_total_teorico=datos.tiempos_articulo[i],
        )

        if i in datos.obligatorias:
            asignaciones_crud.anadir(session, AsignacionOPL(
                id_opl=id_opl,
                semana=semana,
                dni_operario=dni_asignado,
                tipo_asignacion=TipoAsignacion.OBLIGATORIA,
                es_fija=False,
                tiempo_planificado=tiempo_esta_semana,
                tiempo_estimado_operario=tiempo_total_para_op,
                tiempo_total_teorico=datos.tiempos_articulo[i],
                peso_aportado=peso_aportado,
                n_articulos_aportados=n_art_aportados,
            ))
        else:
            if id_opl in existentes_semana:
                continue
            asignaciones_crud.anadir(session, AsignacionOPL(
                id_opl=id_opl,
                semana=semana,
                dni_operario=dni_asignado,
                tipo_asignacion=TipoAsignacion.NORMAL,
                es_fija=False,
                tiempo_planificado=tiempo_esta_semana,
                tiempo_estimado_operario=tiempo_total_para_op,
                tiempo_total_teorico=datos.tiempos_articulo[i],
                peso_aportado=peso_aportado,
                n_articulos_aportados=n_art_aportados,
            ))

    for id_opl in resultado.no_asignadas:
        if id_opl in existentes_semana:
            continue
        i = id_a_idx_opl[id_opl]
        if i in datos.obligatorias:
            continue
        asignaciones_crud.anadir(session, AsignacionOPL(
            id_opl=id_opl,
            semana=semana,
            dni_operario=None,
            tipo_asignacion=TipoAsignacion.NORMAL,
            es_fija=False,
            tiempo_planificado=0,
            tiempo_estimado_operario=None,
            tiempo_total_teorico=datos.tiempos_articulo[i],
            peso_aportado=0.0,
            n_articulos_aportados=0.0,
        ))

    session.commit()


# ─── Aprobación ─────────────────────────────────────────────────────────────

def aprobar_reparto(
    session: Session,
    semana: date,
    semana_destino: date,
    con_arrastre: bool = True,
    incluir_no_asignadas_en_arrastre: bool = True,
    forzar_obligatorias_pendientes: bool = False,
    devolver_meta: bool = False,
) -> Reparto | tuple[Reparto, dict[str, object]]:
    """Aprueba el reparto de una semana y opcionalmente genera arrastres."""
    if semana_destino is None:
        raise DomainValidationError("Semana destino es obligatoria")
    if semana_destino <= semana:
        raise DomainValidationError("La semana_destino debe ser posterior a la semana aprobada")

    reparto = repartos_crud.leer(session, semana)
    if reparto is None:
        raise NotFoundError(f"No existe Reparto para la semana {semana}")
    if reparto.aprobado:
        raise ConflictError(f"El reparto de la semana {semana} ya está aprobado")

    anterior_pendiente = leer_reparto_anterior_pendiente(session, semana)
    if anterior_pendiente is not None:
        raise ConflictError(
            f"No se puede aprobar la semana {semana}: la semana anterior {anterior_pendiente.semana} sigue pendiente"
        )

    filas = asignaciones_crud.listar_semana(session, semana)
    if not filas:
        raise DomainValidationError(f"El reparto de la semana {semana} no tiene asignaciones")

    advertencias: list[str] = []

    obligatorias_sin_operario = [
        f for f in filas
        if f.tipo_asignacion == TipoAsignacion.OBLIGATORIA
        and not f.es_fija
        and f.dni_operario is None
    ]
    if obligatorias_sin_operario:
        msg = f"Hay {len(obligatorias_sin_operario)} OPL obligatoria(s) sin asignar en la semana {semana}"
        if forzar_obligatorias_pendientes:
            advertencias.append(msg)
        else:
            raise DomainValidationError(msg)

    limpieza_aplicada = False

    normales = asignaciones_crud.listar_no_fijas_semana(session, semana)

    necesita_arrastre = False
    if con_arrastre:
        for fila in normales:
            if fila.dni_operario is None:
                if incluir_no_asignadas_en_arrastre:
                    necesita_arrastre = True
                    break
                continue
            tiempo_total_ref = float(fila.tiempo_total_teorico)
            tiempo_restante = round(tiempo_total_ref - fila.tiempo_planificado, 6)
            if tiempo_restante > 0.01:
                necesita_arrastre = True
                break

    if con_arrastre and necesita_arrastre:
        reparto_destino = repartos_crud.leer(session, semana_destino)
        if reparto_destino is not None and reparto_destino.aprobado:
            raise ConflictError(f"La semana destino {semana_destino} ya está aprobada")
        if reparto_destino is None:
            repartos_crud.crear(session, semana_destino)
        else:
            asignaciones_crud.eliminar_semana(session, semana_destino)
            limpieza_aplicada = True

        for fila in normales:
            existente_sig = asignaciones_crud.leer(session, fila.id_opl, semana_destino)

            if fila.dni_operario is None:
                if not incluir_no_asignadas_en_arrastre:
                    continue
                tiempo_total_teorico = float(fila.tiempo_total_teorico)

                if existente_sig is None:
                    asignaciones_crud.anadir(session, AsignacionOPL(
                        id_opl=fila.id_opl,
                        semana=semana_destino,
                        dni_operario=None,
                        tipo_asignacion=TipoAsignacion.OBLIGATORIA,
                        es_fija=False,
                        tiempo_planificado=tiempo_total_teorico,
                        tiempo_estimado_operario=None,
                        tiempo_total_teorico=tiempo_total_teorico,
                        peso_aportado=0.0,
                        n_articulos_aportados=0.0,
                    ))
                else:
                    existente_sig.tipo_asignacion = TipoAsignacion.OBLIGATORIA
                    existente_sig.es_fija = False
                    existente_sig.dni_operario = None
                    existente_sig.tiempo_planificado = tiempo_total_teorico
                    existente_sig.tiempo_estimado_operario = None
                    existente_sig.tiempo_total_teorico = tiempo_total_teorico
                    existente_sig.peso_aportado = 0.0
                    existente_sig.n_articulos_aportados = 0.0
                continue

            tiempo_total_ref = fila.tiempo_total_teorico
            tiempo_estimado_ref = (
                float(fila.tiempo_estimado_operario)
                if fila.tiempo_estimado_operario is not None
                else float(tiempo_total_ref)
            )
            tiempo_restante = round(tiempo_total_ref - fila.tiempo_planificado, 6)

            if tiempo_restante > 0.01:
                opl_obj = opls_crud.leer(session, fila.id_opl)
                art_obj = (
                    articulos_crud.leer(session, opl_obj.ref_articulo)
                    if opl_obj is not None else None
                )
                if opl_obj is not None and art_obj is not None:
                    peso_aportado, n_art_aportados = asignacion_opl_service.calcular_aportes(
                        cantidad=opl_obj.cantidad,
                        peso_unitario=art_obj.peso,
                        tiempo_planificado=tiempo_restante,
                        tiempo_total_teorico=fila.tiempo_total_teorico,
                    )
                else:
                    peso_aportado, n_art_aportados = 0.0, 0.0
                if existente_sig is None:
                    asignaciones_crud.anadir(session, AsignacionOPL(
                        id_opl=fila.id_opl,
                        semana=semana_destino,
                        dni_operario=fila.dni_operario,
                        tipo_asignacion=TipoAsignacion.ARRASTRE,
                        es_fija=True,
                        tiempo_planificado=tiempo_restante,
                        tiempo_estimado_operario=tiempo_estimado_ref,
                        tiempo_total_teorico=fila.tiempo_total_teorico,
                        peso_aportado=peso_aportado,
                        n_articulos_aportados=n_art_aportados,
                    ))
                else:
                    existente_sig.tipo_asignacion = TipoAsignacion.ARRASTRE
                    existente_sig.es_fija = True
                    existente_sig.dni_operario = fila.dni_operario
                    existente_sig.tiempo_planificado = tiempo_restante
                    existente_sig.tiempo_estimado_operario = tiempo_estimado_ref
                    existente_sig.tiempo_total_teorico = fila.tiempo_total_teorico
                    existente_sig.peso_aportado = peso_aportado
                    existente_sig.n_articulos_aportados = n_art_aportados
            else:
                if existente_sig is not None and existente_sig.tipo_asignacion == TipoAsignacion.ARRASTRE:
                    asignaciones_crud.eliminar(session, existente_sig)

    no_asignadas_eliminadas_origen = asignaciones_crud.eliminar_semana(
        session, semana, solo_no_fijas=True, solo_sin_operario=True,
    )

    reparto.aprobado = True
    reparto.fecha_aprobacion = datetime.now(timezone.utc)
    session.commit()
    session.refresh(reparto)
    meta = {
        "semana_destino": semana_destino,
        "modo_aprobacion": "con_arrastre" if con_arrastre else "sin_arrastre",
        "incluir_no_asignadas_en_arrastre": con_arrastre and incluir_no_asignadas_en_arrastre,
        "obligatorias_forzadas": bool(forzar_obligatorias_pendientes and obligatorias_sin_operario),
        "validacion_errores": [],
        "validacion_advertencias": list(advertencias),
        "limpieza_aplicada": limpieza_aplicada,
        "no_asignadas_eliminadas_origen": no_asignadas_eliminadas_origen,
    }
    if devolver_meta:
        return reparto, meta
    return reparto
