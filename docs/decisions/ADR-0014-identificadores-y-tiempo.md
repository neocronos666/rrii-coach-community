# ADR-0014: UUIDv4 y timestamps UTC

- Estado: aceptada
- Fecha: 2026-07-28
- Complementa: ADR-0002

## Contexto

ADR-0002 definió UUID sin fijar versión ni generación. También se necesitan
marcas temporales portables para trazabilidad futura.

## Decisión

Generar UUIDv4 en la aplicación con la biblioteca estándar y almacenarlos en el
tipo UUID nativo de PostgreSQL. Almacenar `created_at` y `updated_at` como
`TIMESTAMP WITH TIME ZONE`, con valores iniciales asignados por PostgreSQL y
actualización ORM explícita para `updated_at`.

## Consecuencias

- No se adopta UUIDv7 sin una necesidad demostrada.
- Los valores temporales tienen semántica UTC y son timezone-aware.
- Estos campos se incorporan mediante mixins pequeños, no mediante una base
  con responsabilidades acumuladas.
