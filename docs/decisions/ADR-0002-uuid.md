# ADR-0002: UUID para entidades persistentes

- Estado: aceptada
- Fecha de consolidación: 2026-07-28

## Contexto

El sistema debe soportar instalaciones locales, sincronización futura,
integraciones e identificación estable de archivos y entidades.

## Decisión

Las entidades persistentes utilizarán UUID, salvo una excepción posterior
justificada mediante ADR. La versión concreta y su generación se elegirán al
diseñar la persistencia.

## Consecuencias

- No se depende de secuencias globales para identidad pública.
- Los UUID no sustituyen claves naturales ni restricciones de unicidad.
- La representación HTTP y PostgreSQL deberá ser consistente.
