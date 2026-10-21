# Contribuir a RRII-Coach Community

Si querés ayudar como usuario o tester, empezá por [cómo probar y reportar](docs/installation/testing_es.md).
Para modificar el código, seguí los pasos de esta página.

[Inicio](README.md) · [Documentación](docs/README.md)

## Requisitos y preparación

El entorno oficial requiere Docker Engine, Docker Compose y GNU Make. Seguir
el [inicio rápido](README.md#probar-ahora-desde-el-repositorio) y la
[guía de desarrollo](docs/development/local_environment_es.md).

## Ramas

`main` representa código integrable y validado. Crear ramas cortas con alguno
de estos prefijos:

```text
feature/*
fix/*
docs/*
chore/*
```

No se utiliza Git Flow completo.

## Calidad y pruebas

Antes de abrir un pull request:

```bash
make check
make ci
make precommit-all
git diff --check
```

Cuando cambie el contrato FastAPI, ejecutar `make openapi` e incluir juntos
`frontend/openapi.json` y los tipos TypeScript generados. No mantener contratos
duplicados manualmente.

Los commits siguen la convención documentada en
[la guía de commits](docs/development/commits_es.md).

## Pull requests

El cambio debe tener alcance acotado, pruebas proporcionales, riesgos
documentados y CI aprobado. Actualizar documentación cuando cambie el
comportamiento o el flujo de desarrollo.

La documentación para usuarios y desarrolladores se escribe en castellano.
Los nombres técnicos internos se escriben en inglés cuando sea la convención.

El alcance funcional está congelado: se aceptan correcciones, estabilidad, UX
menor sin ampliar alcance, refactors necesarios, instalación, pruebas,
documentación, empaquetado, seguridad y CI/CD. No incorporar capacidades ocultas
ni flags de distribución. No agregar
secretos, credenciales, datos de clientes, assets privados ni archivos de
fabricación.

## Migraciones futuras

Toda modificación futura del esquema deberá incluir una migración Alembic
revisable y su estrategia de reversión. No reescribir migraciones ya aplicadas
en entornos compartidos ni ejecutar operaciones destructivas sin autorización.

## Condiciones de evaluación

Todos los derechos reservados, según [LICENSE](LICENSE). La publicación vigente
permite evaluación local; los aportes de código requieren acordar previamente sus
condiciones de uso. Nuevos artefactos y cambios públicos requieren autorización.
