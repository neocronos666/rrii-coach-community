# Arquitectura de RRII-Coach Community

## Flujo y responsabilidades

```text
Navegador
    │
Nuxt 4 / Vue 3 (SPA)
    │ HTTP / OpenAPI
FastAPI
    ├── módulos de dominio y servicios transaccionales
    ├── repositorios SQLAlchemy 2.x → PostgreSQL
    └── almacenamiento local de archivos
```

La API conserva la autoridad sobre reglas, costos, stock y transiciones.
El frontend presenta datos, valida entradas y coordina interacción; no reproduce
los cálculos de negocio. Los contratos se exportan desde FastAPI a OpenAPI y se
generan tipos TypeScript para el cliente.

## Alcance

La instalación es local, para una persona y sin autenticación. Su configuración
funcional es única y tipada. No hay modelos de usuarios, membresías ni
organizaciones, ni selección de capacidades mediante flags de distribución.
Los archivos se almacenan en filesystem local y sus metadatos en PostgreSQL.

## Consistencia e historia

Los servicios controlan commit y rollback. Las migraciones pasan por Alembic.
Los snapshots de costos y presupuestos preservan decisiones históricas; los
movimientos de inventario, ejecuciones y revisiones conservan trazabilidad.
Eso no implica un bus general de eventos ni auditoría de identidad del operador.

Ver [backend](backend.md), [frontend](frontend.md),
[persistencia](persistence_es.md) y [contratos externos](integrations.md).
