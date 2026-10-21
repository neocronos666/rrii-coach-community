# Prueba local desde el repositorio

[Inicio](../../README.md) · [Elegir instalación](../installation/README.md) · [Ayuda](../troubleshooting/README.md)

Esta guía usa un clon del repositorio y prepara imágenes desde el código. Si
recibiste un paquete con install.sh, seguí la [guía del paquete](../installation/linux_es.md).

Este entorno permite recorrer la aplicación en la PC y detener sus procesos al
terminar. Es independiente de las suites automatizadas y del Compose de
desarrollo. No requiere el servidor remoto ni Python o Node instalados en el host.

## Requisitos

- Docker Engine iniciado, con permisos de acceso para el usuario.
- Docker Compose 2.20 o posterior (`docker compose version`). La versión antigua
  `docker-compose` 1.x no es compatible.
- Bash y acceso a Internet durante la primera construcción de imágenes.
- Puertos locales 13000 y 18000 libres.

Desde cualquier directorio, ejecutar el script mediante su ruta; los ejemplos
siguientes parten de la raíz del repositorio. No es necesario copiar `.env`.
Estos scripts ignoran el `.env` de desarrollo y utilizan el proyecto fijo
`rrii-community-test`, una red propia y dos volúmenes propios:
`rrii-community-test_postgres_data` y `rrii-community-test_assets_data`.
No ejecutar simultáneamente estos scripts desde dos checkouts: comparten ese
nombre de proyecto en el daemon Docker local.

## Arrancar

```bash
./scripts/test-env-up.sh
```

El script construye las imágenes desde el checkout actual, inicia PostgreSQL y
espera su healthcheck. Detiene la API y el frontend de este proyecto si estaban
activos, aplica `alembic upgrade head` y espera que backend y frontend estén
saludables. Una base existente se actualiza; una base vacía recibe toda la cadena
de migraciones. No realiza downgrade ni elimina datos.

- Aplicación: <http://localhost:13000>
- API: <http://localhost:18000/api/v1>
- OpenAPI: <http://localhost:18000/docs>
- Readiness: <http://localhost:18000/ready>

Usar `localhost` también en el navegador para coincidir con CORS. Los puertos se
publican sólo en loopback. Las credenciales fijas de PostgreSQL son exclusivas de
prueba local y la base no publica puertos al host. No utilizar este Compose como
despliegue público.

El código y las dependencias se copian en imágenes y no se monta el checkout.
La construcción usa los Dockerfiles de desarrollo actuales; todavía no es el
empaquetado definitivo de la RC. Al cambiar código, repetir `up` para reconstruir.
El primer arranque puede tardar por descarga/compilación de dependencias.

## Detener y liberar memoria de los procesos

```bash
./scripts/test-env-down.sh
```

Elimina los contenedores y la red del proyecto. Conserva PostgreSQL y los archivos
de assets en volúmenes; el siguiente `up` los reutiliza. Las imágenes y la caché
de construcción permanecen en disco. Otros proyectos locales continúan activos.

## Reiniciar como una instalación nueva

```bash
./scripts/test-env-reset.sh
```

**Destructivo:** exige escribir exactamente `ELIMINAR rrii-community-test` y
elimina ambos volúmenes, incluidos todos los archivos subidos. Respaldar antes
cualquier dato necesario. EOF o cualquier otra respuesta cancelan la operación.
No existe confirmación implícita ni opción de borrado en `down`.
Después de confirmar, ejecutar `up` para comenzar de nuevo.

## Puertos y diagnóstico

Para usar otros puertos, mantener los mismos valores en cada comando:

```bash
RRII_TEST_FRONTEND_PORT=13001 RRII_TEST_BACKEND_PORT=18001 ./scripts/test-env-up.sh
RRII_TEST_FRONTEND_PORT=13001 RRII_TEST_BACKEND_PORT=18001 ./scripts/test-env-down.sh
```

Los scripts rechazan puertos inválidos o iguales. Si otro proceso ocupa un puerto,
Docker informa el conflicto y el script termina con error conservando datos.
Un arranque fallido puede dejar contenedores para diagnóstico; `down` los retira.

Para consultar estado y logs:

```bash
docker compose --env-file /dev/null -p rrii-community-test -f compose.test-env.yaml ps
docker compose --env-file /dev/null -p rrii-community-test -f compose.test-env.yaml logs --tail 100
```

Una migración fallida impide iniciar la API. Revisar el error y respaldar los
datos antes de intentar una reparación; no usar `reset` como solución automática.
Un binario Compose independiente puede seleccionarse mediante
`RRII_TEST_COMPOSE_BIN=/ruta/al/binario`; se verifica la versión igualmente.

## Prueba humana y automatización

Este arranque no ejecuta pytest, Vitest ni Playwright. El recorrido de pantallas
existente está en [prueba manual](frontend_prueba_manual_es.md). Seguir la
[aceptación local](local_acceptance_es.md) para registrar el recorrido funcional,
la persistencia tras down/up y el resultado humano.
Las pruebas automatizadas deben usar datos aislados y no esta base con trabajo
manual que se quiera conservar.
