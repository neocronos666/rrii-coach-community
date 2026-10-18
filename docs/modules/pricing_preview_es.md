# Vista previa de costos y precio por receta

`POST /api/v1/pricing-preview` devuelve una simulación sin persistir cálculos,
presupuestos, reservas ni consumos. La transacción PostgreSQL utiliza
`REPEATABLE READ` y `READ ONLY`. No asigna lotes a los consumos reales.

## Entrada y cantidades

- `recipe_id`, `variant_id`, `target_quantity`, `selections`: mismos conceptos y
  resolución compartida que producción y test print; admite receta base o legacy.
- `strategy`: `fifo` por defecto o `last_purchase` explícito. Nunca cambia de
  estrategia silenciosamente por falta de fuentes.
- `step_estimates`: mapa por clave de paso activo. Sus tiempos e importes son
  **totales para la demanda solicitada**, no unitarios ni por lote. Admite
  `machine_id` junto con `machine_duration_minutes`, `energy_kwh`, `labor`
  (`labor_type`, `duration_minutes`) y `extras` (`description`, `amount`, `currency`).
- `markup_percentage`: opcional; si se omite usa la configuración de instalación.
  Cero explícito prevalece sobre el default.

Los insumos se obtienen exclusivamente de la receta resuelta y sus lotes
planificados. Un insumo usado en varios pasos comparte el mismo conjunto de
capas durante toda la petición, siguiendo el orden topológico del plan. No se
multiplica nuevamente la cantidad seleccionada ni el rendimiento del lote.

Un paso no informado, salvo `wait`, agrega una línea incompleta de estimación.
Para operaciones o servicios, `{}` declara explícitamente que no se agregan
costos de tiempo ni extras. Para impresión se exige máquina activa, tecnología
compatible y duración. Service y wait no admiten máquina. Las tarifas de mano
de obra, energía y depreciación se resuelven con el motor técnico existente;
las fuentes faltantes permanecen incompletas. Los campos libres `parameters`
no se interpretan como tiempos ni costos.

## Reconstrucción FIFO

Se recorren todos los movimientos registrados del insumo, igual que el saldo
vigente del ledger, ordenados ascendentemente por `occurred_at`, `created_at` e
`id`. No es una consulta histórica a una fecha de corte. Los movimientos
retroactivos pueden cambiar una simulación posterior.

Cada entrada crea una capa. Cada salida retira primero la capa más antigua.
Una salida que excede las capas deja deuda de cantidad: las entradas posteriores
cubren primero esa deuda. Las reservas no se descuentan como salidas físicas.
Luego se simula la demanda de la receta sobre las capas restantes.

Desde la migración 0035, las compras nuevas enlazan el movimiento con
`purchase_id` en la misma transacción. El vínculo es único y tiene FK; el
servicio fija insumo y cantidad normalizada coincidentes. Sólo ese origen
verificable aporta `total_cost / quantity` y moneda a FIFO. Un vínculo incoherente
no aporta un costo conocido.

Las compras anteriores sin vínculo y ajustes positivos conservan cantidad con
costo desconocido. No se asocian compras por fechas o importes parecidos. Una
porción sin stock tampoco tiene costo. No se usa última compra como fallback.
La migración no rellena vínculos históricos; su downgrade rechaza perder
vínculos existentes.

`last_purchase` conserva la estimación por última compra, aunque no quede stock.
La vista previa advierte si la demanda agregada supera la existencia física.
No sustituye la estrategia del endpoint histórico de CostCalculation.

## Salida y precio sugerido

La respuesta incluye `planned_steps`, `omitted_step_keys` y `lines` con paso,
cantidad, unidad, costo unitario, subtotal, moneda, fuente y referencias a
compra/movimiento cuando existen. Las porciones desconocidas tienen importes
nulos y `complete=false`; sus cantidades siguen visibles.

`totals_by_currency` suma sólo importes conocidos, redondeados con las reglas
del motor técnico. No representa costo total si `complete=false`. Monedas
múltiples se conservan separadas y activan `multi_currency`.

Un componente interno ya se costea en sus pasos proveedores y no se suma otra
vez. Los componentes externos no tienen fuente de costo en este incremento:
producen una línea incompleta con su unidad real, aunque haya stock comercial.

Sólo un resultado completo, con exactamente una moneda y markup definido,
produce `suggested_price` y `suggested_currency`. Se aplica el calculador de
markup de Community, sin autoredondeo comercial, impuestos ni ajustes implícitos.
No es un Quote formal ni una valuación contable de inventario.

## Límites

No hay asignaciones FIFO persistentes, conversión de monedas,
reconciliación de historia ni costeo recursivo de componentes externos.
Quick Quote guarda evaluaciones en 10B.7; el puente al Quote formal corresponde
a 10B.8.

## Reutilización desde Quick Quote

10B.7 comparte `evaluate_in_snapshot`, que devuelve resultado y contexto efectivo
sin escribir ni confirmar transacciones. [Quick Quote](quick_quotes_es.md) guarda
ese resultado bajo su propia transacción. La ruta de pricing preview conserva
READ ONLY, su respuesta y su ausencia de efectos persistentes.
