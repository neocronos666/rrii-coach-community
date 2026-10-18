# Consumo real y desperdicio

Desde 10B.5 los Runs experimentales reutilizan estos consumos de insumos, sin
modificar reservas de tareas comerciales. Los componentes producidos dentro de
la prueba registran internal_source_step_id y no descuentan stock comercial;
los externos sí lo descuentan. Ver [test print](test_prints_es.md).

El cierre del Run acepta supply_consumptions: un resumen por insumo, en su unidad
base, con consumed > 0 y 0 <= wasted <= consumed. El cierre, los consumos, los
movimientos y la actualización de reservas se confirman en una sola transacción.

consumed=100 y wasted=15 producen exactamente una salida de 100. No se genera
una segunda salida por desperdicio. Un fallo puede conservar unidades buenas y
consumos reales. La ausencia de stock se informa en warnings y permite continuar.

La reserva pendiente disminuye por consumed; finalizar la Task libera el resto.
Cada movimiento de consumo referencia el registro que identifica Run e insumo.
Repetir el mismo cierre no genera movimientos adicionales; un resultado diferente
para un Run cerrado genera conflicto. No hay edición ni borrado de consumos.

GET /production-runs/{id}/supply-consumptions permite consultar los registros.
El ledger existente de Supply sigue siendo la única fuente de stock físico.
Los consumos se registran explícitamente; no se infieren mediciones físicas.
