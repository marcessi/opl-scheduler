"""
Modelos Pydantic para request/response de la API.
"""

from datetime import date, datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────────────────────────────────────
# Respuestas para GET /datos
# ─────────────────────────────────────────────────────────────────────────────

class FamiliaOut(BaseModel):
    descripcion: str
    experiencia_requerida: int


class ArticuloOut(BaseModel):
    referencia: str
    familia: str
    descripcion: str
    peso: float
    tiempo_estandar: float


class OperarioOut(BaseModel):
    dni: str
    nombre_completo: str
    horas_semanales: float


class OperarioFamiliaOut(BaseModel):
    dni_operario: str
    familia: str
    experiencia: int


class OperarioArticuloOut(BaseModel):
    ref_articulo: str
    dni_operario: str
    tiempo_estimado: float


class OplOut(BaseModel):
    id: str
    ref_articulo: str
    cantidad: int
    tiempo_estimado: float
    asignado_a: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# POST /carga
# ─────────────────────────────────────────────────────────────────────────────

class ImportEntityResult(BaseModel):
    importados: int
    omitidos: int
    razones: dict[str, int]


class CargaOut(BaseModel):
    familias: Optional[ImportEntityResult] = None
    articulos: Optional[ImportEntityResult] = None
    operarios: Optional[ImportEntityResult] = None
    operario_familia: Optional[ImportEntityResult] = None
    operario_articulo: Optional[ImportEntityResult] = None
    opls: Optional[ImportEntityResult] = None


# ─────────────────────────────────────────────────────────────────────────────
# Respuesta de optimización (usada en /repartos/{semana}/optimizar)
# ─────────────────────────────────────────────────────────────────────────────


class AsignacionItemOut(BaseModel):
    id_opl: str
    nombre_operario: str
    dni_operario: str
    tiempo_min: int


class CargaOperarioOut(BaseModel):
    nombre: str
    dni: str
    carga_min: int
    capacidad_min: int
    pct_utilizacion: int
    n_articulos: float = 0.0   # artículos proporcionales asignados esta semana
    peso_kg: float = 0.0       # kg proporcionales asignados esta semana


class MetricasOut(BaseModel):
    n_opls_totales: int
    n_asignadas: int
    n_optimas: int
    media_exp_no_optimos: Optional[float] = None
    media_tiempo_real: Optional[float] = None
    total_asignado_min: int
    total_capacidad_min: int
    pct_utilizacion_global: int


class ResultadoOut(BaseModel):
    estado: str
    estado_base: str
    estado_eficiencia: str
    estado_equidad_peso: str
    estado_equidad_articulos: str
    asignaciones: list[AsignacionItemOut]
    no_asignadas_sin_capacidad: list[str]
    no_asignadas_sin_candidato: list[str]
    cargas: list[CargaOperarioOut]
    metricas: MetricasOut


# ─────────────────────────────────────────────────────────────────────────────
# GET /repartos  y  GET /repartos/{semana}
# ─────────────────────────────────────────────────────────────────────────────

class AsignacionDetalleOut(BaseModel):
    id_opl: str
    ref_articulo: str
    nombre_articulo: str = ""
    ref_familia: str = ""
    cantidad: int
    tipo_asignacion: str
    es_fija: bool = False
    dni_operario: Optional[str] = None
    nombre_operario: Optional[str] = None
    tiempo_planificado: float
    tiempo_total_teorico: float
    es_optima: Optional[bool] = None


class RepartoResumenOut(BaseModel):
    semana: date
    aprobado: bool
    fecha_aprobacion: Optional[datetime] = None
    n_asignadas: int
    n_pendientes: int
    estado_base: Optional[str] = None
    estado_eficiencia: Optional[str] = None
    estado_equidad_peso: Optional[str] = None
    estado_equidad_articulos: Optional[str] = None
    modo_aprobacion: Optional[str] = None
    semana_destino: Optional[date] = None
    incluir_no_asignadas_en_arrastre: Optional[bool] = None
    obligatorias_forzadas: Optional[bool] = None
    validacion_errores: Optional[list[str]] = None
    validacion_advertencias: Optional[list[str]] = None
    limpieza_aplicada: Optional[bool] = None
    no_asignadas_eliminadas_origen: Optional[int] = None
    perfil: Optional[str] = None


class RepartoDetalleOut(BaseModel):
    semana: date
    aprobado: bool
    fecha_aprobacion: Optional[datetime] = None
    estado_base: Optional[str] = None
    estado_eficiencia: Optional[str] = None
    estado_equidad_peso: Optional[str] = None
    estado_equidad_articulos: Optional[str] = None
    asignaciones: list[AsignacionDetalleOut]


class EstadoOptimizacionOut(BaseModel):
    semana_en_curso: Optional[date] = None
    fase: Optional[str] = None
    estado: Optional[str] = None
    inicio_ts: Optional[float] = None
    n_opls: Optional[int] = None


# Modelo estándar de error para respuestas unificadas
class ErrorOut(BaseModel):
    error: str
    detail: str
    code: int


# ─────────────────────────────────────────────────────────────────────────────
# POST /repartos/{semana}/optimizar
# ─────────────────────────────────────────────────────────────────────────────

class PerfilDelta(str, Enum):
    produccion = "produccion"   # delta_eficiencia=2%, delta_equidad_peso=3%  — SLA, presión de output
    balanceado = "balanceado"   # delta_eficiencia=6%, delta_equidad_peso=5%  — operación estándar
    personas   = "personas"     # delta_eficiencia=10%, delta_equidad_peso=5% — equipos con fatiga/rotación


class OptimizarSemanaRequest(BaseModel):
    ids_opls: Optional[list[str]] = None  # None = todas las normales de la BD
    tiempo_maximo_min: int = Field(default=5, ge=1, le=15)
    perfil: PerfilDelta = PerfilDelta.balanceado


class ActualizarAsignacionRequest(BaseModel):
    dni_operario: Optional[str] = None
    es_fija: Optional[bool] = None


class AnadirAsignacionesRequest(BaseModel):
    ids_opls: list[str] = Field(min_length=1)


class AprobarSemanaRequest(BaseModel):
    semana_destino: date
    con_arrastre: bool = True
    incluir_no_asignadas_en_arrastre: bool = True
    forzar_obligatorias_pendientes: bool = False


class LimpiarSelectivoRequest(BaseModel):
    desfijar: bool = False
    normalizar_obligatorias: bool = False
    eliminar_arrastre: bool = False


class LimpiarSelectivoOut(BaseModel):
    semana: date
    desfijadas: int = 0
    normalizadas: int = 0
    arrastre_eliminados: int = 0


class OplCrearManualRequest(BaseModel):
    ref_articulo: str
    cantidad: int = Field(gt=0)
