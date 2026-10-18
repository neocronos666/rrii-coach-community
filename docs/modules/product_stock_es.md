# Stock físico de productos

Extensión 10B.5: los Runs experimentales no ingresan producto al cerrar. Su
promoción explícita genera un movimiento test_print con test_print_id único,
sólo después de completar la receta entera. Los Runs comerciales conservan el
comportamiento descrito aquí. Ver [test print](test_prints_es.md).

El stock de cada ProductVariant se calcula sumando ProductStockMovement.
No existe una columna mutable de saldo. Un único almacén es implícito.

- POST /product-variants/{id}/stock-movements registra compras y ajustes.
  La cantidad de entrada es positiva; adjustment_out genera una salida.
  request_id permite repetir una petición sin duplicar el movimiento.
- GET sobre la misma ruta lista movimientos con paginación.
- GET /product-variants/{id}/stock devuelve cantidad física y advertencia
  cuando el saldo es negativo. Un ajuste puede registrar faltantes reales.

Los movimientos son inmutables mediante API. Las correcciones se registran
con nuevos ajustes, incluso en variantes inactivas, para conservar el historial.

Cerrar un Run con output_variant_id y unidades buenas genera una entrada
atómica dentro de la misma transacción que resultados y consumos. Los fallos
no ingresan al stock. Doce unidades buenas para un objetivo de diez generan
una entrada de doce. Asignar a un pedido y entregar son operaciones diferentes,
se describen en [asignación y entrega](product_allocations_es.md); completar
una Task no representa entrega comercial.

La referencia al Run permite recorrer Task y Order o ProjectComponent/Project.
Los excedentes conservan ese origen. No se serializan unidades ni se crea una
entidad de lote adicional. Los pasos sin salida inventariable no crean stock.

La migración 0016 incorpora las salidas buenas de Runs cerrados que ya tengan
una variante de salida. No inventa producción para tareas históricas legacy.
El downgrade rechaza eliminar un ledger que contenga movimientos.
