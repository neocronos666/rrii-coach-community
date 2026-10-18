# Composición física

RunClose admite product_consumptions con variant_id, consumed y wasted.
Las cantidades corresponden a la unidad base de la variante. consumed es
positivo y wasted pertenece al intervalo [0, consumed]. Cada variante aparece
una sola vez por Run. El producto de salida no puede ser componente de sí mismo.

El cierre crea ProductionRunProductConsumption y una salida del ledger por
consumed. wasted clasifica parte de esa cantidad; no crea otro descuento.
La salida buena del Run ingresa al stock sólo si hay output_variant_id.
Los consumos, la producción, los consumos Supply y el resultado del Run se
confirman juntos. Una variante inexistente revierte la transacción completa.

GET /production-runs/{id}/product-consumptions devuelve los componentes reales.
Los reintentos idénticos del cierre devuelven el resultado existente. No hay
edición o eliminación de consumos confirmados. Un faltante de stock produce
insufficient_product_stock:<variant_id> y permite registrar el hecho físico.

Las variantes de entrada y salida se bloquean en orden UUID estable. Así dos
composiciones concurrentes no invierten el orden de bloqueos de componentes.
El origen de cada producto fabricado sigue conservado en su movimiento de
entrada. Este incremento no adjudica automáticamente consumos a lotes de entrada
ni implementa FIFO, trazabilidad serial o valorización de inventario.
