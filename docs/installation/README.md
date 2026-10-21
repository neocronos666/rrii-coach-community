# Instalación y primeros pasos

[Inicio](../../README.md) · [Documentación](../README.md) · [Ayuda](../troubleshooting/README.md)

## Elegí tu recorrido

| Tu situación | Qué usar | Dirección habitual |
| --- | --- | --- |
| Querés probar hoy y podés clonar el repositorio | [Prueba desde el repositorio](../development/human_test_environment_es.md) | `http://localhost:13000` |
| Recibiste un paquete y las imágenes de una prueba preparada | [Instalación Linux de usuario](linux_es.md) | `http://localhost:18080` |
| Vas a preparar ese paquete para otra persona | [Construcción y prueba fuera del checkout](local_trial_es.md) | `http://localhost:18080` |
| Vas a modificar el código | [Entorno de desarrollo](../development/local_environment_es.md) | `http://localhost:3000` |

**Disponibilidad:** el repositorio público permite evaluación. La distribución
Linux está en preparación: aún no hay imágenes ni una Release candidata para
descargar. No hace falta buscar un archivo que todavía no se publicó.

El paquete de usuario usa imágenes ya construidas y no compila en tu PC. La prueba
desde el repositorio sí prepara imágenes a partir del código. Cada guía indica qué
comandos corresponden; no mezcles los scripts de un entorno con los de otro.

## Si no tenés Docker

Docker permite que RRII-Coach ejecute sus servicios sin instalar herramientas de
programación en tu sistema. El paquete detecta si falta y muestra una guía; no
modifica el sistema ni pide sudo automáticamente.

Pedí a quien administra tu PC que siga la guía de [Docker para Debian](https://docs.docker.com/engine/install/debian/)
o [Docker para Ubuntu](https://docs.docker.com/engine/install/ubuntu/), según el sistema.
Para Mint se debe revisar la versión base de Ubuntu. [Requisitos y matriz de pruebas](linux_es.md#requisitos-y-sistemas).

## Después de arrancar

1. Abrí la URL que muestra el script.
2. Seguí las [guías de uso](../user-guide/README.md) o el [recorrido para testers](testing_es.md).
3. Detené la aplicación con el comando de tu entorno cuando termines; los datos
   se conservan.

**Detener conserva datos. Resetear los borra.** No necesitás resetear para salir
ni para informar un problema.
