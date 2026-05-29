"""
Modelo CP-SAT para la asignacion de OPLs a operarios.

Flujo de uso:
    datos     = cargar_datos_problema(session, ids_opls_normales, semana)  # loader.py
    resultado = resolver(datos, config)

MVP — dos tipos de OPL:
- Normal: se asigna completamente a un operario o queda sin asignar.
- Obligatoria (fija=True, dni=None): debe asignarse; si no cabe → INFACTIBLE.

Las filas fija-con-operario no entran en el modelo; solo reducen la capacidad
del operario correspondiente (ya descontada en ProblemaAsignacion.capacidades).
"""

import logging
from dataclasses import dataclass
from typing import Callable, Optional

from ortools.sat.python import cp_model

from src.optimization.cargador_problema import ProblemaAsignacion

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Estructuras de datos
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ResultadoAsignacion:
    """Resultado devuelto por el solver tras ejecutar resolver()."""

    estado: str                    # 'OPTIMA' | 'FACTIBLE' | 'INFACTIBLE' | 'DESCONOCIDO'
    estado_base: str               # estado de la fase 1 — maximizar minutos
    estado_eficiencia: str         # estado de la fase de eficiencia — maximizar calidad de asignaciones
    estado_equidad_peso: str       # estado de la fase de equidad de peso
    estado_equidad_articulos: str  # estado de la fase de equidad de artículos
    asignaciones: dict             # {id_opl: dni_operario}  — OPLs asignadas
    tiempos_asignados: dict        # {id_opl: minutos}       — tiempo completo de cada OPL asignada
    no_asignadas: list             # [id_opl] — OPLs normales que no cabieron
    cargas: dict                   # {dni_operario: minutos_asignados}
    cota_eficiencia: Optional[float] = None   # best_objective_bound de la fase EFICIENCIA
    valor_eficiencia: Optional[float] = None  # objective_value logrado en EFICIENCIA


# ─────────────────────────────────────────────────────────────────────────────
# Configuración
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class Configuracion:
    """
    Parámetros configurables del solver.

    Fases (lexicográficas, cada una fija el objetivo de la anterior):
      BASE (siempre): maximiza minutos asignados.
      EFICIENCIA (nivel_eficiencia>0): maximiza calidad de asignaciones.
      EQUIDAD_PESO (nivel_equidad_peso>0): minimiza rango de kg acumulados por operario.
      EQUIDAD_ARTICULOS (nivel_equidad_articulos>0): minimiza rango de artículos acumulados.

    Un límite de 0.0 significa sin límite de tiempo.
    """
    nivel_eficiencia:             int   = 0    # 0=off, 1-100=activo
    nivel_equidad_peso:           int   = 0    # 0=off, 1-100=activo
    nivel_equidad_articulos:      int   = 0    # 0=off, 1-100=activo
    time_limit_base:              float = 0.0  # límite para la fase BASE (0.0=sin límite)
    time_limit_eficiencia:        float = 0.0
    time_limit_equidad_peso:      float = 0.0
    time_limit_equidad_articulos: float = 0.0
    num_search_workers:           int   = 0
    delta_eficiencia:             float = 0.0  # fracción 0–1; relaja exp+speed al pasar a equidad
    delta_equidad_peso:           float = 0.0  # fracción 0–1; relaja gap kg al pasar a equidad_articulos


# ─────────────────────────────────────────────────────────────────────────────
# Construcción del objetivo lexicográfico
# ─────────────────────────────────────────────────────────────────────────────


def _tiempo_real_eficiencia(datos: ProblemaAsignacion, i: int, j: int) -> int:
    """
    Devuelve el tiempo real usado en eficiencia:
    - si no hay tiempo por operario, usa tiempo estándar del artículo;
    - si el tiempo por operario es mayor al estándar, cae al estándar.
    """
    t_std = int(datos.tiempos_articulo[i])
    t_op = datos.tiempos_operario.get((i, j))
    if t_op is None or t_op <= 0 or t_op > t_std:
        return t_std
    return int(t_op)


def _weighted_expr(terminos: list[tuple[int, object]]):
    """Construye una expresión lineal a partir de pares (coef, var)."""
    return cp_model.LinearExpr.sum([coef * var for coef, var in terminos if coef != 0])


