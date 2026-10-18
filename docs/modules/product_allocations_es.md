# Asignación y entrega

ProductStockAllocation asigna una cantidad de ProductVariant a exactamente un
Order o ProjectComponent. No cambia el ledger físico. Mantiene cantidad inicial,
cantidad pendiente, unidad base y petición original para reintentos seguros.

POST /product-allocations recibe request_id, variant_id, quantity y el destino.
Devuelve allocation y stock: physical_quantity, allocated_quantity,
available_quantity y shortage_warning. Se permiten faltantes con advertencia.
GET /product-allocations lista con filtros de destino y paginación.
GET /product-allocations/{id} devuelve una asignación.

POST /product-allocations/{id}/deliver recibe request_id y quantity. Descuenta
la cantidad pendiente y crea un movimiento negativo delivery en una transacción.
Se permite entrega parcial, hasta la cantidad pendiente. La entrega se registra
al momento actual y no cierra comercialmente el Order/Project.
POST /product-allocations/{id}/release libera todo lo pendiente sin salida física.

Ejemplo: físico 12, asignado 10, disponible 2. Entregar 4 deja físico 8,
asignado 6, disponible 2. Liberar el resto deja físico 8 y disponible 8.
Cancelar Order/Project libera cantidades pendientes sin borrar entregas reales.
Los reintentos de crear, entregar o liberar no reponen cantidades liberadas.

Las asignaciones se hacen por variante, sin elegir lotes ni introducir FIFO.
Cada ingreso fabricado conserva su Run/Task/origen, incluso los excedentes.
El enlace detallado entre una entrega comercial y sus lotes fuente queda fuera
del MVP; no se pierde el historial productivo de entradas.
