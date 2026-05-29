"""Estado global del solver en memoria (un único solver activo por proceso API)."""

from __future__ import annotations

import threading
import time
from datetime import date
from typing import Any, Optional


class _SolverState:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._reset()

    def _reset(self) -> None:
        self.semana: Optional[date] = None
        self.proceso = None
        self.inicio_ts: Optional[float] = None
        self.fase: str = "SIN_DATOS"
        self.estado: str = "SIN_DATOS"
        self.fases: dict[str, str] = {
            "base": "SIN_DATOS",
            "eficiencia": "SIN_DATOS",
            "equidad_peso": "SIN_DATOS",
            "equidad_articulos": "SIN_DATOS",
        }
        self.config: Optional[dict[str, Any]] = None
        self.resultado: Optional[dict[str, Any]] = None
        self.error: Optional[str] = None
        self.terminado: bool = False
        self.ejecutando: bool = False

    def is_running(self) -> bool:
        with self._lock:
            return self.ejecutando

    def iniciar(
        self,
        semana: date,
        proceso,
        config: dict[str, Any],
        fases_activas: dict[str, bool],
    ) -> None:
        with self._lock:
            self.semana = semana
            self.proceso = proceso
            self.inicio_ts = time.time()
            self.fase = "BASE"
            self.estado = "PENDIENTE"
            self.fases = {
                "base": "PENDIENTE",
                "eficiencia": "PENDIENTE" if fases_activas.get("eficiencia") else "NO_EJECUTADA",
                "equidad_peso": "PENDIENTE" if fases_activas.get("equidad_peso") else "NO_EJECUTADA",
                "equidad_articulos": "PENDIENTE" if fases_activas.get("equidad_articulos") else "NO_EJECUTADA",
            }
            self.config = config
            self.resultado = None
            self.error = None
            self.terminado = False
            self.ejecutando = True

    def actualizar_fase(self, fase: str, estado: str) -> None:
        with self._lock:
            fase_l = fase.lower()
            if fase_l in self.fases:
                self.fases[fase_l] = estado
            self.fase = fase
            self.estado = estado

    def finalizar_exito(self, resultado_dict: dict[str, Any]) -> None:
        with self._lock:
            self.resultado = resultado_dict
            self.ejecutando = False
            self.terminado = True

    def finalizar_error(self, mensaje: str) -> None:
        with self._lock:
            self.error = mensaje
            self.ejecutando = False
            self.terminado = True

    def reset_semana(self, semana: date) -> None:
        """Limpia el resultado cacheado de una semana (para mutaciones manuales)."""
        with self._lock:
            if self.resultado is not None and self.semana == semana and not self.ejecutando:
                self.resultado = None

    def snapshot_progreso(self) -> dict[str, Any]:
        with self._lock:
            return {
                "fase": self.fase,
                "estado": self.estado,
                "ejecutando": self.ejecutando,
                "terminado": self.terminado,
                "inicio_ts": self.inicio_ts,
                "error": self.error,
                "config": self.config,
                "fases": dict(self.fases),
            }

    def snapshot_estado_global(self) -> dict[str, Any]:
        with self._lock:
            return {
                "semana_en_curso": self.semana if self.ejecutando else None,
                "fase": self.fase if self.ejecutando else None,
                "estado": self.estado if self.ejecutando else None,
                "inicio_ts": self.inicio_ts if self.ejecutando else None,
                "n_opls": (self.config or {}).get("n_opls") if self.ejecutando else None,
            }

    def get_resultado(self, semana: date) -> Optional[dict[str, Any]]:
        with self._lock:
            if self.semana == semana:
                return self.resultado
            return None


SOLVER_STATE = _SolverState()
