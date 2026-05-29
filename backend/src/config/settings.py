"""
Configuración global del sistema de optimización de OPLs.
"""

import os
import warnings
from pathlib import Path
from dotenv import load_dotenv

# Directorio raíz del proyecto
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Cargar .env si existe (no falla si no está)
load_dotenv(BASE_DIR / ".env")

# ── Entorno ────────────────────────────────────────────────────────────────────
# Valores: "development" (default) | "production"
ENV: str = os.environ.get("ENV", "development").lower()
IS_PRODUCTION: bool = ENV == "production"

# ── Base de datos ──────────────────────────────────────────────────────────────
# Default apunta al PostgreSQL del docker-compose.override.yml (desarrollo local).
# En producción, establecer DATABASE_URL en App Settings (Azure) o .env.
DATABASE_URL: str = os.environ.get(
    "DATABASE_URL",
    "postgresql://opl_user:dev_password@localhost:5432/opl_scheduler",
)

# BD separada para tests — se crea automáticamente en docker-compose dev
TEST_DATABASE_URL: str = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://opl_user:dev_password@localhost:5432/opl_scheduler_test",
)

# ── CORS ───────────────────────────────────────────────────────────────────────
# En producción: CORS_ORIGINS=https://tu-app.com,https://app-operarios.com
CORS_ORIGINS: list[str] = [
    o.strip()
    for o in os.environ.get("CORS_ORIGINS", "*").split(",")
    if o.strip()
]

if IS_PRODUCTION and (not CORS_ORIGINS or CORS_ORIGINS == ["*"]):
    raise RuntimeError(
        "CORS_ORIGINS no puede ser '*' ni estar vacío cuando ENV=production. "
        "Define dominios explícitos separados por coma."
    )

# ── Autenticación JWT ──────────────────────────────────────────────────────────
# Generar clave segura: python -c "import secrets; print(secrets.token_hex(32))"
_jwt_secret = os.environ.get("JWT_SECRET_KEY")
if _jwt_secret is None:
    if IS_PRODUCTION:
        raise RuntimeError(
            "JWT_SECRET_KEY obligatorio cuando ENV=production. "
            "Genera con: python -c 'import secrets; print(secrets.token_hex(32))'"
        )
    warnings.warn(
        "JWT_SECRET_KEY no configurado — usando clave insegura de desarrollo. "
        "Establece JWT_SECRET_KEY en .env antes de desplegar.",
        stacklevel=2,
    )
    _jwt_secret = "dev-insecure-secret-change-in-prod"

JWT_SECRET_KEY: str = _jwt_secret
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 8  # 8 horas (una jornada laboral)

# ── Bootstrap admin ────────────────────────────────────────────────────────────
# Password inicial del usuario 'admin'. Solo se aplica si la BD está vacía (primer
# arranque). Cambiar después por la API. En producción establecer en App Settings.
ADMIN_BOOTSTRAP_PASSWORD: str = os.environ.get("ADMIN_BOOTSTRAP_PASSWORD", "admin1234")

if IS_PRODUCTION and ADMIN_BOOTSTRAP_PASSWORD == "admin1234":
    warnings.warn(
        "ADMIN_BOOTSTRAP_PASSWORD usa el valor por defecto en producción. "
        "Define una contraseña fuerte y cámbiala tras el primer login.",
        stacklevel=2,
    )
