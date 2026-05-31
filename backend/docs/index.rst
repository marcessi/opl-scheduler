OPLscheduler — Documentación del backend
==========================================

Referencia de la API interna del backend de **OPLscheduler**, el planificador
semanal de producción que asigna OPLs a operarios mediante programación con
restricciones (CP-SAT de OR-Tools).

La documentación se genera automáticamente a partir de los docstrings del
paquete ``src`` y está organizada por capas:

* **api** — FastAPI: routers, schemas Pydantic y manejo de excepciones.
* **services** — lógica de negocio que orquesta las reglas del dominio.
* **crud** — acceso a la base de datos (lecturas y mutaciones puras).
* **optimization** — carga del problema, validación y solver CP-SAT.
* **io** — importación y exportación de Excel.
* **database** — modelos SQLAlchemy y sesión.

.. toctree::
   :maxdepth: 2
   :caption: Referencia de la API

   api/modules

Índices
=======

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
