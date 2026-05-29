-- Crea la BD de tests en el primer arranque de PostgreSQL.
-- Solo se ejecuta cuando pgdata está vacío (init de Docker Postgres).
-- Si la BD principal ya existe (volumen persistido), créala manualmente:
--   docker exec deploy-db-1 psql -U opl_user -d opl_scheduler \
--       -c "CREATE DATABASE opl_scheduler_test OWNER opl_user;"

CREATE DATABASE opl_scheduler_test OWNER opl_user;
