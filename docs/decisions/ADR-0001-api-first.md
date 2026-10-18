# ADR-0001: API First

- Estado: aceptada
- Fecha de consolidación: 2026-07-28

## Contexto

RRII-Coach tendrá un backend independiente, un frontend web y futuras
integraciones. Las reglas no deben duplicarse entre consumidores.

## Decisión

FastAPI expondrá contratos HTTP documentados mediante OpenAPI. El backend será
la autoridad de reglas y validación. Los clientes generarán tipos y acceso HTTP
desde OpenAPI cuando sea viable.

## Consecuencias

- El frontend no contiene lógica de negocio.
- Los cambios incompatibles de contrato requieren gestión explícita.
- La API no implica microservicios ni exposición pública automática.
