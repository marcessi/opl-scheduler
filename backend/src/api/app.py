"""
Instancia principal de la aplicación FastAPI.
"""

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from starlette import status
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
from src.exceptions import NotFoundError, ConflictError, DomainValidationError, AuthenticationError
from src.config import CORS_ORIGINS, BASE_DIR, IS_PRODUCTION
import logging


# Configure basic logging for the application
LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
logger = logging.getLogger("opl_scheduler")

from src.api.routers import health
from src.api.routers.auth import router as auth_router
from src.api.routers.datos_maestros import router as datos_maestros_router
from src.api.routers.importacion_exportacion import import_router, export_router
from src.api.routers.planificacion import router as planificacion_router
from src.database import init_db

app = FastAPI(
    title="OPL Scheduler API",
    description="API para gestión y optimización de repartos de OPLs",
    version="0.1.0",
)

# Trust X-Forwarded-* headers cuando hay un load balancer delante (Azure App
# Service, Nginx, etc.). Necesario para que request.url.scheme refleje 'https'
# y la generación de URLs absolutas funcione tras el reverse proxy.
if IS_PRODUCTION:
    app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

# CORS: configurable via CORS_ORIGINS en .env (default "*" en desarrollo)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup_event():
    """Inicializa la base de datos (crea tablas y usuario admin) al arrancar."""
    init_db()


app.include_router(auth_router)
app.include_router(health.router)
app.include_router(datos_maestros_router)
app.include_router(import_router)
app.include_router(export_router)
app.include_router(planificacion_router)


# ---------------------------
# Centralized error handlers
# ---------------------------


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Traduce ``HTTPException`` al formato de error JSON uniforme de la API."""
    logger.warning("HTTPException: %s %s", exc.status_code, exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "http_exception", "detail": str(exc.detail), "code": exc.status_code},
    )


@app.exception_handler(AuthenticationError)
async def authentication_error_handler(request: Request, exc: AuthenticationError):
    """Convierte ``AuthenticationError`` de dominio en una respuesta 401."""
    logger.info("AuthenticationError: %s", exc.message)
    return JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={"error": "unauthorized", "detail": exc.message, "code": status.HTTP_401_UNAUTHORIZED},
        headers={"WWW-Authenticate": "Bearer"},
    )


@app.exception_handler(NotFoundError)
async def not_found_domain_handler(request: Request, exc: NotFoundError):
    """Convierte ``NotFoundError`` de dominio en una respuesta 404."""
    logger.info("NotFoundError: %s", exc.message)
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"error": "not_found", "detail": exc.message, "code": status.HTTP_404_NOT_FOUND},
    )


@app.exception_handler(ConflictError)
async def conflict_domain_handler(request: Request, exc: ConflictError):
    """Convierte ``ConflictError`` de dominio en una respuesta 409."""
    logger.info("ConflictError: %s", exc.message)
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"error": "conflict", "detail": exc.message, "code": status.HTTP_409_CONFLICT},
    )


@app.exception_handler(DomainValidationError)
async def validation_domain_handler(request: Request, exc: DomainValidationError):
    """Convierte ``DomainValidationError`` de dominio en una respuesta 422."""
    logger.info("DomainValidationError: %s", exc.message)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"error": "domain_validation", "detail": exc.message, "code": status.HTTP_422_UNPROCESSABLE_ENTITY},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Da formato uniforme a los errores de validación de la petición (422)."""
    logger.warning("RequestValidationError: %s", exc.errors())
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "validation_error",
            "detail": "Invalid request data",
            "code": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "errors": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Captura cualquier excepción no controlada y responde con un 500 genérico."""
    logger.exception("Unhandled exception during request")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "internal_server_error", "detail": "Internal server error", "code": status.HTTP_500_INTERNAL_SERVER_ERROR},
    )


# ── Servir frontend compilado ──────────────────────────────────────────────────
# Solo activo si existe frontend/dist (producción o `npm run build` ejecutado).
# Las rutas de API definidas arriba tienen prioridad sobre este catch-all.
_DIST = BASE_DIR / "frontend" / "dist"

if _DIST.exists():
    _ASSETS = _DIST / "assets"
    if _ASSETS.exists():
        app.mount("/assets", StaticFiles(directory=_ASSETS), name="static-assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        """Sirve la SPA: devuelve el fichero estático pedido o ``index.html``.

        Catch-all de menor prioridad que las rutas de API; permite el routing del
        lado cliente devolviendo ``index.html`` cuando la ruta no es un fichero.
        """
        file = _DIST / full_path
        return FileResponse(file if file.is_file() else _DIST / "index.html")
