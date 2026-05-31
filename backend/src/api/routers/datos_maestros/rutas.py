"""GET endpoints para consultar los datos maestros de la BD."""

from fastapi import APIRouter

from src.database import get_session
from src.services.datos_maestros import (
	familias as familia_service,
	articulos as articulo_service,
	operarios as operario_service,
	operario_familia as operario_familia_service,
	operario_articulo as operario_articulo_service,
)
from src.services.planificacion import opls as opl_service
from src.api.schemas import (
	FamiliaOut,
	ArticuloOut,
	OperarioOut,
	OperarioFamiliaOut,
	OperarioArticuloOut,
	OplOut,
	ErrorOut,
)

router = APIRouter()


@router.get("/familias", response_model=list[FamiliaOut], responses={500: {"model": ErrorOut}})
def get_familias():
	"""Lista todas las familias con su experiencia requerida."""
	with get_session() as session:
		return [
			FamiliaOut(descripcion=f.descripcion, experiencia_requerida=f.experiencia_requerida)
			for f in familia_service.leer_todas_familias(session)
		]


@router.get("/articulos", response_model=list[ArticuloOut], responses={500: {"model": ErrorOut}})
def get_articulos():
	"""Lista todos los artículos recorriendo familias, con peso y tiempo estándar."""
	with get_session() as session:
		articulos = []
		for f in familia_service.leer_todas_familias(session):
			for a in articulo_service.leer_articulos_por_familia(session, f.descripcion):
				articulos.append(ArticuloOut(
					referencia=a.referencia,
					familia=a.familia,
					descripcion=a.descripcion,
					peso=a.peso,
					tiempo_estandar=a.tiempo_estandar,
				))
		return articulos


@router.get("/operarios", response_model=list[OperarioOut], responses={500: {"model": ErrorOut}})
def get_operarios():
	"""Lista todos los operarios con su capacidad semanal en horas."""
	with get_session() as session:
		return [
			OperarioOut(dni=op.dni, nombre_completo=op.nombre_completo, horas_semanales=op.horas_semanales)
			for op in operario_service.leer_todos_operarios(session)
		]


@router.get("/operario-familia", response_model=list[OperarioFamiliaOut], responses={500: {"model": ErrorOut}})
def get_operario_familia():
	"""Lista las cualificaciones (experiencia por familia) de cada operario."""
	with get_session() as session:
		resultado = []
		for op in operario_service.leer_todos_operarios(session):
			for rel in operario_familia_service.leer_familias_de_operario(session, op.dni):
				resultado.append(OperarioFamiliaOut(
					dni_operario=rel.dni_operario,
					familia=rel.familia,
					experiencia=rel.experiencia,
				))
		return resultado


@router.get("/operario-articulo", response_model=list[OperarioArticuloOut], responses={500: {"model": ErrorOut}})
def get_operario_articulo():
	"""Lista los tiempos específicos por artículo definidos para cada operario."""
	with get_session() as session:
		resultado = []
		for op in operario_service.leer_todos_operarios(session):
			for t in operario_articulo_service.leer_articulos_de_operario(session, op.dni):
				resultado.append(OperarioArticuloOut(
					ref_articulo=t.ref_articulo,
					dni_operario=t.dni_operario,
					tiempo_estimado=t.tiempo_estimado,
				))
		return resultado


@router.get("/opls", response_model=list[OplOut], responses={500: {"model": ErrorOut}})
def get_opls():
	"""Lista todas las OPLs con su tiempo estimado y el operario asignado, si lo hay."""
	with get_session() as session:
		resultado = []
		for opl in opl_service.leer_todas_opls(session):
			asigs = opl.asignaciones
			dnis = list(dict.fromkeys(
				a.dni_operario for a in asigs if a.dni_operario is not None
			))
			asignado_a = dnis[0] if dnis else None
			resultado.append(OplOut(
				id=opl.id,
				ref_articulo=opl.ref_articulo,
				cantidad=opl.cantidad,
				tiempo_estimado=round(opl.cantidad * opl.articulo.tiempo_estandar),
				asignado_a=asignado_a,
			))
		return resultado


@router.get("/resumen", responses={500: {"model": ErrorOut}})
def get_resumen():
	"""Devuelve el número de registros de cada entidad."""
	with get_session() as session:
		return {
			"familias":          familia_service.contar_familias(session),
			"articulos":         articulo_service.contar_articulos(session),
			"operarios":         operario_service.contar_operarios(session),
			"operario_familia":  operario_familia_service.contar_operario_familia(session),
			"operario_articulo": operario_articulo_service.contar_operario_articulo(session),
			"opls":              opl_service.contar_opls(session),
		}
