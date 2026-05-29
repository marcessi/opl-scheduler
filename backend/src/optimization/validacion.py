"""
Modulo de validaciones de reglas de negocio.
"""

from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import select
from src.database.schema import Operario
from src.optimization.cargador_problema import ProblemaAsignacion
from src.services.planificacion import opls as opl_service


class ResultadoValidacion:
    """Resultado de una validacion con detalles de errores y advertencias."""

    def __init__(self):
        self.valido = True
        self.errores: List[str] = []

    def agregar_error(self, mensaje: str):
        """Agrega un error critico que impide continuar."""
        self.valido = False
        self.errores.append(mensaje)

    def __str__(self) -> str:
        estado = "VALIDO" if self.valido else "INVALIDO"
        texto = [f"Validacion: {estado}"]

        if self.errores:
            texto.append(f"\nErrores ({len(self.errores)}):")
            for i, error in enumerate(self.errores, 1):
                texto.append(f"  {i}. {error}")

        return "\n".join(texto)


def validar_opls(session: Session, ids_opls: List[str]) -> ResultadoValidacion:
    """
    Punto de entrada del validator.

    Solo comprueba las condiciones que el solver no puede resolver por si mismo:
      1. Todos los IDs de OPL existen en la BD.
      2. Hay al menos un operario registrado.

    Cualquier otra situacion (sin cualificados, sin tiempo estimado,
    capacidad insuficiente...) se refleja como INFACTIBLE o resultado
    suboptimo devuelto directamente por el solver.

    Args:
        session:    Sesion de SQLAlchemy.
        ids_opls:   Lista de IDs de OPL a repartir.

    Returns:
        ResultadoValidacion con errores si alguna condicion falla.
    """
    resultado = ResultadoValidacion()

    # 1. Cada OPL existe en la BD
    for id_opl in ids_opls:
        if not opl_service.leer_opl(session, id_opl):
            resultado.agregar_error(f"No existe ninguna OPL con ID '{id_opl}'")

    if not resultado.valido:
        return resultado

    # 2. Hay al menos un operario activo (horas_semanales > 0)
    if not session.scalars(select(Operario).where(Operario.horas_semanales > 0)).first():
        resultado.agregar_error("No hay operarios activos en la base de datos (horas_semanales > 0)")

    return resultado


def validar_datos_problema(datos: ProblemaAsignacion) -> ResultadoValidacion:
    """
    Validaciones sobre el problema ya cargado para evitar ejecutar el solver
    en casos estructuralmente inválidos.

    Comprueba:
      1. Hay al menos una OPL a repartir.
      2. Hay al menos un operario activo cargado.
    """
    resultado = ResultadoValidacion()

    if datos.n_opls == 0:
        resultado.agregar_error("No hay OPLs disponibles para repartir")
        return resultado

    if datos.n_operarios == 0:
        resultado.agregar_error("No hay operarios activos para el reparto semanal (horas_semanales > 0)")
        return resultado

    return resultado