def _construir_expresion_eficiencia(x: dict, p: dict, datos: ProblemaAsignacion):
    """
    Fase EFICIENCIA (única pasada): combina lexicográficamente, en un solo objetivo,
    tres criterios decrecientes en prioridad mediante pesos:

        1) nº de asignaciones cualificadas (óptimos)
        2) experiencia acumulada en asignaciones no cualificadas
        3) velocidad total (operario más rápido) como desempate global

    Los pesos se eligen para que cada criterio domine estrictamente al siguiente,
    dado que todos los términos están acotados por n_opls * (max valor por par).
    """
    max_t = max(
        (_tiempo_real_eficiencia(datos, i, j) for (i, j) in datos.experiencias),
        default=1,
    ) if datos.experiencias else 1

    max_exp = max(datos.experiencias.values(), default=1) if datos.experiencias else 1

    t_count: list[tuple[int, object]] = []
    t_exp: list[tuple[int, object]] = []
    t_speed: list[tuple[int, object]] = []

    for vars_asignacion in (x, p):
        for (i, j), var in vars_asignacion.items():
            t_real = _tiempo_real_eficiencia(datos, i, j)
            t_speed.append((max_t - t_real, var))
            if (i, j) in datos.cualificados:
                t_count.append((1, var))
            else:
                exp = datos.experiencias.get((i, j), 0)
                if exp > 0:
                    t_exp.append((exp, var))

    # Cotas superiores estrictas de cada criterio (acotando por encima):
    #   speed_max ≤ n_opls * max_t
    #   exp_max   ≤ n_opls * max_exp
    #   count_max ≤ n_opls
    max_speed = datos.n_opls * max_t
    w_speed = 1
    w_exp = max_speed + 1
    w_count = (datos.n_opls * max_exp) * w_exp + max_speed + 1

    return cp_model.LinearExpr.sum([
        w_count * _weighted_expr(t_count),
        w_exp * _weighted_expr(t_exp),
        w_speed * _weighted_expr(t_speed),
    ])


def _construir_expresion_base(x: dict, m: dict, datos: ProblemaAsignacion):
    """Objetivo base: maximizar minutos asignados."""
    terminos = [(datos.tiempos_articulo[i], var) for (i, _j), var in x.items()]
    terminos.extend((1, var_m) for var_m in m.values())
    return _weighted_expr(terminos)


def _construir_expr_equidad_peso(model, x: dict, m: dict, datos: ProblemaAsignacion):
    """
    Fase EQUIDAD_PESO: minimiza el rango (max − min) de kg totales acumulados por operario.
    Retorna expresión a maximizar: m_p − M_p  (≤ 0; 0 = equidad perfecta).
    Escala ×100 para precisión de 10 g. Los kg históricos son constantes.
    """
    SCALE = 100
    n_normales = datos.n_opls - len(datos.obligatorias)

    M_p = model.new_int_var(0, 10 ** 10, 'max_peso_eq')
    m_p = model.new_int_var(0, 10 ** 10, 'min_peso_eq')

    for j in range(datos.n_operarios):
        base_j = int(round(datos.pesos_historicos[j] * SCALE))
        terminos = []
        for i in range(datos.n_opls):
            if (i, j) in x:
                coef = int(round(datos.pesos[i] * SCALE))
                if coef > 0:
                    terminos.append(coef * x[i, j])
        for i in range(n_normales):
            if (i, j) in m:
                t_std = datos.tiempos_articulo[i]
                if t_std > 0:
                    coef_p = int(round(datos.pesos[i] * SCALE / t_std))
                    if coef_p > 0:
                        terminos.append(coef_p * m[i, j])
        total_j = base_j + (cp_model.LinearExpr.sum(terminos) if terminos else 0)
        model.add(M_p >= total_j)
        model.add(m_p <= total_j)

    return m_p - M_p


