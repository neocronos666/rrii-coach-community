# Módulos del dominio

La estructura es modular dentro de una API; no exige microservicios ni workers.

| Módulo | Responsabilidad |
| --- | --- |
| `installation` | Configuración funcional única y tarifas |
| `machines` | Datos del equipo, activación y límite de máquinas |
| `assets` | Biblioteca, archivos, revisiones, familias, composición y compatibilidad |
| `options` | Definiciones, valores y configuración de productos |
| `products` | Productos, variantes, stock, asignaciones y entregas |
| `recipes` | Recetas, pasos, inputs y servicios reutilizables |
| `supplies` | Insumos, presentaciones, compras, movimientos y reservas |
| `costing` | Cálculos técnicos y preview de recetas |
| `quick_quotes` | Borradores, revisiones guardadas y formalización |
| `quotes` | Snapshots comerciales, aprobación y conversión explícita |
| `orders`, `projects` | Destinos operativos creados por conversión |
| `production` | Planes, tareas, DAG, intentos, consumos y Test Print |

Las operaciones que cruzan módulos pasan por servicios con transacciones
explícitas. El frontend coordina la interacción mediante contratos OpenAPI.
No se crean módulos para conceptos que no están implementados.
