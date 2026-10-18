# ADR-0007: Una instalación local

- Estado: aceptada; alcance revisado el 2026-10-17.
- Fecha original: 2026-07-28.

## Decisión

Community tiene una única configuración funcional de instalación. No implementa
organizaciones, aislamiento por empresa, membresías ni políticas Row-Level
Security. No se agregan columnas o abstracciones para anticipar esos conceptos.

## Consecuencias

La separación entre entornos de prueba y desarrollo se realiza mediante proyectos
Compose, redes y volúmenes propios. Esta revisión corrige documentación
conceptual antigua; no modifica modelos ni migraciones históricas.
