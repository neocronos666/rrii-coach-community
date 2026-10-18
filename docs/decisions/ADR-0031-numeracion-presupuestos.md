# ADR-0031: numeración de presupuestos

## Estado

Aceptada.

## Decisión

Una secuencia PostgreSQL global genera la parte numérica de códigos
`Q-AAAA-NNNNNN`. No se usa conteo de filas ni se reinicia el contador por año.
