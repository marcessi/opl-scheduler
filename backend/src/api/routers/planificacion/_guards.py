"""Dependencies de FastAPI que bloquean operaciones cuando hay un solver activo."""

from src.exceptions import ConflictError
from src.api.routers.planificacion._solver_state import SOLVER_STATE


def bloquear_si_solver_activo() -> None:
    """Lanza 409 si el solver está corriendo. Se aplica como `Depends(...)`."""
    if SOLVER_STATE.is_running():
        semana = SOLVER_STATE.semana
        raise ConflictError(
            f"Optimización en curso para semana {semana}. "
            "Las modificaciones de BD están temporalmente bloqueadas."
        )
