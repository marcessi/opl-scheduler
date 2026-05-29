"""Router de planificación semanal."""

from fastapi import APIRouter
from .consulta import router as consulta_router
from .optimizacion import router as optimizacion_router
from .acciones import router as acciones_router

router = APIRouter()
router.include_router(consulta_router)
router.include_router(optimizacion_router)
router.include_router(acciones_router)
