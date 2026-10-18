# ADR-0026: Providers desacoplados para fuentes de costo

## Estado

Aceptada el 15 de agosto de 2026.

## Decisión

El calculador puro recibe valores normalizados. Un protocolo pequeño resuelve
costos de Supply y Community lo implementa con la última compra.

## Consecuencias

Una fuente futura, incluida una integración externa, podrá reemplazar el
provider sin modificar la aritmética ni los snapshots.
