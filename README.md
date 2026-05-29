# OPLscheduler

Planificador semanal de producción que asigna OPLs (Órdenes de Producción) a operarios mediante programación con restricciones (Google OR-Tools CP-SAT).

**Stack:** FastAPI · PostgreSQL 16 · React 19 · TypeScript · Docker

---

## Ejecutar

Requiere [Docker](https://www.docker.com/products/docker-desktop/) instalado.

```bash
git clone https://github.com/marcessi/opl-scheduler.git
cd opl-scheduler
docker compose up --build
```

- Aplicación: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`
- Login: `admin` / `admin`

El primer `--build` tarda unos minutos (compila frontend + instala dependencias Python). Las siguientes ejecuciones usan la imagen cacheada:

```bash
docker compose up
```

## Tests

Con el stack levantado:

```bash
docker compose exec backend python -m pytest -q
```

## Frontend en desarrollo

Para trabajar con hot-reload en el frontend (proxy automático a :8000):

```bash
cd frontend
npm install
npm run dev     # http://localhost:5173
```

---

## Estructura

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
│   └── alembic/           # Migraciones de BD
├── frontend/
│   └── src/               # React 19 + TypeScript + Vite
└── deploy/
    ├── Dockerfile
    └── db-init/
```

---

## Flujo de uso

1. **Importar datos maestros** — `POST /carga` (Excel con operarios, artículos, OPLs)
2. **Optimizar semana** — `POST /repartos/{semana}/optimizar` (solver en background, devuelve 202)
3. **Revisar y ajustar** — SPA permite fijar/mover asignaciones manualmente
4. **Aprobar** — `POST /repartos/{semana}/aprobar` (genera arrastre para la semana siguiente)
5. **Exportar** — `GET /repartos/{semana}/excel`

---

## Tecnologías

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3.12, FastAPI, SQLAlchemy, Alembic |
| Optimización | Google OR-Tools CP-SAT |
| Base de datos | PostgreSQL 16 |
| Frontend | React 19, TypeScript 5, Vite 8 |
| Contenedores | Docker, Docker Compose |
