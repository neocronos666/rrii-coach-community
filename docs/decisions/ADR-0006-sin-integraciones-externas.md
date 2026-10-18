# ADR-0006: Funcionamiento sin integraciones externas

- Estado: aceptada; alcance revisado el 2026-10-17.
- Fecha original: 2026-07-28.

## Decisión

La instalación no requiere conectores ERP ni facturación fiscal. No se mantienen
carpetas vacías o módulos de integración como promesa de desarrollo futuro.
Los flujos implementados dependen de la API, PostgreSQL y archivos locales.

## Consecuencias

El uso de slicers y máquinas se realiza fuera del sistema. Los límites externos
se documentan en [arquitectura](../architecture/integrations.md).
