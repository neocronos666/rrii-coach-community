# RRII-Coach Community

**Organizá el trabajo de tu taller maker, desde el diseño hasta la entrega.**

RRII-Coach Community — Repuestos Impresos Coach — reúne recursos digitales,
productos, recetas, costos, presupuestos, producción e inventario. Está pensado
para uso local por una persona y admite hasta dos máquinas activas de distintos
tipos. Seguís usando tus slicers y equipos por fuera de la aplicación.

[Documentación](docs/README.md) · [Instalación Linux](docs/installation/README.md) ·
[Guías de uso](docs/user-guide/README.md) · [Reportar un problema](https://github.com/neocronos666/rrii-coach-community/issues/new?template=bug_report_es.yml)

## 🧭 Elegí por dónde empezar

| Quiero… | Empezar aquí |
| --- | --- |
| Probarlo ahora desde el repositorio | [Inicio rápido](#probar-ahora-desde-el-repositorio) |
| Usar un paquete sin compilar | [Distribución Linux: disponibilidad y requisitos](docs/installation/README.md) |
| Entender las pantallas y el flujo | [Guías de uso](docs/user-guide/README.md) |
| Ayudar como tester | [Recorrido y devolución de resultados](docs/installation/testing_es.md) |
| Trabajar en el código | [Entorno de desarrollo](docs/development/local_environment_es.md) y [contribuciones](CONTRIBUTING.md) |

## Estado del proyecto

El alcance funcional está completo y congelado. Estamos estabilizando instalación,
pruebas y documentación. El repositorio se comparte **para evaluación**; todavía
no hay una Release candidata ni imágenes de distribución publicadas.

La preparación local del paquete Linux ya existe. Su instalación usa imágenes
preconstruidas, sin pedir Python, Node ni una base de datos al usuario. Hasta que
se publiquen esas imágenes, necesita una preparación local por parte del responsable;
[la guía explica ese paso](docs/installation/local_trial_es.md).
Los datos demo y los tutoriales con un dataset completo siguen pendientes.

Community funciona sin autenticación. Los entornos incluidos publican la aplicación
sólo en esta PC; no están preparados para exponerla directamente a Internet.

## Del diseño al trabajo terminado

1. Guardá **Assets**: diseños o recursos digitales, con sus revisiones y archivos.
2. Definí **productos y recetas**: qué vas a fabricar y qué pasos requiere.
3. Prepará un **Quick Quote** o cálculo técnico y formalizá un **presupuesto (Quote)**.
4. Aprobá y convertí explícitamente el presupuesto en **pedido o proyecto**.
5. Planificá tareas y registrá **intentos de producción**, resultados y consumos.
6. Consultá **stock**, asigná productos y registrá entregas.

También podés probar una receta mediante **Test Print** y promover explícitamente
su resultado a stock. Aprobar un presupuesto, producir y entregar son acciones
separadas. [Ver las guías de cada área →](docs/user-guide/README.md)

## Probar ahora desde el repositorio

Este camino requiere Git, Bash, Docker Engine y Docker Compose >= 2.20.
El script prepara las imágenes automáticamente desde el código; la primera vez
necesita Internet y puede tardar. Para una persona que recibe un paquete ya preparado,
seguí la [guía de instalación de usuario](docs/installation/linux_es.md).

```bash
git clone https://github.com/neocronos666/rrii-coach-community.git
cd rrii-coach-community
./scripts/test-env-up.sh
```

Abrí **[http://localhost:13000](http://localhost:13000)**. Para terminar y conservar
la base y los archivos:

```bash
./scripts/test-env-down.sh
```

Podés volver con `./scripts/test-env-up.sh`. La parada retira los contenedores y
libera la memoria de sus procesos; los datos permanecen en volúmenes.

[Guía detallada del entorno](docs/development/human_test_environment_es.md) ·
[Qué probar](docs/installation/testing_es.md) ·
[Si algo no arranca](docs/troubleshooting/README.md)

## Tres entornos, tres usos

| Entorno | Dirección habitual | Arrancar / detener | Datos |
| --- | --- | --- | --- |
| Prueba desde el repositorio | `http://localhost:13000` | `scripts/test-env-up.sh` / `scripts/test-env-down.sh` | Se conservan al detener |
| Paquete Linux preparado | `http://localhost:18080` | `install.sh` la primera vez; luego `start.sh` / `stop.sh` | Se conservan al detener |
| Desarrollo | `http://localhost:3000` | [Guía de desarrollo](docs/development/local_environment_es.md) | Entorno propio |

Los puertos son configurables. Los scripts de **reset borran datos** y requieren
confirmación; no hacen falta para una prueba normal. Las suites automatizadas usan
bases separadas de la prueba humana.

## Desarrollo y colaboración

El backend usa Python 3.13, FastAPI, SQLAlchemy 2.x, Alembic y PostgreSQL 17.
El frontend usa Nuxt 4, Vue 3 y TypeScript. La API define contratos y reglas de negocio.

- [Documentación completa](docs/README.md), [arquitectura](docs/architecture/overview.md)
  y [decisiones técnicas](docs/decisions/).
- [Pruebas y calidad](docs/development/quality_es.md), [contribuciones](CONTRIBUTING.md)
  y [registro de cambios](CHANGELOG.md).
- [Errores y consultas](https://github.com/neocronos666/rrii-coach-community/issues)
  y [plan de mantenimiento](ROADMAP.md).

Se aceptan correcciones, estabilidad, instalación, pruebas y documentación dentro
del alcance Community. Un reporte con pasos claros ayuda mucho: [cómo prepararlo](docs/installation/testing_es.md#reportar-un-problema).

## Licencia

Todos los derechos reservados. Se comparte para evaluación local bajo los
[términos de LICENSE](LICENSE); no se concede una licencia de código abierto.
