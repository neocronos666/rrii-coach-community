# ADR-0012: Desarrollo contenerizado

- Estado: implementada; alcance revisado el 2026-10-17.
- Fecha original: 2026-07-28.

## Decisión

Aplicación, PostgreSQL, migraciones y herramientas de calidad pueden ejecutarse
con Docker, variables de entorno, volúmenes, healthchecks y scripts versionados.
Backend y frontend están implementados. No se requieren workers externos.

## Consecuencias

`compose.yaml` conserva el flujo de desarrollo. `compose.test-env.yaml` y los
scripts de prueba humana ofrecen un proyecto independiente, con datos persistentes
y puertos de loopback. Las dependencias se fijan mediante lockfiles.
