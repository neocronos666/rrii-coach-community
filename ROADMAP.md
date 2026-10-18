# Estabilización de RRII-Coach Community

El alcance funcional está congelado. Esta etapa prepara una instalación local
reproducible y una release candidate, sin agregar capacidades nuevas.

## Orden de trabajo

1. Registrar alcance, clasificación de documentos y criterios de cierre.
2. Preparar entorno local aislado con arranque, parada persistente y reset explícito.
3. Conservar decisiones internas fuera del contenido público y revisar documentos.
4. Depurar estructura, restos de desarrollo y enlaces sin romper rutas ni imports.
5. Ejecutar backend, frontend, E2E, tipos, lint, build y comprobaciones Alembic.
6. Verificar instalación limpia, actualización, permisos y prueba humana local.
7. Completar documentación de uso, instalación, contribución y tutoriales reales.
8. Resolver licencia, auditar árbol e historial y preparar `v0.1.0-rc1`.

Esta copia pública se comparte para evaluación local. La documentación de uso y
los tutoriales se completan durante la estabilización. La auditoría del árbol
actual no sustituye la revisión del historial Git.

## Condiciones de publicación

La RC debe instalarse desde instrucciones comprobadas, conservar datos al detener
el entorno y diferenciar verificaciones automáticas de aceptación humana.
Esta publicación para evaluación no constituye una release candidate. Los tags y
releases se prepararán después de completar sus verificaciones.
