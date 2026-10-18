# ADR-0016: PostgreSQL en pruebas de integración

- Estado: aceptada
- Fecha: 2026-07-28

## Contexto

SQLite difiere de PostgreSQL en UUID, JSONB, constraints y comportamiento de
migraciones. Sustituir la base oficial produciría pruebas engañosas.

## Decisión

Ejecutar integración y ciclos de Alembic contra PostgreSQL 17 real. Localmente
se usa un servicio Compose efímero y aislado; CI usa un service container con
credenciales exclusivas de prueba.

## Consecuencias

- Las pruebas unitarias rápidas no requieren base.
- Las pruebas marcadas `integration` nunca usan la base ni el volumen de
  desarrollo.
- CI verifica `upgrade`, `downgrade`, reaplicación y sincronía de metadata.
