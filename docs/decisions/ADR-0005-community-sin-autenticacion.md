# ADR-0005: Community sin autenticación

- Estado: aceptada; alcance revisado el 2026-10-17.
- Fecha original: 2026-07-28.

## Decisión

Community funciona localmente para una persona, sin login, sesiones ni gestión
de credenciales de usuarios. No se agregan modelos de membresías o permisos.

## Consecuencias

Los entornos locales publican puertos sólo en loopback. El aislamiento de red
es parte de la instalación; la aplicación no proporciona control de acceso
por identidad. Agregar autenticación requiere una decisión explícita posterior.
