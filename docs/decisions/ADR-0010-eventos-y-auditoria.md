# ADR-0010: Trazabilidad mediante registros de dominio

- Estado: alcance revisado el 2026-10-17.
- Fecha original: 2026-07-28.

## Decisión

La historia implementada reside en snapshots de costos y presupuestos,
revisiones de Assets y Quick Quotes, intentos de producción y movimientos de
inventario. Los servicios preservan estos registros dentro de sus transacciones.

No existe una infraestructura general de eventos persistidos, auditoría por
usuario ni publicación distribuida. No se presenta como implementada.

## Consecuencias

Los timestamps y snapshots describen hechos del dominio; no identifican a un
operador autenticado. La actividad reciente del dashboard no equivale a un
registro general de auditoría. No se agrega infraestructura durante esta revisión.
