# Instalar y usar el paquete Linux

[Inicio](../../README.md) · [Elegir instalación](README.md) · [Ayuda](../troubleshooting/README.md)

**Disponibilidad:** el paquete está preparado para pruebas locales. Todavía no hay
imágenes ni una Release candidata publicadas. Seguí esta guía si el responsable te
entregó el paquete y preparó sus imágenes; para probar hoy desde un clon, usá el
[entorno del repositorio](../development/human_test_environment_es.md).

## Inicio rápido

1. Descomprimí el paquete y abrí una terminal en la carpeta resultante.
2. Ejecutá `./install.sh`. En una prueba local sin imágenes publicadas, el
   responsable te indicará `./install.sh --offline`.
3. Cuando termine, abrí la URL mostrada: normalmente **http://localhost:18080**.
4. Al terminar, ejecutá `./stop.sh`.
5. La próxima vez, ejecutá `./start.sh`.

No necesitás instalar Python, Node, pnpm ni una base de datos. Los servicios ya
están dentro de las imágenes; el paquete no compila código en tu PC.

| Quiero… | Comando, desde la carpeta instalada |
| --- | --- |
| Instalar por primera vez | `./install.sh` |
| Volver a usar la aplicación | `./start.sh` |
| Detener y conservar mis datos | `./stop.sh` |
| Consultar versión, estado y últimos mensajes | `./status.sh` |
| Actualizar a una versión entregada por el responsable | `./update.sh` |
| Borrar los datos y comenzar de cero | `./reset.sh`, con confirmación explícita |

## Requisitos y sistemas

Necesitás Linux amd64, Bash, Docker Engine local y Docker Compose >= 2.20.
Los scripts también usan `flock` y `ss`, herramientas de sistema de util-linux e
iproute2. No administran servidores Docker remotos ni modifican el sistema con sudo.

| Sistema | Estado de esta preparación |
| --- | --- |
| Linux Mint 22.2 amd64 | Pruebas automatizadas del paquete realizadas localmente; aceptación humana pendiente |
| Debian 12/13 y Ubuntu 22.04/24.04 amd64 | Objetivos de compatibilidad; pendientes de prueba en esos sistemas |
| ARM y otras familias | Fuera del alcance inicial |

Si falta Docker, el script muestra el problema y la guía correspondiente.
Pedí a quien administra tu PC que revise los paquetes existentes y siga la guía
oficial de [Debian](https://docs.docker.com/engine/install/debian/)
o [Ubuntu](https://docs.docker.com/engine/install/ubuntu/).
Docker no declara soporte oficial para derivados como Mint; Mint 22 usa base
Ubuntu 24.04 Noble. Esa condición del proveedor es distinta de las pruebas del
paquete realizadas aquí.

No se desinstalan paquetes ni se cambian grupos, firewall o permisos del socket
automáticamente. Para dudas de acceso, consultá la [ayuda de Docker](../troubleshooting/README.md#falta-docker-o-aparece-permission-denied).

## Conservar tu instalación

Guardá la carpeta instalada. Su `.env` identifica el proyecto y contiene una
contraseña local generada al instalar; se crea con permisos privados.
No copies ese `.env` a otra instalación independiente: ambas administrarían los
mismos datos. Tampoco cambies el nombre del proyecto ni la contraseña una vez
creados los datos.

La parada elimina contenedores y red, conservando base y archivos en volúmenes.
Las imágenes, backups y cachés permanecen en disco. No necesitás resetear para
liberar la memoria de los procesos de la aplicación.

Si el puerto 18080 está ocupado, cambiá sólo `RRII_PORT` en `.env` y repetí el
comando que falló. Si la instalación ya estaba activa, detenela antes.
La aplicación escucha únicamente en esta PC; la base no publica un puerto adicional.
[Más ayuda sobre puertos →](../troubleshooting/README.md#el-puerto-está-ocupado)

## Actualizar sin perder datos

Esperá una versión indicada por el responsable. Copiá los archivos del nuevo paquete
sobre la carpeta instalada, **sin borrar `.env`, archivos de estado ni `backups/`**,
y ejecutá:

```bash
./update.sh
```

Si el responsable confirma que los scripts instalados admiten otra versión,
también podés indicar su número, por ejemplo `./update.sh 0.1.0-rc2`.
Es sólo un ejemplo; no significa que esa versión esté publicada.

El script muestra la versión anterior y la nueva y pide escribir `ACTUALIZAR`.
Descarga imágenes antes de detener la aplicación, guarda un respaldo de base y
archivos con la aplicación parada, actualiza los datos y comprueba que los servicios
estén saludables. No actualiza automáticamente PostgreSQL a otra versión mayor.

Si algo falla, conservá la carpeta y consultá `./status.sh`. No uses reset para
reparar una actualización. No hay rollback automático: volver a una imagen anterior
no revierte el esquema. El responsable debe revisar el fallo y, si corresponde,
restaurar juntos base y archivos en una instalación controlada.

El script conserva `.previous-version` y `.attempted-version` para diagnóstico;
una actualización incompleta impide un arranque incompatible. Reintentar
`./update.sh VERSION` con la versión intentada permite retomar sin borrar datos.
`--offline` en install/update es para imágenes precargadas, sin descarga ni compilación.

## Empezar de cero

`./reset.sh` elimina los datos y archivos de **esa instalación**. Exige escribir
`ELIMINAR` seguido del nombre exacto del proyecto que muestra en pantalla.
Conserva configuración, imágenes y backups; no elimina recursos de otros proyectos.
El siguiente `./start.sh` crea una instancia nueva.

## Probar y pedir ayuda

Seguí la [prueba breve](testing_es.md#prueba-breve), recorré las
[guías de uso](../user-guide/README.md) o consultá la
[ayuda de arranque](../troubleshooting/README.md).
Antes de compartir un reporte, revisá los logs: no adjuntes `.env`, contraseñas,
backups ni archivos privados.
