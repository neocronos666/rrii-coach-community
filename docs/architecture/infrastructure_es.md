# Infraestructura de desarrollo

## Objetivo

RRII-Coach Community se prueba localmente con Docker Engine y Docker Compose.
El entorno humano no requiere una VM ni un servidor remoto; sus comandos y
puertos se describen en la [guía local](../development/human_test_environment_es.md).
El resto de este documento describe el Compose de desarrollo.

## Servicios

```text
Navegador
├── frontend (Nuxt, localhost:3000)
└── backend (FastAPI, localhost:8000)
        └── db (PostgreSQL, solo red interna)
```

- `db`: PostgreSQL 17 con volumen `postgres_data`.
- `backend`: Python 3.13.14, FastAPI y volumen `assets_data`.
- `frontend`: Node.js 24 LTS y Nuxt 4 en modo de desarrollo SPA.

PostgreSQL no publica un puerto al host. Backend y frontend se publican
únicamente en `127.0.0.1` por defecto.

## Versiones verificadas

Resoluciones comprobadas el 28 de julio de 2026:

- Python 3.13.14 y uv 0.11.29.
- FastAPI 0.139.2, SQLAlchemy 2.0.51, Alembic 1.18.5 y Pydantic 2.13.4.
- PostgreSQL 17.10 mediante la imagen `postgres:17-bookworm`.
- Node.js 24.18.0 LTS y pnpm 11.17.0.
- Nuxt 4.5.1, Vue 3.5.40 y Nuxt UI 4.10.0.
- TypeScript 5.9.3, Vitest 4.1.10 y Playwright 1.62.0.

Los manifests expresan rangos compatibles; `uv.lock` y `pnpm-lock.yaml`
registran las resoluciones exactas.

## Persistencia

Los volúmenes administrados por Compose son:

- `postgres_data`: base PostgreSQL.
- `assets_data`: archivos privados de Community en `/data/assets`.
- `backend_venv`: entorno Python de desarrollo.
- `frontend_node_modules`: dependencias Node de desarrollo.
- `frontend_nuxt` y `frontend_output`: artefactos generados por Nuxt sin
  modificar permisos del código montado.

`make down` y `make clean` conservan los volúmenes. `make destroy` pide una
confirmación textual antes de eliminarlos.

## Salud y dependencias

PostgreSQL utiliza `pg_isready`. `/health` comprueba únicamente que el proceso
FastAPI responde. `/ready` realiza una consulta liviana a PostgreSQL y compara
la revisión registrada en `alembic_version` con el head de Alembic. El
healthcheck del contenedor backend usa readiness, por lo que el frontend espera
una base accesible y con el esquema actualizado.

Las migraciones no se ejecutan automáticamente. `make migrate` aplica
explícitamente `alembic upgrade head`; iniciar workers nunca modifica el
esquema de forma implícita.

## Red y seguridad

Los servicios comparten una red bridge interna del proyecto. Este despliegue es
exclusivamente de desarrollo:

- no contiene TLS;
- no incluye autenticación;
- no expone PostgreSQL;
- no requiere Redis, Celery, workers ni Nginx;
- la contraseña de `.env.example` debe reemplazarse en `.env`.

La exposición remota y las reglas de firewall quedan fuera del entorno local.
