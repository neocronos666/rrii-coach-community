# Módulo de pedidos

## Finalidad

`Order` representa una ejecución operativa simple derivada de un presupuesto
aprobado con exactamente un `QuoteItem`. No reemplaza ni modifica al `Quote`.

La creación es exclusivamente mediante `POST /api/v1/quotes/{quote_id}/convert`;
no existe POST directo de pedidos. La conversión copia título, descripción,
cantidad, moneda, costos técnicos del item y precios sugerido/final globales
del presupuesto. Estos importes son snapshots y no se recalculan.

## Estado y código

Todo pedido nace `pending` y puede pasar una sola vez a `cancelled`. Cancelarlo
no altera el presupuesto, stock ni producción. El código visible usa
`O-AAAA-NNNNNN` y una secuencia PostgreSQL que no se reinicia por año.

## API

- `GET /api/v1/orders`, con filtro opcional `status`.
- `GET /api/v1/orders/{order_id}`.
- `POST /api/v1/orders/{order_id}/cancel`.

No existen PATCH, DELETE ni creación directa.
