# ADR-0008: Producto, asset, variante y revisión

- Estado: aceptada
- Fecha: 2026-07-28

## Contexto

Un archivo puede venderse, reutilizarse y evolucionar técnicamente. Variante,
color, compatibilidad y versión expresan dimensiones diferentes.

## Decisión

`Product` y `Asset` permanecerán separados aunque se relacionen. Familia,
compatibilidad, variante, color, revisión y archivo serán conceptos explícitos.
La biblioteca mostrará la revisión activa más reciente y conservará las
anteriores.

## Consecuencias

- El nombre del archivo no es fuente única de verdad.
- Los pedidos antiguos podrán referenciar la revisión usada.
- La cardinalidad exacta de revisiones activas queda por definir.