def _construir_expr_equidad_articulos(model, x: dict, m: dict, datos: ProblemaAsignacion):
    """
    Fase EQUIDAD_ARTICULOS: minimiza el rango (max − min) de artículos acumulados por operario.
    Retorna expresión a maximizar: m_a − M_a  (≤ 0; 0 = equidad perfecta).
    Escala ×10 para artículos fraccionarios en asignaciones parciales.
    """
    SCALE = 10
    n_normales = datos.n_opls - len(datos.obligatorias)

    M_a = model.new_int_var(0, 10 ** 10, 'max_art_eq')
    m_a = model.new_int_var(0, 10 ** 10, 'min_art_eq')

    for j in range(datos.n_operarios):
        base_j = int(round(datos.articulos_historicos[j] * SCALE))
        terminos = []
        for i in range(datos.n_opls):
            if (i, j) in x:
                coef = int(round(datos.cantidades[i] * SCALE))
                if coef > 0:
                    terminos.append(coef * x[i, j])
        for i in range(n_normales):
            if (i, j) in m:
                t_std = datos.tiempos_articulo[i]
                if t_std > 0:
                    coef_a = int(round(datos.cantidades[i] * SCALE / t_std))
                    if coef_a > 0:
                        terminos.append(coef_a * m[i, j])
        total_j = base_j + (cp_model.LinearExpr.sum(terminos) if terminos else 0)
        model.add(M_a >= total_j)
        model.add(m_a <= total_j)

    return m_a - M_a


def _configure_solver(solver: cp_model.CpSolver, config: Configuracion, time_limit: float = 0.0):
    if time_limit > 0:
        solver.parameters.max_time_in_seconds = time_limit
    if config.num_search_workers > 0:
        solver.parameters.num_search_workers = config.num_search_workers


def _add_hints_from_solution(model, solver: cp_model.CpSolver, x: dict, p: dict, m: dict) -> None:
    """Reemplaza el warm start del modelo con la solución ya encontrada en la fase anterior.

    Limpia los hints existentes antes de añadir los nuevos para evitar entradas duplicadas
    (add_hint acumula en el proto; con duplicados CP-SAT puede arrancar desde la solución
    incorrecta de una fase anterior cuando se ejecuta con múltiples workers).
    """
    model.clear_hints()
    for var in x.values():
        model.add_hint(var, solver.value(var))
    for var in p.values():
        model.add_hint(var, solver.value(var))
    for var in m.values():
        model.add_hint(var, solver.value(var))


# ─────────────────────────────────────────────────────────────────────────────
# Modelo CP-SAT
# ─────────────────────────────────────────────────────────────────────────────

