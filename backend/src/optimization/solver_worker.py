"""Punto de entrada del solver cuando corre en un subproceso aislado."""

from __future__ import annotations


def ejecutar_solver_en_subproceso(datos, config, cola_progreso) -> None:
    """Ejecuta el solver y publica eventos en `cola_progreso`.

    Eventos publicados (`dict` con clave `tipo`):
      - {"tipo": "fase", "fase": str, "estado": str}
      - {"tipo": "ok", "resultado": ResultadoAsignacion}
      - {"tipo": "error", "mensaje": str}

    Se importa `resolver` dentro de la función para no arrastrar OR-Tools al
    proceso padre cuando el subproceso usa el contexto `spawn`.
    """
    try:
        from src.optimization.solver import resolver

        def on_phase(fase: str, estado: str) -> None:
            try:
                cola_progreso.put({"tipo": "fase", "fase": fase, "estado": estado})
            except Exception:
                pass

        resultado = resolver(datos, config, on_phase_change=on_phase)
        cola_progreso.put({"tipo": "ok", "resultado": resultado})
    except Exception as e:  # noqa: BLE001
        try:
            cola_progreso.put({"tipo": "error", "mensaje": str(e)})
        except Exception:
            pass
