# ADR-0028: separar costo técnico de presupuesto

## Estado

Aceptada.

## Decisión

`Quote` consume `CostCalculation` existente sin recalcularlo ni modificarlo.
Esto evita mezclar fuentes técnicas con reglas comerciales y prepara ambos
módulos para evolucionar de forma independiente.
