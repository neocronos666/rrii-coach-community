# ADR-0034: FIFO simulado para vista previa de recetas

## Estado

Aceptada el 28 de septiembre de 2026. El usuario confirmó simulación FIFO sólo
para la vista previa; no asignaciones persistentes al consumir.

## Decisión

Agregar una vista previa de lectura con estrategia FIFO explícita y última
compra como alternativa. Reutilizar resolución de recetas y aritmética técnica
y comercial. Registrar el vínculo de nuevas compras con su movimiento; conservar
sin costo trazable los ingresos históricos no vinculados y los ajustes positivos.

FIFO ordena por fecha efectiva, creación e identificador de movimiento. Las
salidas consumen capas y los déficits absorben entradas posteriores. La demanda
de todos los pasos comparte capas. No guardar las asignaciones simuladas ni
alterar cierres de Runs. Usar una transacción consistente y de sólo lectura.

## Consecuencias

Las simulaciones cambian ante movimientos retroactivos y no garantizan disponibilidad
futura. Una demanda puede quedar incompleta aunque exista cantidad física; no se
inventa su costo. Sólo se ofrece precio sugerido si el costo es completo,
monomoneda y tiene markup. El contrato detalla estimaciones explícitas por paso.

ADR-0022 sigue rigiendo los cálculos técnicos persistentes por última compra.
Esta ampliación se limita al [contrato de preview](../modules/pricing_preview_es.md),
sin recalcular snapshots ni introducir valuación contable.
