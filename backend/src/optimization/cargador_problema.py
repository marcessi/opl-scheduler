"""
Carga de datos de la BD y construcción del problema de asignación.

Transforma entidades ORM en estructuras numéricas puras (ProblemaAsignacion)
listas para ser consumidas por el solver.
"""

from dataclasses import dataclass
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from src.services.datos_maestros import (
    operarios as operario_service,
    operario_familia as operario_familia_service,
    operario_articulo as operario_articulo_service,
    articulos as articulo_service,
)
from src.services.planificacion import (
    opls as opl_service,
    asignaciones as asignacion_opl_service,
)
from src.exceptions import DomainValidationError


# ─────────────────────────────────────────────────────────────────────────────
# Estructura de datos
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ProblemaAsignacion:
    """
    Representación del problema de asignación lista para el solver.

    El orden de ids_opls es: OPLs normales primero, luego obligatorias.
    Los índices en `obligatorias` corresponden a la posición en ids_opls.
    """

    # Dimensiones
    n_opls: int
    n_operarios: int

    # Mapeos índice → identificador de BD
    ids_opls: list       # ids_opls[i]       → id OPL en BD
    dnis_operarios: list # dnis_operarios[j] → DNI operario en BD

    # Índices (0-based) de OPLs obligatorias dentro de ids_opls
    obligatorias: set       # {i}  — deben asignarse completas; si no → INFACTIBLE

    # Datos numéricos
    cantidades: list        # cantidades[i]  → unidades de la OPL i
    pesos: list             # pesos[i]       → kg totales de la OPL i (cantidad * articulo.peso)
    # Capacidad disponible ya descontadas las filas fija-con-operario
    capacidades: list       # capacidades[j] → minutos disponibles del operario j (entero)

    # tiempos_articulo[i] = round(cantidad_i * tiempo_estandar_i)
    #   tiempo total basado en el estándar del artículo, igual para todos los operarios
    tiempos_articulo: list

    # tiempos_operario[(i, j)] = round(cantidad_i * oa.tiempo_estimado)
    #   solo se guarda cuando existe Operario_Articulo y el tiempo es valido (<= estandar)
    #   si no existe o es invalido, se usa tiempo_articulo
    tiempos_operario: dict

    # experiencias[(i, j)] = experiencia del operario j en la familia de la OPL i (entero)
    #   solo existe para pares con registro Operario_Familia
    experiencias: dict

    # Pares (i, j) donde el operario cumple experiencia >= experiencia_requerida de la familia
    cualificados: set       # {(i, j)}

    # Acumuladores históricos derivados de AsignacionOPL en semanas anteriores
    pesos_historicos:     list   # pesos_historicos[j]     = kg aprobados acumulados del operario j
    articulos_historicos: list   # articulos_historicos[j] = artículos aprobados acumulados del operario j


# ─────────────────────────────────────────────────────────────────────────────
# Carga de datos
# ─────────────────────────────────────────────────────────────────────────────

