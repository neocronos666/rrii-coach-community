# ADR-0027: Precisión y redondeo de costos

## Estado

Aceptada el 15 de agosto de 2026.

## Decisión

La aritmética usa `Decimal`. Se conserva precisión durante el cálculo y al
crear el snapshot se aplica `ROUND_HALF_UP`: ocho decimales para costo unitario
y cuatro para subtotal. Los totales suman subtotales ya persistibles.

## Consecuencias

Costos pequeños por gramo o milímetro no se truncan prematuramente. La UI futura
decidirá la presentación por moneda sin alterar el valor histórico.
