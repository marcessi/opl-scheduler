"""Tests de la cancelación de optimizaciones en curso.

Cubren la máquina de estados de ``_SolverState`` y el endpoint ``/cancelar``,
sin lanzar un solver real (se usa un subproceso simulado).
"""

from datetime import date

import pytest

from src.api.routers.planificacion._solver_state import _SolverState, SOLVER_STATE
from src.api.routers.planificacion.optimizacion import cancel_optimization
from src.exceptions import ConflictError


class _FakeProc:
    """Subproceso simulado: registra terminate() y reporta su vida."""

    def __init__(self) -> None:
        self.alive = True
        self.terminado = False

    def is_alive(self) -> bool:
        return self.alive

    def terminate(self) -> None:
        self.terminado = True
        self.alive = False


SEMANA = date(2026, 6, 8)
CONFIG = {"n_opls": 3, "perfil": "balanceado", "tiempo_maximo_min": 5}
FASES = {"eficiencia": True, "equidad_peso": True, "equidad_articulos": False}


def _estado_en_curso() -> tuple[_SolverState, _FakeProc]:
    estado = _SolverState()
    proc = _FakeProc()
    estado.iniciar(SEMANA, proc, CONFIG, FASES)
    return estado, proc


# ── Máquina de estados ───────────────────────────────────────────


def test_solicitar_cancelacion_sin_solver_devuelve_none():
    estado = _SolverState()
    assert estado.solicitar_cancelacion() is None
    assert estado.cancelado is False


def test_solicitar_cancelacion_marca_flag_y_devuelve_proceso():
    estado, proc = _estado_en_curso()

    devuelto = estado.solicitar_cancelacion()

    assert devuelto is proc
    assert estado.cancelado is True
    # Aún no finalizado: el supervisor lo cerrará al ver el proceso muerto.
    assert estado.is_running() is True


def test_finalizar_cancelado_deja_estado_limpio():
    estado, _ = _estado_en_curso()
    estado.solicitar_cancelacion()

    estado.finalizar_cancelado()

    assert estado.estado == "CANCELADO"
    assert estado.fase == "CANCELADO"
    assert estado.is_running() is False
    assert estado.terminado is True
    assert estado.resultado is None
    assert estado.error is None


def test_iniciar_limpia_cancelado_previo():
    estado, _ = _estado_en_curso()
    estado.solicitar_cancelacion()
    estado.finalizar_cancelado()

    estado.iniciar(SEMANA, _FakeProc(), CONFIG, FASES)

    assert estado.cancelado is False


def test_snapshot_progreso_expone_cancelado():
    estado, _ = _estado_en_curso()
    assert estado.snapshot_progreso()["cancelado"] is False
    estado.solicitar_cancelacion()
    assert estado.snapshot_progreso()["cancelado"] is True


# ── Endpoint ─────────────────────────────────────────────────────


@pytest.fixture
def reset_solver_state():
    """Restaura el singleton global tras manipularlo en los tests del endpoint."""
    yield
    SOLVER_STATE._reset()  # noqa: SLF001


def test_cancelar_sin_optimizacion_en_curso_da_conflicto(reset_solver_state):
    SOLVER_STATE._reset()  # noqa: SLF001
    with pytest.raises(ConflictError):
        cancel_optimization(SEMANA)


def test_cancelar_otra_semana_da_conflicto(reset_solver_state):
    SOLVER_STATE._reset()  # noqa: SLF001
    SOLVER_STATE.iniciar(SEMANA, _FakeProc(), CONFIG, FASES)
    with pytest.raises(ConflictError):
        cancel_optimization(date(2026, 6, 15))


def test_cancelar_en_curso_termina_proceso(reset_solver_state):
    SOLVER_STATE._reset()  # noqa: SLF001
    proc = _FakeProc()
    SOLVER_STATE.iniciar(SEMANA, proc, CONFIG, FASES)

    resp = cancel_optimization(SEMANA)

    assert resp.status_code == 200
    assert proc.terminado is True
    assert SOLVER_STATE.cancelado is True
