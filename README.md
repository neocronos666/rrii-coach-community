# RRII-Coach Community

RRII-Coach Community — Repuestos Impresos Coach — organiza el trabajo de un
taller maker: assets digitales, productos y recetas, costos técnicos,
presupuestos, pedidos, proyectos, producción e inventario.

Está pensado para uso local por una persona. Admite hasta dos máquinas activas,
con equipos de distintos tipos. El operador utiliza sus slicers y máquinas por
fuera de la aplicación.

## Estado y alcance

El alcance funcional del frontend está completo. El proyecto está en
estabilización, documentación y preparación de una release candidate; todavía
no hay una release candidate preparada. Esta copia se comparte para evaluación local. Las contribuciones de esta etapa se
concentran en errores, estabilidad, instalación, pruebas y documentación.

Community funciona con PostgreSQL y archivos locales, sin autenticación.
El entorno de prueba publica sus servicios únicamente en loopback.

## Flujo principal

1. Registrar Assets y sus revisiones; definir productos, variantes y recetas.
2. Preparar un Quick Quote o un cálculo técnico y componer un presupuesto.
3. Aprobar y convertir explícitamente el presupuesto en pedido o proyecto.
4. Planificar tareas y registrar intentos de producción, resultados y consumos.
5. Consultar stock, asignar productos y registrar entregas mediante inventario.

También se puede probar una receta mediante Test Print y promover explícitamente
su resultado a stock. Los cálculos y las transiciones se validan en el backend.

## Probar localmente

Requisitos: Docker Engine, Docker Compose >= 2.20 y Bash.

```bash
git clone https://github.com/neocronos666/rrii-coach-community.git
cd rrii-coach-community
./scripts/test-env-up.sh
```

- Aplicación: <http://localhost:13000>
- API: <http://localhost:18000/api/v1>
- OpenAPI: <http://localhost:18000/docs>

Para detener los procesos y conservar la base y los archivos:

```bash
./scripts/test-env-down.sh
```

El script `test-env-reset.sh` es destructivo y exige confirmación. La
[guía del entorno de prueba](docs/development/human_test_environment_es.md)
describe aislamiento, puertos, persistencia y diagnóstico. Este entorno permite
prueba humana; no ejecuta automáticamente las suites de tests.

## Desarrollo y documentación

El backend usa Python 3.13, FastAPI, SQLAlchemy 2.x, Alembic y PostgreSQL 17.
El frontend usa Nuxt 4, Vue 3 y TypeScript, con contratos generados desde OpenAPI.
El dominio se organiza por módulos y las reglas de negocio pertenecen a la API.

- [Alcance Community](docs/domain/community_scope_es.md).
- [Arquitectura](docs/architecture/overview.md) y [decisiones](docs/decisions/).
- [Índice de documentación](docs/README.md) y [módulos](docs/modules/README.md).
- [Recorrido manual](docs/development/frontend_prueba_manual_es.md).
- [Aceptación humana y devolución de resultados](docs/development/local_acceptance_es.md).
- [Entorno de desarrollo](docs/development/local_environment_es.md).
- [Pruebas y calidad](docs/development/quality_es.md).
- [Contribuciones](CONTRIBUTING.md).
- [Plan de estabilización](ROADMAP.md).

Las instrucciones detalladas de desarrollo usan el Compose de desarrollo;
no ejecutar suites que alteren datos sobre una base utilizada para prueba humana.

## Licencia

Todos los derechos reservados. Se comparte para evaluación local bajo los
términos de [LICENSE](LICENSE); no se concede una licencia de código abierto.
