# ADR-0021: Stock derivado de movimientos

## Estado

Aceptada el 15 de agosto de 2026.

## Decisión

La existencia es la suma de un ledger de movimientos con signo. `Supply` no
guarda un saldo editable. Compras y ajustes se confirman en servicios; los
repositorios no controlan transacciones.

## Consecuencias

Se conserva historia auditable y se evita desincronizar saldo y movimientos.
Las salidas bloquean el insumo y no pueden producir stock negativo. Una futura
materialización por rendimiento deberá seguir siendo derivada.
