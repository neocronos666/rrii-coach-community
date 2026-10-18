# ADR-0020: Supply como recurso físico genérico

## Estado

Aceptada el 15 de agosto de 2026.

## Decisión

La entidad raíz es `Supply`, no `Filament` ni `Material`. Una categoría Python
clasifica el recurso sin restringir sus usos futuros. Propiedades particulares
se modelarán después mediante relaciones explícitas, no columnas especializadas
ni JSONB indiscriminado.

## Consecuencias

El catálogo representa materiales, componentes, consumibles, embalajes,
repuestos y mercadería con una API común. El futuro módulo comercial decidirá
cómo se vende cada recurso.