def resolver(
    datos: ProblemaAsignacion,
    config: Configuracion,
    on_phase_change: Optional[Callable[[str, str], None]] = None,
) -> ResultadoAsignacion:
    """
    Construye y resuelve el modelo CP-SAT.

    Variables:
        x[i, j]  bool — OPL i asignada completa al operario j
        p[i, j]  bool — OPL i asignada parcial al operario j (solo normales)
        m[i, j]   int — minutos parciales de la OPL i en el operario j

    Restricciones:
        - Normal i:      add_at_most_one(x[i,j] for j)
        - Obligatoria i: add_exactly_one(x[i,j] for j)
        - Capacidad j:   sum_i(tiempos_articulo[i] * x[i,j]) <= capacidades[j]

    Objetivo (lexicográfico por fases):
        - Fase 1 (siempre):   BASE        — maximizar minutos totales asignados.
        - Fase 2 (opcional):  EFICIENCIA  — única pasada que maximiza, por prioridad
          decreciente: nº cualificados > experiencia no-cualificados > velocidad.
          Se activa con nivel_eficiencia>0.
    """
    if datos.n_opls == 0:
        if on_phase_change is not None:
            on_phase_change("BASE", "OPTIMA")
            on_phase_change("EFICIENCIA", "NO_EJECUTADA")
            on_phase_change("EQUIDAD_PESO", "NO_EJECUTADA")
            on_phase_change("EQUIDAD_ARTICULOS", "NO_EJECUTADA")
        return ResultadoAsignacion(
            estado="OPTIMA",
            estado_base="OPTIMA",
            estado_eficiencia="NO_EJECUTADA",
            estado_equidad_peso="NO_EJECUTADA",
            estado_equidad_articulos="NO_EJECUTADA",
            asignaciones={},
            tiempos_asignados={},
            no_asignadas=[],
            cargas={dni: 0 for dni in datos.dnis_operarios},
        )

    model = cp_model.CpModel()

    def _emit(fase: str, estado_fase: str) -> None:
        if on_phase_change is not None:
            on_phase_change(fase, estado_fase)

    def _estado_texto(status_code: int) -> str:
        return {
            cp_model.OPTIMAL: "OPTIMA",
            cp_model.FEASIBLE: "FACTIBLE",
            cp_model.INFEASIBLE: "INFACTIBLE",
            cp_model.UNKNOWN: "DESCONOCIDO",
        }.get(status_code, "DESCONOCIDO")

    # ── Variables x/p/m ─────────────────────────────────────────────────────
    x = {
        (i, j): model.new_bool_var(f'x_opl{datos.ids_opls[i]}_op{j}')
        for (i, j) in datos.experiencias
    }

    p: dict[tuple[int, int], object] = {}
    m: dict[tuple[int, int], object] = {}

    n_normales = datos.n_opls - len(datos.obligatorias)
    for i in range(n_normales):
        t_i = int(datos.tiempos_articulo[i])
        if t_i < 2:
            continue
        for j in range(datos.n_operarios):
            if (i, j) not in datos.experiencias:
                continue
            p_ij = model.new_bool_var(f'p_opl{datos.ids_opls[i]}_op{j}')
            m_ij = model.new_int_var(0, t_i - 1, f'm_opl{datos.ids_opls[i]}_op{j}')
            p[i, j] = p_ij
            m[i, j] = m_ij

            # Linealización sin reificación:
            #   p_ij = 0 → m_ij ∈ [0,0]
            #   p_ij = 1 → m_ij ∈ [1, t_i-1]
            model.Add(m_ij >= p_ij)
            model.Add(m_ij <= (t_i - 1) * p_ij)
            model.Add(x[i, j] + p_ij <= 1)

    # ── Restricciones de asignación por OPL ─────────────────────────────────
    for i in range(datos.n_opls):
        opciones = [x[i, j] for j in range(datos.n_operarios) if (i, j) in datos.experiencias]
        if i in datos.obligatorias:
            model.add_exactly_one(opciones)
        else:
            opciones_parcial = [p[i, j] for j in range(datos.n_operarios) if (i, j) in p]
            todas = opciones + opciones_parcial
            if todas:
                model.add_at_most_one(todas)

    # Como mucho una OPL parcial por operario y semana.
    for j in range(datos.n_operarios):
        parciales_j = [p[i, j] for i in range(n_normales) if (i, j) in p]
        if parciales_j:
            model.add_at_most_one(parciales_j)

    # ── Capacidad por operario ───────────────────────────────────────────────
    for j in range(datos.n_operarios):
        vars_j  = [x[i, j] for i in range(datos.n_opls) if (i, j) in datos.experiencias]
        pesos_j = [datos.tiempos_articulo[i] for i in range(datos.n_opls) if (i, j) in datos.experiencias]
        mins_parciales_j = [m[i, j] for i in range(n_normales) if (i, j) in m]
        expr_cap = cp_model.LinearExpr.weighted_sum(vars_j, pesos_j)
        if mins_parciales_j:
            expr_cap = cp_model.LinearExpr.sum([expr_cap, cp_model.LinearExpr.sum(mins_parciales_j)])
        model.Add(expr_cap <= datos.capacidades[j])

    eff_activa = config.nivel_eficiencia > 0
    cota_eficiencia: Optional[float] = None
    valor_eficiencia: Optional[float] = None

    # ── Fase 1: BASE ────────────────────────────────────────────────────────
    solver = cp_model.CpSolver()
    expr_base = _construir_expresion_base(x, m, datos)
    model.maximize(expr_base)
    _configure_solver(solver, config, config.time_limit_base)
    _emit("BASE", "EJECUTANDO")
    status_base = solver.solve(model)
    _emit("BASE", _estado_texto(status_base))
    logger.info("Fase BASE: status=%d (%s), t=%.1fs", status_base, _estado_texto(status_base), solver.wall_time)

    if status_base not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        status = status_base
        estado_eficiencia_txt = "NO_EJECUTADA"
        estado_equidad_peso_txt = "NO_EJECUTADA"
        estado_equidad_art_txt = "NO_EJECUTADA"
        _emit("EFICIENCIA", "NO_EJECUTADA")
        _emit("EQUIDAD_PESO", "NO_EJECUTADA")
        _emit("EQUIDAD_ARTICULOS", "NO_EJECUTADA")
    else:
        # Fijar minutos de la base para fases posteriores.
        # OPTIMAL → igualdad exacta; FEASIBLE → >= para no degradar.
        base_best = (
            int(solver.best_objective_bound) if status_base == cp_model.OPTIMAL
            else int(round(solver.objective_value))
        )
        if status_base == cp_model.OPTIMAL:
            model.Add(expr_base == base_best)
        else:
            model.Add(expr_base >= base_best)

        # ── Fase 2: EFICIENCIA ────────────────────────────────────────────
        if not eff_activa:
            status = status_base
            estado_eficiencia_txt = "NO_EJECUTADA"
            _emit("EFICIENCIA", "NO_EJECUTADA")
        else:
            solver_prev = solver
            expr_eficiencia = _construir_expresion_eficiencia(x, p, datos)
            _add_hints_from_solution(model, solver_prev, x, p, m)
            model.maximize(expr_eficiencia)
            solver2 = cp_model.CpSolver()
            _configure_solver(solver2, config, config.time_limit_eficiencia)
            _emit("EFICIENCIA", "EJECUTANDO")
            status2 = solver2.solve(model)
            logger.info("Fase EFICIENCIA: status=%d (%s), obj=%.0f, t=%.1fs",
                        status2, _estado_texto(status2),
                        solver2.objective_value if status2 in (cp_model.OPTIMAL, cp_model.FEASIBLE) else 0,
                        solver2.wall_time)

            if status2 not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                solver = solver_prev
                status = status_base
                estado_eficiencia_txt = "DESCONOCIDO"
            else:
                solver = solver2
                status = status2
                estado_eficiencia_txt = _estado_texto(status2)
                valor_eficiencia = float(solver2.objective_value)
                cota_eficiencia = float(solver2.best_objective_bound)
                # Fijar cualificadas de forma rígida (==); son el criterio más importante
                # y nunca deben degradarse en fases de equidad.
                cualificadas_vars = [var for (i, j), var in list(x.items()) + list(p.items())
                                     if (i, j) in datos.cualificados]
                if cualificadas_vars:
                    cualificadas_best = sum(solver2.value(v) for v in cualificadas_vars)
                    model.Add(cp_model.LinearExpr.sum(cualificadas_vars) == cualificadas_best)
                # Fijar expresión de eficiencia (exp+speed) con delta de relajación
                eff_best = (int(solver2.best_objective_bound) if status2 == cp_model.OPTIMAL
                            else int(round(solver2.objective_value)))
                eff_floor = int(round(eff_best * (1.0 - config.delta_eficiencia)))
                model.Add(expr_eficiencia >= eff_floor)
            _emit("EFICIENCIA", estado_eficiencia_txt)

        # ── Fase 3: EQUIDAD_PESO ──────────────────────────────────────────
        if config.nivel_equidad_peso <= 0:
            estado_equidad_peso_txt = "NO_EJECUTADA"
            _emit("EQUIDAD_PESO", "NO_EJECUTADA")
        else:
            expr_equidad_peso = _construir_expr_equidad_peso(model, x, m, datos)
            _add_hints_from_solution(model, solver, x, p, m)
            model.maximize(expr_equidad_peso)
            solver_ep = cp_model.CpSolver()
            _configure_solver(solver_ep, config, config.time_limit_equidad_peso)
            _emit("EQUIDAD_PESO", "EJECUTANDO")
            status_ep = solver_ep.solve(model)
            logger.info("Fase EQUIDAD_PESO: status=%d (%s), t=%.1fs",
                        status_ep, _estado_texto(status_ep), solver_ep.wall_time)
            if status_ep in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                solver = solver_ep
                estado_equidad_peso_txt = _estado_texto(status_ep)
                # Fijar para fase de artículos con delta de relajación.
                # expr_equidad_peso = m_p - M_p  (≤ 0; 0 = equidad perfecta).
                # Multiplicar por (1 + delta) hace el floor más negativo, permitiendo
                # un gap de kg algo mayor al optimizar artículos.
                eq_peso_best = (int(solver_ep.best_objective_bound) if status_ep == cp_model.OPTIMAL
                                else int(round(solver_ep.objective_value)))
                eq_peso_floor = int(round(eq_peso_best * (1.0 + config.delta_equidad_peso)))
                model.Add(expr_equidad_peso >= eq_peso_floor)
            else:
                estado_equidad_peso_txt = "DESCONOCIDO"
            _emit("EQUIDAD_PESO", estado_equidad_peso_txt)

        # ── Fase 4: EQUIDAD_ARTICULOS ─────────────────────────────────────
        if config.nivel_equidad_articulos <= 0:
            estado_equidad_art_txt = "NO_EJECUTADA"
            _emit("EQUIDAD_ARTICULOS", "NO_EJECUTADA")
        else:
            expr_equidad_art = _construir_expr_equidad_articulos(model, x, m, datos)
            _add_hints_from_solution(model, solver, x, p, m)
            model.maximize(expr_equidad_art)
            solver_ea = cp_model.CpSolver()
            _configure_solver(solver_ea, config, config.time_limit_equidad_articulos)
            _emit("EQUIDAD_ARTICULOS", "EJECUTANDO")
            status_ea = solver_ea.solve(model)
            logger.info("Fase EQUIDAD_ARTICULOS: status=%d (%s), t=%.1fs",
                        status_ea, _estado_texto(status_ea), solver_ea.wall_time)
            if status_ea in (cp_model.OPTIMAL, cp_model.FEASIBLE):
                solver = solver_ea
                estado_equidad_art_txt = _estado_texto(status_ea)
            else:
                estado_equidad_art_txt = "DESCONOCIDO"
            _emit("EQUIDAD_ARTICULOS", estado_equidad_art_txt)

    estado = _estado_texto(status)
    estado_base_txt = _estado_texto(status_base)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return ResultadoAsignacion(
            estado=estado,
            estado_base=estado_base_txt,
            estado_eficiencia=estado_eficiencia_txt,
            estado_equidad_peso=estado_equidad_peso_txt,
            estado_equidad_articulos=estado_equidad_art_txt,
            asignaciones={},
            tiempos_asignados={},
            no_asignadas=[],
            cargas={},
        )

    # ── Extraer solución ─────────────────────────────────────────────────────
    asignaciones: dict = {}
    tiempos_asignados: dict = {}
    cargas: dict = {datos.dnis_operarios[j]: 0 for j in range(datos.n_operarios)}

    for i in range(datos.n_opls):
        for j in range(datos.n_operarios):
            if (i, j) in x and solver.value(x[i, j]):
                id_opl = datos.ids_opls[i]
                dni = datos.dnis_operarios[j]
                minutos = int(datos.tiempos_articulo[i])
                asignaciones[id_opl] = dni
                tiempos_asignados[id_opl] = minutos
                cargas[dni] += minutos
                break
            if (i, j) in p and solver.value(p[i, j]):
                id_opl = datos.ids_opls[i]
                dni = datos.dnis_operarios[j]
                minutos = int(solver.value(m[i, j]))
                asignaciones[id_opl] = dni
                tiempos_asignados[id_opl] = minutos
                cargas[dni] += minutos
                break

    no_asignadas = [
        datos.ids_opls[i]
        for i in range(datos.n_opls)
        if i not in datos.obligatorias
        and datos.ids_opls[i] not in asignaciones
    ]

    return ResultadoAsignacion(
        estado=estado,
        estado_base=estado_base_txt,
        estado_eficiencia=estado_eficiencia_txt,
        estado_equidad_peso=estado_equidad_peso_txt,
        estado_equidad_articulos=estado_equidad_art_txt,
        asignaciones=asignaciones,
        tiempos_asignados=tiempos_asignados,
        no_asignadas=no_asignadas,
        cargas=cargas,
        cota_eficiencia=cota_eficiencia,
        valor_eficiencia=valor_eficiencia,
    )
