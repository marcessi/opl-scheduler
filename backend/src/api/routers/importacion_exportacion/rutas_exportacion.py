"""GET /exportar/excel para exportar entidades maestras en Excel."""

import io

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from src.exceptions import DomainValidationError

from src.database import get_session
from src.io.excel_datos_maestros import ESQUEMA, exportar_entidades
from src.api.schemas import ErrorOut

router = APIRouter()
export_router = router

_ENTIDADES_VALIDAS = set(ESQUEMA.keys())


@router.get("/exportar/excel", responses={422: {"model": ErrorOut}, 500: {"model": ErrorOut}})
def exportar_excel(
	entidades: list[str] = Query(default=[]),
):
	"""Descarga un fichero Excel con las entidades seleccionadas."""
	invalidas = set(entidades) - _ENTIDADES_VALIDAS
	if invalidas:
		raise DomainValidationError(
			f"Entidades no reconocidas: {sorted(invalidas)}. "
			f"Valores válidos: {sorted(_ENTIDADES_VALIDAS)}"
		)

	seleccionadas = entidades or None

	buffer = io.BytesIO()
	with get_session() as session:
		exportar_entidades(session, buffer, seleccionadas)
	buffer.seek(0)

	return StreamingResponse(
		buffer,
		media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
		headers={"Content-Disposition": "attachment; filename=datos.xlsx"},
	)
