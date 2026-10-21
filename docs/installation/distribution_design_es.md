# Arquitectura de la distribución Linux

[Documentación](../README.md) · [Instalación de usuario](linux_es.md) · [Preparación local](local_trial_es.md)

Esta referencia es para desarrolladores y responsables de distribución. El usuario
puede comenzar por el [inicio rápido del paquete](linux_es.md#inicio-rápido).

## Dos caminos separados

El Compose de desarrollo y el de prueba desde el repositorio conservan sus flujos.
La distribución de usuario vive en `distribution/`: imágenes preconstruidas, sin
builds ni bind mounts a fuentes. El constructor usa una lista cerrada de doce
archivos y genera tar.gz y checksum; no copia el árbol del proyecto.

La versión interna es 0.1.0; 0.1.0-rc1 es la candidata de trabajo local, sin tag ni
Release publicados. Las imágenes usan tags explícitos. Los nombres previstos son
`ghcr.io/neocronos666/rrii-coach-community-backend:VERSION` y
`ghcr.io/neocronos666/rrii-coach-community-frontend:VERSION`.

## Servicios y red

Navegador → frontend compilado → proxy `/api/**` → backend → PostgreSQL.

El proxy de Nuxt sólo transporta solicitudes; las reglas de negocio permanecen en
la API. Hay un puerto de loopback configurable y una red propia por instalación.
La API y la base no publican puertos adicionales. Los procesos backend/frontend
usan UID 10001; el runtime no incluye tests de aplicación ni Chromium.

Cada instalación genera un nombre de proyecto y una contraseña aleatorios. `.env`
se lee como datos y se conserva con permisos 0600. La base y los archivos de Assets
persisten en dos volúmenes propios. Las operaciones en una carpeta se serializan
con un lock; stop y reset tienen efectos distintos y explícitos.

## Actualización

Se descarga la versión solicitada antes de detener la aplicación. Con sus servicios
parados se guardan un dump PostgreSQL y un tar de archivos. Se aplican migraciones
y sólo se registra nueva versión instalada tras superar healthchecks.

La versión anterior, la intentada y los backups permiten diagnosticar fallos.
No hay rollback automático del esquema ni actualización de PostgreSQL entre versiones
mayores. El reset confirmado elimina los volúmenes de esa instalación y limpia una
marca de actualización incompleta para permitir volver a empezar.

## Validación y límites

La [prueba del artefacto](local_trial_es.md) comprueba instalación limpia, acceso,
persistencia, reset, migración desde un esquema histórico y conflicto de puerto.
El escenario de actualización reutiliza el mismo build etiquetado de nuevo: todavía
no hay dos releases binarias distintas para verificar ese salto real.

La matriz de sistemas y su evidencia están en [requisitos](linux_es.md#requisitos-y-sistemas).
La [propuesta de demo](demo_proposal_es.md) usa APIs y datos sintéticos en una
instalación separada, y sigue pendiente de aprobación e implementación.

El workflow manual `prepare-distribution.yml` prepara candidatos tras superar las
pruebas. No tiene pasos de login, push de imágenes ni publicación de Release.
Publicar imágenes o releases requiere una autorización separada.
