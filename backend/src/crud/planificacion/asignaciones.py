"""CRUD para AsignacionOPL.

Mutaciones puras: añade/elimina filas o muta atributos. No hace ``commit``.
Las validaciones de negocio (operario activo, reparto aprobado, ARRASTRE inmutable)
viven en la capa de servicios.
"""

from datetime import date
from typing import List, Optional
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session
from src.database.schema import (
    AsignacionOPL,
    Articulo,
    Familia,
    OPL,
    Operario,
    Operario_Familia,
    TipoAsignacion,
)


# ─── Lecturas ───────────────────────────────────────────────────────────────

def leer(session: Session, id_opl: str, semana: date) -> Optional[AsignacionOPL]:
    """Lee una asignación por su clave primaria compuesta.

    Args:
        session: Sesión de base de datos activa.
        id_opl: Identificador de la OPL.
        semana: Lunes ISO de la semana de la asignación.

    Returns:
        La ``AsignacionOPL`` correspondiente, o ``None`` si no existe.
    """
    return session.scalars(
        select(AsignacionOPL).where(
            AsignacionOPL.id_opl == id_opl,
            AsignacionOPL.semana == semana,
        )
    ).first()


def listar_por_opl(session: Session, id_opl: str) -> List[AsignacionOPL]:
    """Lista todas las asignaciones de una OPL ordenadas por semana.

    Args:
        session: Sesión de base de datos activa.
        id_opl: Identificador de la OPL.

    Returns:
        Lista de asignaciones (como máximo dos: semana actual y siguiente).
    """
    stmt = (
        select(AsignacionOPL)
        .where(AsignacionOPL.id_opl == id_opl)
        .order_by(AsignacionOPL.semana)
    )
    return list(session.scalars(stmt).all())


def listar_semana(session: Session, semana: date) -> List[AsignacionOPL]:
    """Lista todas las asignaciones de una semana.

    Args:
        session: Sesión de base de datos activa.
        semana: Lunes ISO de la semana.

    Returns:
        Lista de asignaciones de esa semana (cualquier tipo y estado).
    """
    return list(session.scalars(
        select(AsignacionOPL).where(AsignacionOPL.semana == semana)
    ).all())


def listar_semana_por_tipo(
    session: Session, semana: date, tipo: TipoAsignacion,
) -> List[AsignacionOPL]:
    """Lista las asignaciones de una semana filtrando por tipo.

    Args:
        session: Sesión de base de datos activa.
        semana: Lunes ISO de la semana.
        tipo: Tipo de asignación a filtrar (NORMAL, OBLIGATORIA o ARRASTRE).

    Returns:
        Lista de asignaciones de la semana con el tipo indicado.
    """
    return list(session.scalars(
        select(AsignacionOPL).where(
            AsignacionOPL.semana == semana,
            AsignacionOPL.tipo_asignacion == tipo,
        )
    ).all())


def listar_no_fijas_semana(session: Session, semana: date) -> List[AsignacionOPL]:
    """Lista las asignaciones reoptimizables (``es_fija=False``) de una semana.

    Args:
        session: Sesión de base de datos activa.
        semana: Lunes ISO de la semana.

    Returns:
        Lista de asignaciones que el solver puede reasignar libremente.
    """
    return list(session.scalars(
        select(AsignacionOPL).where(
            AsignacionOPL.semana == semana,
            AsignacionOPL.es_fija == False,  # noqa: E712
        )
    ).all())


def listar_fijas_con_operario_semana(session: Session, semana: date) -> List[AsignacionOPL]:
    """Lista las asignaciones fijas que ya tienen operario asignado.

    Sus minutos se descuentan de la capacidad del operario sin reoptimizarlas.

    Args:
        session: Sesión de base de datos activa.
        semana: Lunes ISO de la semana.

    Returns:
        Lista de asignaciones con ``es_fija=True`` y ``dni_operario`` no nulo.
    """
    return list(session.scalars(
        select(AsignacionOPL).where(
            AsignacionOPL.semana == semana,
            AsignacionOPL.es_fija == True,  # noqa: E712
            AsignacionOPL.dni_operario.is_not(None),
        )
    ).all())


def listar_obligatorias_semana(session: Session, semana: date) -> List[AsignacionOPL]:
    """Lista las asignaciones OBLIGATORIA aún reoptimizables de una semana.

    Args:
        session: Sesión de base de datos activa.
        semana: Lunes ISO de la semana.

    Returns:
        Lista de asignaciones OBLIGATORIA con ``es_fija=False``; el solver debe
        colocarlas sí o sí o el problema resulta infactible.
    """
    return list(session.scalars(
        select(AsignacionOPL).where(
            AsignacionOPL.semana == semana,
            AsignacionOPL.tipo_asignacion == TipoAsignacion.OBLIGATORIA,
            AsignacionOPL.es_fija == False,  # noqa: E712
        )
    ).all())


def ids_opls_asignadas_otras_semanas(session: Session, semana: date) -> set[str]:
    """Obtiene los ids de OPL que ya están asignados en semanas distintas.

    Sirve para excluir del reparto de una semana las OPLs comprometidas en otra.

    Args:
        session: Sesión de base de datos activa.
        semana: Lunes ISO de la semana que se está planificando.

    Returns:
        Conjunto de ids de OPL con asignación en cualquier semana ≠ ``semana``.
    """
    stmt = select(AsignacionOPL.id_opl).where(AsignacionOPL.semana != semana).distinct()
    return set(session.scalars(stmt).all())


