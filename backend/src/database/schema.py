"""
Definición del esquema de la base de datos.

Implementa el modelo de datos para el sistema de optimización de producción:
- Familia: Categoría de artículos con experiencia requerida
- Articulo: Productos a fabricar
- Operario: Trabajadores
- Operario_Familia: Experiencia de cada operario por familia
- Operario_Articulo: Matriz de tiempos por artículo
- OPL: Órdenes de producción (entrada del algoritmo)
- AsignacionOPL: Asignación de OPLs a operarios (salida del algoritmo)
- Reparto: Registro de ejecuciones del optimizador por semana (gate de aprobación)
"""

from typing import Optional
from enum import Enum as PyEnum
from sqlalchemy import Integer, String, Float, ForeignKey, CheckConstraint, Boolean, Date, DateTime, Enum
from sqlalchemy.orm import relationship, Mapped, mapped_column
from src.database.base import Base
from datetime import date, datetime


class Familia(Base):
    """Familia o categoría de artículos."""
    __tablename__ = "familias"

    descripcion: Mapped[str] = mapped_column(String, primary_key=True)
    experiencia_requerida: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relaciones
    articulos: Mapped[list["Articulo"]] = relationship(back_populates="familia_obj")
    operarios_familia: Mapped[list["Operario_Familia"]] = relationship(back_populates="familia_obj")

    # Constraints
    __table_args__ = (
        CheckConstraint('experiencia_requerida BETWEEN 1 AND 4', name='check_experiencia_requerida_1_4'),
    )

    def __repr__(self):
        return f"<Familia(descripcion='{self.descripcion}', experiencia_requerida={self.experiencia_requerida})>"


class Articulo(Base):
    """Artículo o producto a fabricar."""
    __tablename__ = "articulos"

    referencia: Mapped[str] = mapped_column(String, primary_key=True)
    familia: Mapped[str] = mapped_column(ForeignKey("familias.descripcion"), nullable=False)
    descripcion: Mapped[str] = mapped_column(String, nullable=False)
    peso: Mapped[float] = mapped_column(Float, nullable=False)
    tiempo_estandar: Mapped[float] = mapped_column(Float, nullable=False)

    # Relaciones
    familia_obj: Mapped["Familia"] = relationship(back_populates="articulos")
    habilidades: Mapped[list["Operario_Articulo"]] = relationship(back_populates="articulo")
    opls: Mapped[list["OPL"]] = relationship(back_populates="articulo")

    # Constraints
    __table_args__ = (
        CheckConstraint('peso > 0', name='check_peso_positivo'),
        CheckConstraint('tiempo_estandar > 0', name='check_tiempo_estandar_positivo'),
    )

    def __repr__(self):
        return f"<Articulo(referencia='{self.referencia}', familia='{self.familia}')>"


class Operario(Base):
    """Operario o trabajador de producción."""
    __tablename__ = "operarios"

    dni: Mapped[str] = mapped_column(String, primary_key=True)
    nombre_completo: Mapped[str] = mapped_column(String, nullable=False)
    horas_semanales: Mapped[float] = mapped_column(Float, nullable=False)

    # Relaciones
    habilidades: Mapped[list["Operario_Articulo"]] = relationship(back_populates="operario")
    asignaciones: Mapped[list["AsignacionOPL"]] = relationship(back_populates="operario")
    familias: Mapped[list["Operario_Familia"]] = relationship(back_populates="operario")

    # Constraints
    __table_args__ = (
        CheckConstraint('horas_semanales >= 0', name='check_capacidad_no_negativa'),
    )

    def __repr__(self):
        return f"<Operario(dni='{self.dni}', nombre='{self.nombre_completo}')>"


class Operario_Familia(Base):
    """Experiencia de un operario en una familia de artículos."""
    __tablename__ = "operario_familia"

    dni_operario: Mapped[str] = mapped_column(ForeignKey("operarios.dni"), primary_key=True)
    familia: Mapped[str] = mapped_column(ForeignKey("familias.descripcion"), primary_key=True)
    experiencia: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relaciones
    operario: Mapped["Operario"] = relationship(back_populates="familias")
    familia_obj: Mapped["Familia"] = relationship(back_populates="operarios_familia")

    # Constraints
    __table_args__ = (
        CheckConstraint('experiencia BETWEEN 1 AND 4', name='check_experiencia_1_4'),
    )

    def __repr__(self):
        return f"<Operario_Familia(operario='{self.dni_operario}', familia='{self.familia}', experiencia={self.experiencia})>"


class Operario_Articulo(Base):
    """Matriz de tiempos: tiempo estimado de cada operario para cada artículo."""
    __tablename__ = "operario_articulo"

    ref_articulo: Mapped[str] = mapped_column(ForeignKey("articulos.referencia"), primary_key=True)
    dni_operario: Mapped[str] = mapped_column(ForeignKey("operarios.dni"), primary_key=True)
    tiempo_estimado: Mapped[float] = mapped_column(Float, nullable=False)

    # Relaciones
    articulo: Mapped["Articulo"] = relationship(back_populates="habilidades")
    operario: Mapped["Operario"] = relationship(back_populates="habilidades")

    # Constraints
    __table_args__ = (
        CheckConstraint('tiempo_estimado > 0', name='check_tiempo_estimado_positivo'),
    )

    def __repr__(self):
        return f"<Operario_Articulo(articulo='{self.ref_articulo}', operario='{self.dni_operario}', tiempo={self.tiempo_estimado})>"


