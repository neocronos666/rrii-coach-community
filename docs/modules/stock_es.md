# Stock mínimo de insumos

## Ledger

El stock actual se deriva de `SUM(supply_stock_movements.quantity)`. Las
entradas son positivas y las salidas negativas; no existe un saldo mutable en
`Supply`. Compras y ajustes usan `purchase`, `adjustment_in` y
`adjustment_out`; los consumos productivos generan movimientos `consumption`.

Una compra crea su ingreso de forma atómica. Los ajustes reciben dirección y
cantidad positiva; el servicio traduce la salida a signo negativo. Una salida
mayor al saldo disponible se rechaza con 409 y rollback completo.

## Concurrencia

Las escrituras bloquean la fila del insumo durante la transacción antes de
calcular una salida. Esto evita la carrera trivial entre dos ajustes sobre el
mismo insumo. Community sigue siendo monousuario; necesidades de mayor
concurrencia deberán reevaluarse con métricas y pruebas específicas.

## API

- `GET /api/v1/supplies/{id}/stock`
- `POST /api/v1/supplies/{id}/adjustments`
- `GET /api/v1/supplies/{id}/movements`

Las [reservas](supply_reservations_es.md) afectan disponibilidad y los
[consumos productivos](production_consumption_es.md) registran salidas físicas.
No hay inventario por ubicación ni métodos contables de valuación.
