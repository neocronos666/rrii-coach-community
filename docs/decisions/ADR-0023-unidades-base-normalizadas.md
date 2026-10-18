# ADR-0023: Unidades base normalizadas

## Estado

Aceptada el 15 de agosto de 2026.

## Decisión

Cada insumo posee una unidad base y todos sus movimientos se almacenan en ella.
Un servicio pequeño convierte solo factores deterministas dentro de masa,
volumen y longitud. La unidad queda inmutable tras el primer movimiento.

## Consecuencias

El saldo tiene una interpretación única. No se convierten dimensiones
incompatibles ni se infiere densidad. Las cantidades usan `Decimal` y
`NUMERIC(18,6)`.
