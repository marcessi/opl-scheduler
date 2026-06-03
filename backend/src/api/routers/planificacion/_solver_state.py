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
        self.cancelado: bool = False

    def is_running(self) -> bool:
        """Indica si hay una optimización en curso.

        Returns:
            ``True`` si el solver está ejecutándose, ``False`` en caso contrario.
        """
        with self._lock:
            return self.ejecutando

    def iniciar(
        self,
        semana: date,
        proceso,
        config: dict[str, Any],
        fases_activas: dict[str, bool],
    ) -> None:
        """Registra el arranque de una optimización y reinicia el estado de fases.

        Args:
            semana: Semana que se está optimizando.
            proceso: Subproceso (``multiprocessing.Process``) que ejecuta el solver.
            config: Configuración del solver, expuesta luego en el progreso.
            fases_activas: Qué fases están activas; las inactivas se marcan
                directamente como ``NO_EJECUTADA``.
        """
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
            self.cancelado = False

    def actualizar_fase(self, fase: str, estado: str) -> None:
        """Actualiza el estado de una fase concreta y el estado global actual.

        Args:
            fase: Nombre de la fase (BASE, EFICIENCIA, EQUIDAD_PESO, ...).
            estado: Nuevo estado de la fase (EJECUTANDO, OPTIMA, ...).
        """
        with self._lock:
            fase_l = fase.lower()
            if fase_l in self.fases:
                self.fases[fase_l] = estado
            self.fase = fase
            self.estado = estado

    def finalizar_exito(self, resultado_dict: dict[str, Any]) -> None:
        """Marca la optimización como terminada con éxito y cachea su resultado.

        Args:
            resultado_dict: Resultado serializado del solver para esta semana.
        """
        with self._lock:
            self.resultado = resultado_dict
            self.ejecutando = False
            self.terminado = True

    def finalizar_error(self, mensaje: str) -> None:
        """Marca la optimización como terminada con error.

        Args:
            mensaje: Descripción del error producido.
        """
        with self._lock:
            self.error = mensaje
            self.ejecutando = False
            self.terminado = True

    def solicitar_cancelacion(self):
        """Marca la optimización en curso como cancelada y devuelve su subproceso.

        El subproceso se devuelve para que el llamante lo termine fuera del lock.

        Returns:
            El ``multiprocessing.Process`` activo, o ``None`` si no hay ninguna
            optimización en curso que cancelar.
        """
        with self._lock:
            if not self.ejecutando:
                return None
            self.cancelado = True
            return self.proceso

    def finalizar_cancelado(self) -> None:
        """Marca la optimización como terminada por cancelación del usuario.

        No deja error ni resultado: la BD no se ha modificado, así que la app
        vuelve al estado previo al lanzamiento.
        """
        with self._lock:
            self.fase = "CANCELADO"
            self.estado = "CANCELADO"
            self.resultado = None
            self.error = None
            self.ejecutando = False
            self.terminado = True

    def reset_semana(self, semana: date) -> None:
        """Limpia el resultado cacheado de una semana (para mutaciones manuales)."""
        with self._lock:
            if self.resultado is not None and self.semana == semana and not self.ejecutando:
                self.resultado = None

    def snapshot_progreso(self) -> dict[str, Any]:
        """Captura el progreso detallado de la optimización actual.

        Returns:
            Diccionario con fase y estado actuales, banderas de ejecución/fin,
            timestamp de inicio, posible error, configuración y estado por fase.
        """
        with self._lock:
            return {
                "fase": self.fase,
                "estado": self.estado,
                "ejecutando": self.ejecutando,
                "terminado": self.terminado,
                "cancelado": self.cancelado,
                "inicio_ts": self.inicio_ts,
                "error": self.error,
                "config": self.config,
                "fases": dict(self.fases),
            }

    def snapshot_estado_global(self) -> dict[str, Any]:
        """Captura un resumen del solver para el estado global de la app.

        Returns:
            Diccionario con la semana en curso y su progreso, o campos a ``None``
            si no hay ninguna optimización ejecutándose.
        """
        with self._lock:
            return {
                "semana_en_curso": self.semana if self.ejecutando else None,
                "fase": self.fase if self.ejecutando else None,
                "estado": self.estado if self.ejecutando else None,
                "inicio_ts": self.inicio_ts if self.ejecutando else None,
                "n_opls": (self.config or {}).get("n_opls") if self.ejecutando else None,
            }

    def get_resultado(self, semana: date) -> Optional[dict[str, Any]]:
        """Devuelve el resultado cacheado de una semana, si corresponde.

        Args:
            semana: Semana cuyo resultado se solicita.

        Returns:
            El resultado serializado si coincide con la última semana optimizada,
            o ``None`` en caso contrario.
        """
        with self._lock:
            if self.semana == semana:
                return self.resultado
            return None


SOLVER_STATE = _SolverState()
