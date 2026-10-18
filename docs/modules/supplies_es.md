# Módulo de insumos

## Alcance

`Supply` representa un recurso físico comprable, almacenable o consumible sin
suponer que sea filamento ni fijar un uso comercial exclusivo. Puede ser
material, componente, consumible, embalaje, repuesto, mercadería u otro.

Conserva UUID, nombre, SKU opcional y único, categoría, marca opcional, unidad
base, descripción, estado activo, notas y timestamps UTC. No posee una columna
de stock. Un insumo con historia se desactiva y no se borra mediante la API.

## Unidades y presentaciones

Las unidades iniciales son `unit`, `g`, `kg`, `ml`, `l`, `mm`, `cm`, `m`, `m2`
y `m3`. El stock siempre se normaliza a la unidad base. Solo se convierten
dimensiones compatibles: kg/g, l/ml y m/cm/mm. No se infiere densidad ni se
convierten masa, volumen y unidades entre sí.

`SupplyPresentation` describe una forma de compra, por ejemplo un rollo de 1 kg
o una bolsa de 100 unidades. Su cantidad y unidad se convierten a la unidad base
al registrar una compra. Una presentación puede conservar un precio orientativo,
pero las compras son la fuente histórica del costo.

La unidad base puede corregirse mientras no existan movimientos. Luego queda
bloqueada para evitar reinterpretar el ledger histórico.

## Compras y costo estimado

`SupplyPurchase` conserva cantidad total normalizada, presentación opcional,
costo total, moneda, fecha y notas. No modela proveedor, factura ni pago. Cada
compra crea en la misma transacción un movimiento positivo de stock.

El costo estimado para cotización es el costo total dividido por la cantidad
base de la última compra según `purchased_at`. Conserva su moneda y no realiza
conversión. Sin compras el endpoint responde 404; no inventa costo cero.

El motor de costos accede a este valor mediante un provider y congela compra,
moneda y costo unitario en cada línea. Calcular una cantidad no crea movimientos
ni modifica la existencia.

## API

- `GET/POST /api/v1/supplies`
- `GET/PATCH /api/v1/supplies/{id}`
- `GET/POST /api/v1/supplies/{id}/presentations`
- `GET/POST /api/v1/supplies/{id}/purchases`
- `GET /api/v1/supplies/{id}/estimated-cost`

No existe DELETE. La [interfaz de inventario](inventory_ui_es.md) permite
administrar insumos, presentaciones, compras y ajustes.