class OPL(Base):
    """Orden de Producción Local (entrada del algoritmo de optimización)."""
    __tablename__ = "opls"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    ref_articulo: Mapped[str] = mapped_column(ForeignKey("articulos.referencia"), nullable=False)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relaciones
    articulo: Mapped["Articulo"] = relationship(back_populates="opls")
    asignaciones: Mapped[list["AsignacionOPL"]] = relationship(back_populates="opl")

    # Constraints
    __table_args__ = (
        CheckConstraint('cantidad > 0', name='check_cantidad_positiva'),
    )

    def __repr__(self):
        return f"<OPL(id='{self.id}', articulo='{self.ref_articulo}', cantidad={self.cantidad})>"


class TipoAsignacion(str, PyEnum):
    """Tipos de asignación de OPL a operario."""
    NORMAL = "normal"          # Asignación corriente, reasignable en cada optimización
    OBLIGATORIA = "obligatoria"  # Debe asignarse completamente (INFACTIBLE si no cabe), reasignable
    ARRASTRE = "arrastre"      # Creada por aprobación automática (split parcial), siempre es_fija=True e inmutable


class AsignacionOPL(Base):
    """
    Asignación de OPL a operario (salida del algoritmo de optimización).

    Tipos:
    - NORMAL: Asignación corriente; reasignable. es_fija togglable.
    - OBLIGATORIA: Debe asignarse completamente (INFACTIBLE si no cabe); reasignable. es_fija togglable.
    - ARRASTRE: Creada por aprobación automática al partir una OPL entre semanas. Siempre es_fija=True e inmutable.

    es_fija=True: el solver descuenta su tiempo de la capacidad del operario sin reoptimizarla.
    es_fija=False: el solver la trata según su tipo (candidata libre u obligatoria).
    """
    __tablename__ = "asignaciones_opl"

    id_opl: Mapped[str] = mapped_column(ForeignKey("opls.id"), primary_key=True)
    semana: Mapped[date] = mapped_column(ForeignKey("repartos.semana"), primary_key=True)
    # Nullable: None en filas obligatorias no asignadas
    dni_operario: Mapped[Optional[str]] = mapped_column(ForeignKey("operarios.dni"), nullable=True)
    tipo_asignacion: Mapped[TipoAsignacion] = mapped_column(Enum(TipoAsignacion, native_enum=False), nullable=False, default=TipoAsignacion.NORMAL)
    # True → el solver descuenta capacidad sin reoptimizar. ARRASTRE siempre True; NORMAL/OBLIGATORIA togglable.
    es_fija: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    tiempo_planificado: Mapped[float] = mapped_column(Float, nullable=False)
    # Nullable: None en filas obligatorias no asignadas
    tiempo_estimado_operario: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    # Snapshot del tiempo total teórico en el momento de la asignación (cantidad * tiempo_estandar)
    tiempo_total_teorico: Mapped[float] = mapped_column(Float, nullable=False)
    # Contribución de equidad persistida por fila (reproducible históricamente)
    peso_aportado: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    n_articulos_aportados: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")

    # Relaciones
    opl: Mapped["OPL"] = relationship(back_populates="asignaciones")
    operario: Mapped[Optional["Operario"]] = relationship(back_populates="asignaciones")
    reparto: Mapped["Reparto"] = relationship(back_populates="asignaciones")

    # Constraints
    __table_args__ = (
        CheckConstraint('tiempo_estimado_operario > 0', name='check_tiempo_asignacion_positivo'),
        CheckConstraint('tiempo_planificado >= 0', name='check_tiempo_planificado_positivo'),
        CheckConstraint('tiempo_total_teorico > 0', name='check_tiempo_teorico_positivo'),
        CheckConstraint('peso_aportado >= 0', name='check_peso_aportado_no_negativo'),
        CheckConstraint('n_articulos_aportados >= 0', name='check_n_articulos_aportados_no_negativo'),
    )

    def __repr__(self):
        return f"<AsignacionOPL(opl='{self.id_opl}', operario='{self.dni_operario}', semana='{self.semana}', tipo={self.tipo_asignacion.value}, fija={self.es_fija})>"


class Reparto(Base):
    """
    Registro de una ejecución del optimizador para una semana.

    Actúa como gate de aprobación: las filas fijas de la semana siguiente solo se crean
    cuando el usuario aprueba el reparto (aprobar_reparto).

    Las OPLs incluidas en el reparto se derivan de AsignacionOPL WHERE semana=X AND fija=False.
    Las no asignadas tendrán dni_operario=None en esa tabla.
    """
    __tablename__ = "repartos"

    semana: Mapped[date] = mapped_column(Date, primary_key=True)
    aprobado: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fecha_aprobacion: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    # Estados de cada fase del solver tras la última ejecución del optimizador
    estado_base:              Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    estado_eficiencia:        Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    estado_equidad_peso:      Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    estado_equidad_articulos: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Cota teórica (best_objective_bound) y valor logrado de la fase EFICIENCIA
    cota_eficiencia:  Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    valor_eficiencia: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Modo (perfil) de la última ejecución del optimizador: produccion/balanceado/personas
    perfil: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # Relaciones
    asignaciones: Mapped[list["AsignacionOPL"]] = relationship(back_populates="reparto")

    def __repr__(self):
        return f"<Reparto(semana='{self.semana}', aprobado={self.aprobado})>"


class Usuario(Base):
    """Usuario del sistema con acceso al panel de administración."""
    __tablename__ = "usuarios"

    username: Mapped[str] = mapped_column(String(50), primary_key=True)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    def __repr__(self):
        return f"<Usuario(username='{self.username}')>"