def cargar_datos_problema(
    session: Session,
    ids_opls_normales: list,
    semana: Optional[date] = None,
) -> ProblemaAsignacion:
    """
    Lee la BD y construye un ProblemaAsignacion listo para el solver.

    Args:
        session:            Sesión de SQLAlchemy.
        ids_opls_normales:  IDs de OPL normales a optimizar esta semana.
        semana:             Si se provee, carga también las filas fijas de esa semana:
                            - fija_con_operario → deduce su tiempo_planificado de la
                              capacidad del operario correspondiente.
                            - obligatorias (fija=True, dni=None) → se añaden al
                              problema como OPLs que deben asignarse completas.

    Returns:
        ProblemaAsignacion con todos los datos en estructuras Python puras.
    """
    # ── 1. Operarios activos (horas > 0) ────────────────────────────────────
    # Los operarios con 0h se consideran no disponibles y no entran en reparto.
    operarios = [op for op in operario_service.leer_todos_operarios(session) if op.horas_semanales > 0]
    n_operarios = len(operarios)
    dnis = [op.dni for op in operarios]

    # Capacidades base (minutos semanales)
    capacidades = [round(op.horas_semanales * 60) for op in operarios]

    # Históricos agregados por semana anterior (semana < actual)
    if semana is not None:
        aportes_previos = asignacion_opl_service.leer_aportes_antes_de(session, semana)
    else:
        aportes_previos = {}
    pesos_historicos = [float(aportes_previos.get(op.dni, {}).get("peso", 0.0)) for op in operarios]
    articulos_historicos = [float(aportes_previos.get(op.dni, {}).get("articulos", 0.0)) for op in operarios]

    # ── 2. Filas fija-con-operario: descontar de capacidades ────────────────
    ids_opls_obligatorias: list = []
    fijas_con_op: list = []

    if semana is not None:
        fijas_con_op = asignacion_opl_service.leer_asignaciones_fijas_con_operario_semana(
            session, semana
        )
        for fila in fijas_con_op:
            if fila.dni_operario in dnis:
                j = dnis.index(fila.dni_operario)
                capacidades[j] = max(0, capacidades[j] - round(fila.tiempo_planificado))

        # Sumar contribuciones FIJA ya persistidas en la propia fila de asignación.
        for fila in fijas_con_op:
            if fila.dni_operario not in dnis:
                continue
            j = dnis.index(fila.dni_operario)
            pesos_historicos[j] += float(fila.peso_aportado or 0.0)
            articulos_historicos[j] += float(fila.n_articulos_aportados or 0.0)

        # ── 3. Filas obligatorias ──────────────────────
        obligatorias_db = asignacion_opl_service.leer_asignaciones_obligatorias_semana(
            session, semana
        )
        ids_opls_obligatorias = [f.id_opl for f in obligatorias_db]

    # ── 4. Lista completa de OPLs (normales primero, obligatorias al final) ──
    ids_opls_todos = list(ids_opls_normales) + ids_opls_obligatorias
    n_opls = len(ids_opls_todos)
    obligatorias_idx = set(range(len(ids_opls_normales), n_opls))

    if n_opls == 0:
        return ProblemaAsignacion(
            n_opls=0, n_operarios=n_operarios,
            ids_opls=[], dnis_operarios=dnis,
            obligatorias=set(),
            cantidades=[], pesos=[], capacidades=capacidades,
            tiempos_articulo=[], tiempos_operario={}, experiencias={}, cualificados=set(),
            pesos_historicos=pesos_historicos,
            articulos_historicos=articulos_historicos,
        )

    opls_lista = opl_service.leer_opls_bulk(session, ids_opls_todos)
    opls_por_id = {opl.id: opl for opl in opls_lista}
    opls = [opls_por_id.get(id_opl) for id_opl in ids_opls_todos]

    for id_opl, opl in zip(ids_opls_todos, opls):
        if opl is None:
            raise DomainValidationError(f"La OPL '{id_opl}' no existe en la base de datos")

    # Cache de artículos (una sola query con familia precargada)
    refs_articulos_lote = list({opl.ref_articulo for opl in opls})
    articulos_lista = articulo_service.leer_articulos_bulk(session, refs_articulos_lote)
    articulos = {a.referencia: a for a in articulos_lista}

    refs_faltantes = [ref for ref in refs_articulos_lote if ref not in articulos]
    if refs_faltantes:
        raise DomainValidationError(
            f"Los artículos referenciados por OPLs no existen: {sorted(refs_faltantes)}"
        )

    # ── 5. Construir tiempos, experiencias y cualificados ────────────────────
    # Precarga en dos queries: solo familias y artículos del lote actual
    familias_lote = list({articulos[opl.ref_articulo].familia for opl in opls})
    refs_lote     = list(articulos.keys())

    of_cache = {
        (of.dni_operario, of.familia): of
        for of in operario_familia_service.leer_operario_familia_bulk(session, dnis, familias_lote)
    }
    oa_cache = {
        (oa.ref_articulo, oa.dni_operario): oa
        for oa in operario_articulo_service.leer_operario_articulo_bulk(session, dnis, refs_lote)
    }

    tiempos_articulo: list = []
    tiempos_operario: dict = {}
    experiencias: dict = {}
    cualificados: set = set()

    for i, opl in enumerate(opls):
        articulo = articulos[opl.ref_articulo]
        exp_requerida = articulo.familia_obj.experiencia_requerida
        t_std = max(1, round(opl.cantidad * articulo.tiempo_estandar))
        tiempos_articulo.append(t_std)

        for j, op in enumerate(operarios):
            # Sin Operario_Familia → experiencia mínima (1). El operario puede coger la OPL
            # pero no entra en `cualificados` (la fase EFICIENCIA lo penaliza). Paralelo a
            # la jerarquía de tiempos: sin Operario_Articulo se usa el tiempo estándar.
            of = of_cache.get((op.dni, articulo.familia))
            exp = int(of.experiencia) if of is not None else 1
            experiencias[(i, j)] = exp
            if of is not None and exp >= exp_requerida:
                cualificados.add((i, j))

            oa = oa_cache.get((opl.ref_articulo, op.dni))
            if oa is not None:
                t_oa = round(opl.cantidad * oa.tiempo_estimado)
                if t_oa > 0:
                    tiempos_operario[(i, j)] = t_oa

    return ProblemaAsignacion(
        n_opls=n_opls,
        n_operarios=n_operarios,
        ids_opls=ids_opls_todos,
        dnis_operarios=dnis,
        obligatorias=obligatorias_idx,
        cantidades=[opl.cantidad for opl in opls],
        pesos=[opl.cantidad * articulos[opl.ref_articulo].peso for opl in opls],
        capacidades=capacidades,
        tiempos_articulo=tiempos_articulo,
        tiempos_operario=tiempos_operario,
        experiencias=experiencias,
        cualificados=cualificados,
        pesos_historicos=pesos_historicos,
        articulos_historicos=articulos_historicos,
    )
