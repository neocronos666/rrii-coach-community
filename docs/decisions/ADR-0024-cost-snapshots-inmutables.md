# ADR-0024: Snapshots inmutables de costos

## Estado

Aceptada el 15 de agosto de 2026.

## Decisión

Cada cálculo se persiste con las líneas y valores económicos utilizados. Las
consultas históricas no vuelven a resolver fuentes y no existen endpoints de
edición o borrado.

## Consecuencias

Un cambio de precio no altera resultados anteriores. Una futura recalculación
creará otra identidad y permitirá comparar ambos snapshots.
