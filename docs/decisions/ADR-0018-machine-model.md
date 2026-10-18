# ADR-0018: Modelo inicial de máquina genérica

- Estado: aceptada
- Fecha: 2026-08-14

## Contexto

RRII-Coach debe representar tecnologías maker diferentes y permitir ampliar
los tipos sin acoplar PostgreSQL a una enumeración difícil de evolucionar.

## Decisión

Crear `Machine` como entidad genérica. Guardar `machine_type` en `VARCHAR` y
validarlo mediante enum Python y contratos Pydantic. Usar inicialmente un bool
`active` y no implementar borrado ni una máquina de estados.

## Consecuencias

- FDM, SLA, CNC, láser y otros equipos comparten el modelo.
- Agregar un tipo no exige alterar un enum PostgreSQL.
- Sensores, ubicaciones y métricas futuras permanecerán desacoplados.