def sumar_carga_operario_semana(
    session: Session,
    semana: date,
    dni_operario: str,
    excluir_id_opl: Optional[str] = None,
) -> int:
    """Suma de ``tiempo_planificado`` para un operario en una semana."""
    filas = session.scalars(
        select(AsignacionOPL).where(
            AsignacionOPL.semana == semana,
            AsignacionOPL.dni_operario == dni_operario,
        )
    ).all()
    return int(round(sum(f.tiempo_planificado for f in filas if f.id_opl != excluir_id_opl)))


def sumar_aportes_antes_de(session: Session, semana: date) -> dict[str, dict[str, float]]:
    """Suma de aportes (peso, n_articulos) por operario en semanas anteriores."""
    stmt = (
        select(
            AsignacionOPL.dni_operario,
            func.coalesce(func.sum(AsignacionOPL.peso_aportado), 0.0),
            func.coalesce(func.sum(AsignacionOPL.n_articulos_aportados), 0.0),
        )
        .where(
            AsignacionOPL.semana < semana,
            AsignacionOPL.dni_operario.is_not(None),
        )
        .group_by(AsignacionOPL.dni_operario)
    )
    return {
        dni: {"peso": float(peso), "articulos": float(articulos)}
        for dni, peso, articulos in session.execute(stmt).all()
        if dni is not None
    }


# Fila tipada usada por vista_reparto.construir_detalle.
def leer_detalle_semana(session: Session, semana: date) -> list[tuple]:
    """Devuelve filas (AsignacionOPL, OPL, Articulo, Familia.experiencia_requerida,
    Operario_Familia.experiencia, Operario.nombre_completo) para una semana.

    Una sola query con joins; sustituye la carga masiva previa por tablas completas.
    """
    stmt = (
        select(
            AsignacionOPL,
            OPL,
            Articulo,
            Familia.experiencia_requerida,
            Operario_Familia.experiencia,
            Operario.nombre_completo,
        )
        .join(OPL, OPL.id == AsignacionOPL.id_opl)
        .join(Articulo, Articulo.referencia == OPL.ref_articulo)
        .join(Familia, Familia.descripcion == Articulo.familia)
        .outerjoin(Operario, Operario.dni == AsignacionOPL.dni_operario)
        .outerjoin(
            Operario_Familia,
            and_(
                Operario_Familia.dni_operario == AsignacionOPL.dni_operario,
                Operario_Familia.familia == Articulo.familia,
            ),
        )
        .where(AsignacionOPL.semana == semana)
    )
    return list(session.execute(stmt).all())


# ─── Mutaciones simples (NO hacen commit) ───────────────────────────────────

def anadir(session: Session, asignacion: AsignacionOPL) -> None:
    """Marca una asignación para inserción (sin hacer ``commit``).

    Args:
        session: Sesión de base de datos activa.
        asignacion: Instancia a persistir.
    """
    session.add(asignacion)


def eliminar(session: Session, asignacion: AsignacionOPL) -> None:
    """Marca una asignación para borrado (sin hacer ``commit``).

    Args:
        session: Sesión de base de datos activa.
        asignacion: Instancia a eliminar.
    """
    session.delete(asignacion)


def eliminar_semana(
    session: Session,
    semana: date,
    *,
    solo_no_fijas: bool = False,
    solo_sin_operario: bool = False,
    solo_tipo: Optional[TipoAsignacion] = None,
) -> int:
    """Borrado selectivo de filas de una semana. Devuelve número de filas eliminadas."""
    stmt = select(AsignacionOPL).where(AsignacionOPL.semana == semana)
    if solo_no_fijas:
        stmt = stmt.where(AsignacionOPL.es_fija == False)  # noqa: E712
    if solo_sin_operario:
        stmt = stmt.where(AsignacionOPL.dni_operario.is_(None))
    if solo_tipo is not None:
        stmt = stmt.where(AsignacionOPL.tipo_asignacion == solo_tipo)
    filas = list(session.scalars(stmt).all())
    for fila in filas:
        session.delete(fila)
    return len(filas)


def desfijar_semana(session: Session, semana: date) -> int:
    """Pone es_fija=False en filas NORMAL/OBLIGATORIA fijadas. ARRASTRE intocable."""
    filas = list(session.scalars(
        select(AsignacionOPL).where(
            AsignacionOPL.semana == semana,
            AsignacionOPL.es_fija == True,  # noqa: E712
            AsignacionOPL.tipo_asignacion != TipoAsignacion.ARRASTRE,
        )
    ).all())
    for fila in filas:
        fila.es_fija = False
    return len(filas)


def normalizar_obligatorias_semana(session: Session, semana: date) -> int:
    """Cambia tipo_asignacion OBLIGATORIA → NORMAL en una semana."""
    filas = list(session.scalars(
        select(AsignacionOPL).where(
            AsignacionOPL.semana == semana,
            AsignacionOPL.tipo_asignacion == TipoAsignacion.OBLIGATORIA,
        )
    ).all())
    for fila in filas:
        fila.tipo_asignacion = TipoAsignacion.NORMAL
    return len(filas)
