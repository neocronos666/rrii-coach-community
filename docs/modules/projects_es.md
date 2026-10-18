# Módulo de proyectos

## Finalidad

`Project` representa una ejecución operativa compuesta derivada de un
presupuesto aprobado con dos o más `QuoteItem`. Cada item origina exactamente
un `ProjectComponent`; no se deducen tareas ni subcomponentes de los cálculos
técnicos.

El proyecto conserva los totales técnico, sugerido y final del `Quote`. Cada
componente copia descripción, cantidad y costos técnicos del `QuoteItem`. Los
ajustes comerciales globales no se distribuyen artificialmente entre
componentes.

## Estado y código

Todo proyecto nace `pending` y puede pasar a `cancelled`. No crea producción,
reservas ni consumos. Su código `P-AAAA-NNNNNN` utiliza una secuencia
PostgreSQL independiente y no reiniciable por año.

## API

- `GET /api/v1/projects`, con filtro opcional `status`.
- `GET /api/v1/projects/{project_id}`.
- `POST /api/v1/projects/{project_id}/cancel`.

No existen PATCH, DELETE ni creación directa.
