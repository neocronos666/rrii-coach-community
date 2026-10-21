# Documentación de RRII-Coach Community

Bienvenido. Elegí el recorrido que se parece a lo que necesitás hacer; no hace
falta leer la documentación técnica para empezar a probar la aplicación.

[Volver al inicio](../README.md)

## 🧭 Empezar

| Necesito… | Guía |
| --- | --- |
| Elegir cómo instalar o probar | [Instalación y primeros pasos](installation/README.md) |
| Usar un paquete de usuario | [Instalación Linux](installation/linux_es.md) |
| Probar desde un clon del repositorio | [Entorno local de prueba](development/human_test_environment_es.md) |
| Entender qué hacer en cada pantalla | [Guías de uso](user-guide/README.md) |
| Comprobar el funcionamiento y compartir resultados | [Guía para testers](installation/testing_es.md) |
| Resolver un arranque fallido, puertos o dudas sobre datos | [Ayuda y problemas frecuentes](troubleshooting/README.md) |

El paquete Linux está preparado localmente; sus imágenes y una Release candidata
**todavía no están publicadas**. La [preparación fuera del checkout](installation/local_trial_es.md)
es para el responsable que entrega esa prueba. No hace falta para el recorrido
desde el repositorio.

## Usar y entender Community

- [Guías de uso por tarea](user-guide/README.md).
- [Alcance y límites actuales](domain/community_scope_es.md).
- [Recorrido de pantallas](development/frontend_prueba_manual_es.md).
- [Índice de módulos: interfaz y contratos](modules/README.md).

Las guías describen el comportamiento que existe. Los tutoriales con un conjunto
de datos completo y la carga demo están en preparación; no son capacidades ya
incluidas en la instalación.

## Desarrollar y mantener

- [Preparar el entorno de desarrollo](development/local_environment_es.md).
- [Ejecutar pruebas y controles de calidad](development/quality_es.md).
- [PostgreSQL y migraciones](development/database_es.md).
- [Construir y verificar el paquete Linux](installation/local_trial_es.md).
- [Contribuir](../CONTRIBUTING.md) y [escribir commits](development/commits_es.md).
- [Plan de mantenimiento](../ROADMAP.md) y [cambios](../CHANGELOG.md).

## Referencia técnica

- [Arquitectura general](architecture/overview.md), [backend](architecture/backend.md)
  y [frontend](architecture/frontend.md).
- [Distribución Linux](installation/distribution_design_es.md).
- [Entidades](domain/entities_es.md), [reglas](domain/business_rules_es.md),
  [relaciones](domain/erd_draft_es.md) y [estados](domain/states_es.md).
- [Decisiones técnicas](decisions/).
- [Propuesta de datos demo](installation/demo_proposal_es.md), todavía sin implementar.
