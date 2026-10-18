# ADR-0015: Servicios como frontera transaccional

- Estado: aceptada
- Fecha: 2026-07-28

## Contexto

Los commits ocultos en repositorios o dependencias HTTP dificultan componer
operaciones y manejar errores de manera consistente.

## Decisión

Los servicios controlan `commit` y `rollback`. Los repositorios reciben una
sesión y pueden usar `flush`, pero no confirman. La dependencia FastAPI entrega
y cierra la sesión sin commit automático.

## Consecuencias

- La sesión funciona inicialmente como unidad de trabajo.
- No se crea un `UnitOfWork` ni un `GenericRepository`.
- Los errores transaccionales se traducen a excepciones técnicas sin exponer
  credenciales.
