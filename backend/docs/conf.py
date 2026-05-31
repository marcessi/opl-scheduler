"""Configuración de Sphinx para la documentación del backend de OPLscheduler.

Genera un sitio HTML navegable (y PDF opcional) a partir de los docstrings
Google-style del paquete ``src``.
"""

import os
import sys

# El paquete se importa como ``src.*``; añadimos la raíz del backend (carpeta
# padre de docs/, que contiene src/) al path para que autodoc pueda importarlo.
sys.path.insert(0, os.path.abspath(".."))

# Variables de entorno mínimas para que ``src.config.settings`` se importe sin
# una base de datos real (autodoc solo necesita importar los módulos).
os.environ.setdefault("DATABASE_URL", "postgresql://docs:docs@localhost:5432/docs")
os.environ.setdefault("JWT_SECRET_KEY", "docs-build-secret")


# ── Proyecto ────────────────────────────────────────────────────────────────
project = "OPLscheduler — Backend"
author = "Marc Escribano"
copyright = "2026, Marc Escribano"
release = "0.1.0"
language = "es"

# ── Extensiones ─────────────────────────────────────────────────────────────
extensions = [
    "sphinx.ext.autodoc",      # extrae docstrings de los módulos
    "sphinx.ext.napoleon",     # entiende el estilo Google de los docstrings
    "sphinx.ext.viewcode",     # enlaza a "ver código fuente"
    "sphinx.ext.autosummary",  # tablas resumen de módulos/funciones
    "sphinx.ext.intersphinx",  # enlaces a la doc de librerías externas
]

autosummary_generate = True

# Napoleon: usamos secciones Args/Returns/Raises (Google), no NumPy.
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = False
napoleon_use_rtype = True

# Autodoc: ordena por aparición en el fuente y muestra type hints.
autodoc_member_order = "bysource"
autodoc_typehints = "description"
autodoc_default_options = {
    "members": True,
    "undoc-members": False,
    "show-inheritance": True,
    # Documenta solo lo definido en cada módulo, ignorando los re-exports de los
    # __init__ (evita "duplicate object description" para nombres reexportados).
    "ignore-module-all": True,
}

# Mockear dependencias pesadas/opcionales si no estuvieran instaladas al construir
# (en el contenedor sí lo están, pero esto da robustez fuera de él).
autodoc_mock_imports: list[str] = []

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "sqlalchemy": ("https://docs.sqlalchemy.org/en/20/", None),
    "fastapi": ("https://fastapi.tiangolo.com/", None),
}

# ── Salida HTML ─────────────────────────────────────────────────────────────
# Tema furo si está instalado; si no, cae al tema por defecto.
try:
    import furo  # noqa: F401
    html_theme = "furo"
except ModuleNotFoundError:
    html_theme = "alabaster"

html_title = "OPLscheduler · Backend"
templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
