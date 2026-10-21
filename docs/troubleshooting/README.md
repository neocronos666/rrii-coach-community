# Ayuda y problemas frecuentes

[Inicio](../../README.md) · [Instalación](../installation/README.md) · [Guías de uso](../user-guide/README.md)

## No sé qué instrucciones seguir

Si tenés `install.sh`, `start.sh` y `stop.sh` en la carpeta que recibiste, seguí
la [guía del paquete Linux](../installation/linux_es.md).
Si clonaste el repositorio y usás `scripts/test-env-up.sh`, seguí el
[entorno de prueba del repositorio](../development/human_test_environment_es.md).
No comparten los mismos nombres de proyecto, datos ni puertos predeterminados.

## No encuentro una Release para descargar

El paquete Linux está en preparación. Aún no se publicaron sus imágenes ni una
Release candidata. Podés [probar desde el repositorio](../../README.md#probar-ahora-desde-el-repositorio)
o pedir una [prueba preparada localmente](../installation/local_trial_es.md).
No necesitás crear una cuenta en un registry para resolver esta espera.

## Falta Docker o aparece «permission denied»

RRII-Coach necesita Docker en ejecución y permisos para acceder a su servicio.
El instalador no modifica el sistema. Pedí ayuda a quien administra la PC y
consultá los [requisitos](../installation/linux_es.md#requisitos-y-sistemas).
No hace falta instalar Python ni Node para usar el paquete.

Si aparece «permission denied», puede faltar acceso al servicio aunque Docker
esté instalado. No cambies los permisos del socket ni pruebes comandos
administrativos al azar: la guía de Docker explica la configuración del sistema.

## El puerto está ocupado

| Entorno | Qué cambiar |
| --- | --- |
| Paquete | Detené esa instalación si está activa, editá sólo `RRII_PORT` en su `.env` y repetí el comando que falló |
| Repositorio | Usá otros valores de `RRII_TEST_FRONTEND_PORT` y `RRII_TEST_BACKEND_PORT`, como indica la [guía](../development/human_test_environment_es.md#puertos-y-diagnóstico) |

Abrí después la nueva URL que muestre el script. No borres volúmenes para cambiar
un puerto. En el paquete, conservá las demás variables de `.env`.

## El paquete muestra «pull access denied» o no encuentra una imagen

Primero confirmá si recibiste una prueba local: mientras las imágenes no estén
publicadas, el responsable debe prepararlas en esa PC y pedirte usar
`./install.sh --offline`. Ese modo **no** descarga ni construye imágenes.
Si el responsable ya confirmó una publicación, verificá conexión y versión con él.
No uses `latest` ni reemplaces la versión por una elegida al azar.

## El arranque falló o la página no abre

Esperá que el script termine y muestre la URL; el primer arranque desde el
repositorio incluye construcción de imágenes y puede tardar.

- **Paquete:** ejecutá `./status.sh` en la carpeta instalada.
- **Repositorio:** consultá los [comandos de estado y logs](../development/human_test_environment_es.md#puertos-y-diagnóstico).

Revisá primero el mensaje anterior al error. Si no alcanza,
[reportá los pasos y el mensaje](../installation/testing_es.md#reportar-un-problema).
No hace falta resetear para obtener un diagnóstico.

## ¿Qué se conserva cuando detengo la aplicación?

La base, los archivos adjuntos y la configuración. Los contenedores se retiran;
las imágenes y los datos persistentes siguen en disco. Linux puede conservar
caché y otros programas continúan usando RAM, por lo que la cifra global de memoria
no tiene que volver exactamente al mismo valor.

**Reset sí elimina datos.** Pide una frase explícita y sólo afecta los volúmenes
del entorno correspondiente. No lo uses como una forma de cerrar la aplicación.

## La actualización no terminó

Conservá la carpeta instalada, `.env`, archivos de estado y `backups/`.
Consultá `./status.sh` y compartí un reporte sin secretos. La versión anterior y la
intentada ayudan a diagnosticar el problema. No hay rollback automático del esquema:
volver a una imagen anterior puede ser incompatible con los datos migrados.
La [guía de actualización](../installation/linux_es.md#actualizar-sin-perder-datos)
explica cómo reintentar con la versión indicada por el responsable.

## Veo un fallo viejo de GitHub Actions

Cada ejecución está ligada a un commit. «Re-run» vuelve a probar ese mismo commit;
no incorpora cambios posteriores. Revisá el commit de `main` y la
[ejecución de Calidad correspondiente](https://github.com/neocronos666/rrii-coach-community/actions/workflows/ci.yml).
Un fallo histórico permanece visible aunque una versión posterior haya aprobado.

## Quiero ayuda con una pantalla

Buscá la tarea en las [guías de uso](../user-guide/README.md). Si sigue la duda,
abrí una [consulta en Issues](https://github.com/neocronos666/rrii-coach-community/issues/new)
y contá qué estabas intentando hacer. Una descripción corta y concreta es suficiente
para empezar.
