<div align="center">

# 🏭 OPLscheduler

**Planificador semanal de producción que asigna OPLs (Órdenes de Producción) a operarios mediante programación con restricciones.**

Optimiza el reparto de carga de trabajo respetando cualificaciones, capacidad y equidad, usando el motor [Google OR-Tools CP-SAT](https://developers.google.com/optimization/cp/cp_solver).

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16-4169E1?logo=postgresql&logoColor=white)
![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?logo=typescript&logoColor=white)
![OR-Tools](https://img.shields.io/badge/OR--Tools-CP--SAT-EA4335?logo=google&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?logo=docker&logoColor=white)
![Licencia](https://img.shields.io/badge/Licencia-MIT-green)

</div>

---

## 📋 Índice

- [¿Qué resuelve?](#-qué-resuelve)
- [Arranque rápido](#-arranque-rápido)
- [Cómo funciona el optimizador](#-cómo-funciona-el-optimizador)
- [Flujo de uso](#-flujo-de-uso)
- [Arquitectura](#-arquitectura)
- [Modelo de dominio](#-modelo-de-dominio)
- [API](#-api)
- [Tests](#-tests)
- [Documentación del código](#-documentación-del-código)
- [Desarrollo](#-desarrollo)
- [Despliegue en producción](#-despliegue-en-producción)
- [Estructura del proyecto](#-estructura-del-proyecto)
- [Stack tecnológico](#-stack-tecnológico)
- [Licencia](#-licencia)

---

## 🎯 ¿Qué resuelve?

Cada semana hay que decidir **qué operario hace cada orden de producción (OPL)**. Hacerlo a mano es lento y propenso a desequilibrios. OPLscheduler lo automatiza considerando simultáneamente:

- ✅ **Cualificación** — un operario solo puede coger artículos que sabe hacer (y con qué nivel de experiencia).
- ⏱️ **Capacidad** — cada operario tiene minutos disponibles por semana; no se puede sobrecargar.
- ⚖️ **Equidad** — repartir kilos y variedad de artículos de forma justa entre el equipo.
- 🔁 **Arrastre** — el trabajo que no cabe esta semana se traslada (parcialmente) a la siguiente.
- 📌 **Asignaciones fijas y obligatorias** — el planificador puede forzar o bloquear decisiones manualmente.

El resultado es un reparto **óptimo y explicable**, revisable y ajustable desde una interfaz web antes de aprobarlo.

---

## 🚀 Arranque rápido

> **Requisito único:** [Docker](https://www.docker.com/products/docker-desktop/) (incluye Docker Compose).

```bash
git clone https://github.com/marcessi/opl-scheduler.git
cd opl-scheduler
docker compose up --build
```

Esto levanta **toda la aplicación** (base de datos + backend + frontend ya compilado) en un solo comando.

| Recurso | URL |
|---------|-----|
| 🖥️ **Aplicación web** | http://localhost:8000 |
| 📖 **Documentación API (Swagger)** | http://localhost:8000/docs |
| ❤️ **Health check** | http://localhost:8000/health |

**Credenciales iniciales:** usuario `admin` · contraseña `admin`

> El primer `--build` tarda unos minutos (compila el frontend de React e instala las dependencias de Python). Las siguientes veces arranca al instante:
> ```bash
> docker compose up
> ```
>
> Para parar y borrar todo (incluida la base de datos):
> ```bash
> docker compose down -v
> ```

---

## 🧠 Cómo funciona el optimizador

El núcleo del proyecto es un modelo de **programación con restricciones (CP-SAT)** resuelto en **4 fases lexicográficas**: cada fase optimiza un objetivo, y las siguientes lo respetan dentro de una tolerancia (`delta`) configurable.

```mermaid
graph LR
    A["📦 Fase 1 · BASE<br/>Maximizar minutos<br/>totales asignados"] --> B["⭐ Fase 2 · EFICIENCIA<br/>Maximizar calidad<br/>de la asignación"]
    B --> C["⚖️ Fase 3 · EQUIDAD PESO<br/>Minimizar rango de<br/>kg por operario"]
    C --> D["🎲 Fase 4 · EQUIDAD ARTÍCULOS<br/>Minimizar rango de<br/>artículos por operario"]
```

1. **BASE** — asigna el mayor volumen de trabajo posible (máximos minutos).
2. **EFICIENCIA** — entre soluciones igual de productivas, prefiere asignar cada OPL al operario más cualificado.
3. **EQUIDAD DE PESO** — reparte los kilos de forma pareja, sin que nadie cargue mucho más que el resto.
4. **EQUIDAD DE ARTÍCULOS** — equilibra la variedad de artículos por persona.

El optimizador corre en un **subproceso aislado** (`multiprocessing` con contexto `spawn`) para no bloquear el servidor web, y se controla con dos parámetros sencillos desde la interfaz:

| Parámetro | Valores | Significado |
|-----------|---------|-------------|
| `tiempo_maximo_min` | `1`–`15` min | Presupuesto de cómputo del solver |
| `perfil` | `produccion` · `balanceado` · `personas` | Define cuánta calidad se sacrifica a favor de la equidad |

---

## 🔄 Flujo de uso

```mermaid
graph TD
    A["📥 1. Importar datos maestros<br/>(Excel: operarios, artículos, OPLs)"] --> B["⚙️ 2. Optimizar semana<br/>(solver CP-SAT en background)"]
    B --> C["👀 3. Revisar y ajustar<br/>(fijar / mover asignaciones a mano)"]
    C --> D["✅ 4. Aprobar reparto<br/>(genera arrastre a la semana siguiente)"]
    D --> E["📤 5. Exportar a Excel"]
```

1. **Importar datos maestros** — `POST /carga` con un Excel de operarios, artículos, cualificaciones y OPLs.
2. **Optimizar semana** — `POST /repartos/{semana}/optimizar` (responde `202`; el solver trabaja en segundo plano y el progreso es consultable).
3. **Revisar y ajustar** — la SPA permite fijar, mover o forzar asignaciones manualmente.
4. **Aprobar** — `POST /repartos/{semana}/aprobar` consolida el reparto y genera el **arrastre** del trabajo pendiente.
5. **Exportar** — `GET /repartos/{semana}/excel` descarga el resultado.

> La `semana` se identifica siempre por el **lunes** en formato ISO `YYYY-MM-DD`.

---

## 🏗️ Arquitectura

Una única imagen Docker sirve el backend y el frontend ya compilado; PostgreSQL corre como servicio aparte.

```mermaid
graph TB
    subgraph Browser["🌐 Navegador"]
        SPA["React 19 SPA<br/>(servida por FastAPI)"]
    end
    subgraph Container["🐳 Contenedor backend"]
        API["FastAPI<br/>routers · schemas"]
        SVC["Services<br/>(lógica de negocio)"]
        CRUD["CRUD<br/>(acceso a BD)"]
        SOLVER["Solver CP-SAT<br/>(subproceso aislado)"]
        API --> SVC --> CRUD
        SVC --> SOLVER
    end
    DB[("🐘 PostgreSQL 16")]
    SPA -->|REST + JWT| API
    CRUD --> DB
```

El backend está organizado por capas con responsabilidades claras:

- **`api/`** — FastAPI: routers por dominio, schemas Pydantic, manejo de excepciones.
- **`services/`** — orquesta las reglas de negocio.
- **`crud/`** — aísla todo el acceso a la base de datos (lecturas y mutaciones puras).
- **`optimization/`** — carga del problema, validación de factibilidad y solver CP-SAT.
- **`io/`** — importación y exportación de Excel.

---

## 🗂️ Modelo de dominio

| Entidad | Descripción |
|---------|-------------|
| **Familia** | Agrupación de artículos. |
| **Artículo** | Producto con un tiempo estándar de fabricación. |
| **Operario** | Trabajador con capacidad semanal (minutos). |
| **Operario_Familia / Operario_Articulo** | Cualificaciones y experiencia; pueden sobreescribir el tiempo estándar. |
| **OPL** | Orden de producción a asignar. |
| **Reparto** | Plan semanal de asignaciones. |
| **AsignacionOPL** | Asignación de una OPL a un operario en una semana. |

Cada asignación tiene un **tipo**:

- 🔵 `NORMAL` — el solver decide libremente.
- 🔴 `OBLIGATORIA` — debe asignarse sí o sí (si no es posible, el problema es infactible).
- 🟣 `ARRASTRE` — trabajo trasladado de una semana previa; siempre fijo e inmutable.

---

## 🔌 API

Documentación interactiva completa en **http://localhost:8000/docs**. Endpoints principales:

| Método | Ruta | Descripción |
|--------|------|-------------|
| `POST` | `/auth/login` | Autenticación → devuelve JWT (válido 8 h) |
| `POST` | `/carga` | Importación masiva de datos maestros (Excel) |
| `GET` | `/operarios` · `/articulos` · `/familias` · `/opls` | Consulta de datos maestros (solo lectura) |
| `GET` | `/repartos` | Listado de repartos |
| `POST` | `/repartos/{semana}/optimizar` | Lanza la optimización (asíncrona, `202`) |
| `GET` | `/repartos/{semana}/progreso` | Progreso del solver en curso |
| `POST` | `/repartos/{semana}/asignaciones` | Ajustes manuales de asignaciones |
| `PATCH` | `/repartos/{semana}/asignaciones/{id_opl}` | Editar una asignación |
| `POST` | `/repartos/{semana}/aprobar` | Aprobar reparto y generar arrastre |
| `GET` | `/repartos/{semana}/excel` | Exportar el **reparto** de una semana a Excel |
| `GET` | `/exportar/excel` | Exportar **datos maestros** a Excel |

> Los datos maestros son **solo lectura** vía API: todas las altas y modificaciones se hacen exclusivamente mediante `POST /carga` (Excel).

---

## 🧪 Tests

Con el stack levantado (`docker compose up`), en otra terminal:

```bash
docker compose exec backend python -m pytest -q
```

La base de datos de tests (`opl_scheduler_test`) se crea automáticamente en el primer arranque de PostgreSQL.

```bash
# Un fichero concreto
docker compose exec backend python -m pytest tests/optimization/test_solver.py -q

# Un test por nombre
docker compose exec backend python -m pytest -k "nombre_del_test" -q
```

---

## 📚 Documentación del código

El backend está documentado con **docstrings estilo Google** en todas las funciones y clases públicas. A partir de ellos se genera un **sitio HTML navegable** con [Sphinx](https://www.sphinx-doc.org/) (extensiones `autodoc` + `napoleon`). La configuración vive en `backend/docs/`.

Con el [entorno del backend](#-desarrollo) activado (un venv con `requirements.txt` instalado, que aporta las dependencias que `autodoc` necesita importar):

```bash
cd backend
pip install -r docs/requirements-docs.txt                        # Sphinx + tema furo
python -m sphinx.ext.apidoc --force --separate -o docs/api src    # genera .rst por módulo
python -m sphinx -b html docs docs/_build/html                    # construye el sitio
```

El resultado queda en `backend/docs/_build/html/index.html`. No hace falta una base de datos: `conf.py` define variables de entorno de relleno para que los módulos se importen sin conectar.

> El sitio generado (`_build/`) y los `.rst` autogenerados (`api/`) están en `.gitignore`: son artefactos.
>
> El **frontend** está documentado con **JSDoc**, que da autocompletado e información en el editor; no genera un sitio aparte.

---

## 💻 Desarrollo

### Frontend con hot-reload

La imagen Docker sirve el frontend ya compilado. Para iterar sobre el frontend con recarga en caliente, levanta el servidor de Vite aparte (hace proxy automático al backend de `:8000`):

```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```

| Comando | Acción |
|---------|--------|
| `npm run dev` | Servidor de desarrollo con HMR |
| `npm run build` | Type-check + build de producción |
| `npm run lint` | ESLint |
| `npm run typecheck` | `tsc --noEmit` (modo strict) |
| `npm run gen:api` | Regenera los tipos TypeScript desde el OpenAPI (requiere el backend corriendo en `:8000`) |

### Backend sin Docker

Requiere Python 3.12+ y un PostgreSQL accesible.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

export DATABASE_URL=postgresql://opl_user:dev_password@localhost:5432/opl_scheduler
export JWT_SECRET_KEY=dev-secret

alembic upgrade head               # aplica migraciones
uvicorn src.api.app:app --reload   # http://127.0.0.1:8000
```

---

## 🚀 Despliegue en producción

Para **desarrollo local no necesitas configurar nada**: `docker compose up` ya trae credenciales de desarrollo. Esta sección solo aplica si despliegas la aplicación fuera de tu máquina (un servidor, Azure App Service, etc.).

Copia la plantilla [`.env.example`](.env.example) como `.env` y rellena los valores:

```bash
cp .env.example .env
```

| Variable | Para qué sirve |
|----------|----------------|
| `ENV=production` | Activa las **validaciones estrictas** (sin las de abajo, el arranque falla). |
| `DATABASE_URL` · `POSTGRES_PASSWORD` | Conexión y contraseña de PostgreSQL (no uses las de desarrollo). |
| `JWT_SECRET_KEY` | Clave de firma de los tokens. Genérala con `python -c "import secrets; print(secrets.token_hex(32))"`. |
| `CORS_ORIGINS` | Dominios permitidos, separados por coma. **No puede ser `*`** en producción. |
| `ADMIN_BOOTSTRAP_PASSWORD` | Contraseña inicial del usuario `admin`. Cámbiala tras el primer login. |

Con `ENV=production`, el backend confía en las cabeceras `X-Forwarded-*` (para funcionar tras un reverse proxy) y **rechaza arrancar** si `JWT_SECRET_KEY` falta o si `CORS_ORIGINS` es `*`, evitando configuraciones inseguras por descuido.

---

## 📁 Estructura del proyecto

```
opl-scheduler/
├── docker-compose.yml        # Levanta todo: BD + backend + frontend
├── backend/
│   ├── src/
│   │   ├── api/              # FastAPI: routers, schemas, excepciones
│   │   ├── services/         # Lógica de negocio
│   │   ├── crud/             # Acceso a base de datos
│   │   ├── database/         # Modelos SQLAlchemy + sesión
│   │   ├── optimization/     # Solver CP-SAT (4 fases lexicográficas)
│   │   ├── io/               # Importación/exportación Excel
│   │   └── config/           # Settings (DB, JWT, CORS)
│   ├── tests/                # Suite de pytest
│   ├── docs/                 # Documentación Sphinx (autodoc + napoleon)
│   ├── alembic/              # Migraciones de BD
│   └── requirements.txt
├── frontend/
│   └── src/                  # React 19 + TypeScript + Vite
│       ├── api/              # Cliente HTTP + tipos del OpenAPI
│       ├── pages/            # Vistas (Dashboard, Repartos, ...)
│       ├── components/       # Componentes reutilizables
│       ├── context/          # Estado global (auth)
│       └── utils/            # Utilidades (cálculo de semanas, ...)
└── deploy/
    ├── Dockerfile            # Build multistage (frontend + backend)
    └── db-init/              # Script SQL inicial (crea la BD de tests)
```

---

## 🛠️ Stack tecnológico

| Capa | Tecnologías |
|------|-------------|
| **Backend** | Python 3.12 · FastAPI · SQLAlchemy 2 · Alembic · Pydantic 2 |
| **Optimización** | Google OR-Tools (CP-SAT) |
| **Base de datos** | PostgreSQL 16 |
| **Frontend** | React 19 · TypeScript 5 · Vite 8 · React Router 7 |
| **Autenticación** | JWT (python-jose) · bcrypt |
| **Infraestructura** | Docker · Docker Compose |
| **Testing** | pytest |
| **Documentación** | Sphinx (backend) · JSDoc (frontend) · OpenAPI/Swagger |

---

## 📄 Licencia

Distribuido bajo licencia **MIT** © 2026 Marc Escribano. Consulta el fichero [`LICENSE`](LICENSE).

Puedes usar, copiar y modificar el código libremente, siempre que **se mantenga el aviso de copyright y autoría**. El software se ofrece "tal cual", sin garantías.

---

<div align="center">
<sub>Trabajo de Fin de Grado · Marc Escribano</sub>
</div>
