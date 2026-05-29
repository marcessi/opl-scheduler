# OPLscheduler

Planificador semanal de producción que asigna OPLs (Órdenes de Producción) a operarios mediante programación con restricciones (Google OR-Tools CP-SAT).

**Stack:** FastAPI · PostgreSQL 16 · React 19 · TypeScript · Docker

---

## Arranque rápido (Docker)

Requiere [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado.

```bash
git clone https://github.com/marcessi/opl-scheduler.git
cd opl-scheduler

# Levantar base de datos + backend (con hot-reload)
docker compose -f deploy/docker-compose.yml -f deploy/docker-compose.override.yml up
```

- API disponible en `http://localhost:8000`
- Documentación interactiva (Swagger): `http://localhost:8000/docs`
- Usuario por defecto: `admin` / `admin`

El frontend se sirve desde `http://localhost:8000` (incluido en el build de producción).

### Frontend en modo desarrollo

Para trabajar con hot-reload en el frontend:

```bash
cd frontend
npm install
npm run dev     # http://localhost:5173 (proxy a :8000)
```

---

## Estructura del proyecto

```
opl-scheduler/
├── backend/
│   ├── src/
│   │   ├── api/           # FastAPI: routers, schemas
│   │   ├── services/      # Lógica de negocio
│   │   ├── crud/          # Acceso a base de datos
│   │   ├── database/      # Modelos SQLAlchemy
│   │   ├── optimization/  # Solver CP-SAT (4 fases lexicográficas)
│   │   └── io/            # Importación/exportación Excel
│   ├── tests/
│   ├── alembic/           # Migraciones de BD
│   └── requirements.txt
├── frontend/
│   └── src/               # React 19 + TypeScript + Vite
└── deploy/
    ├── Dockerfile
    ├── docker-compose.yml
    └── docker-compose.override.yml  # Dev local (hot-reload, BD expuesta)
```

---

## Desarrollo sin Docker

### Backend

Requiere Python 3.12+ y PostgreSQL 16 accesible.

```bash
cd backend
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

export DATABASE_URL=postgresql://opl_user:dev_password@localhost:5432/opl_scheduler
export JWT_SECRET_KEY=dev-secret

alembic upgrade head
uvicorn src.api.app:app --host 127.0.0.1 --port 8000 --reload
```

### Tests

```bash
cd backend
# Requiere BD opl_scheduler_test (ver deploy/db-init/01-create-test-db.sql)
python -m pytest -q
```

---

## Flujo de uso

1. **Importar datos maestros** — `POST /carga` (Excel con operarios, artículos, OPLs)
2. **Optimizar semana** — `POST /repartos/{semana}/optimizar` (devuelve 202; solver en background)
3. **Revisar y ajustar** — el SPA permite fijar/mover asignaciones manualmente
4. **Aprobar** — `POST /repartos/{semana}/aprobar` (genera arrastre para la semana siguiente)
5. **Exportar** — `GET /repartos/{semana}/excel`

El solver ejecuta 4 fases CP-SAT lexicográficas: maximizar minutos asignados → calidad de asignación → equidad de carga (kg) → equidad de artículos.

---

## Tecnologías principales

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.12, FastAPI, SQLAlchemy, Alembic |
| Optimización | Google OR-Tools CP-SAT |
| Base de datos | PostgreSQL 16 |
| Frontend | React 19, TypeScript 5, Vite 8 |
| Contenedores | Docker, Docker Compose |
