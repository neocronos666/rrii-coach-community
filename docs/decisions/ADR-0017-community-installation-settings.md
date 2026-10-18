# ADR-0017: Configuración funcional Community sobre SystemSetting

- Estado: aceptada
- Fecha: 2026-08-14

## Contexto

Community necesita una configuración funcional única, pero ya existe un
almacenamiento técnico JSONB y no se justifica otra tabla singleton.

## Decisión

Persistir un documento bajo una clave interna de `SystemSetting` y exponerlo
solo mediante `InstallationSettingsService` y esquemas Pydantic tipados.

## Consecuencias

- El dominio no consulta claves arbitrarias.
- Los defaults funcionan antes de la primera escritura.
- No se crea una tabla adicional ni se expone `SystemSetting` por API.
