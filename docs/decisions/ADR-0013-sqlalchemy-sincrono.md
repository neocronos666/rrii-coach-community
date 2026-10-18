# ADR-0013: SQLAlchemy síncrono

- Estado: aceptada
- Fecha: 2026-07-28

## Contexto

Community todavía no tiene una carga que justifique dos modelos de ejecución.
Mantener soporte síncrono y asíncrono aumentaría la complejidad transaccional y
de pruebas.

## Decisión

Usar SQLAlchemy 2.x síncrono con `Session`, `sessionmaker` y psycopg 3.
FastAPI puede ejecutar la dependencia síncrona sin introducir `AsyncSession`.

## Consecuencias

- Existe un único motor y una única fábrica de sesiones.
- No se agregan `asyncpg`, `AsyncSession` ni soporte doble.
- Una migración asíncrona futura requerirá métricas y un ADR nuevo.
