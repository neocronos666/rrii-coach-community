# Aceptación humana local

[Guía para testers](../installation/testing_es.md) · [Recorrido de pantallas](frontend_prueba_manual_es.md)

La preparación y los comandos de esta guía corresponden al entorno del repositorio.
Para usar un paquete, seguí su [instalación](../installation/linux_es.md) y aplicá
las mismas comprobaciones de pantallas y persistencia con sus propios scripts.

Este recorrido requiere intervención humana. Los resultados de pytest, Vitest y
Playwright no lo completan automáticamente. Usar datos sintéticos; los datos ya
existentes en el entorno se conservan. No ejecutar reset para comenzar la prueba.

## Preparación

Desde la raíz del checkout que se quiere probar:

```bash
git rev-parse --short HEAD
./scripts/test-env-up.sh
```

Registrar el commit mostrado y abrir <http://localhost:13000>. El script debe
terminar mostrando las URLs útiles. Verificar también
<http://localhost:18000/ready> y <http://localhost:18000/docs>.
No usar el Compose de desarrollo ni ejecutar suites contra esta base.

## Recorrido mínimo

Elegir un sufijo propio para los nombres, por ejemplo `Manual 2026-10-18`.
Registrar los IDs o guardar las URLs de los registros creados.

1. Abrir `/settings`. Anotar los valores actuales; cambiar Nombre del negocio a
   un nombre sintético, confirmar el reemplazo y guardar. Recargar y comprobar
   el valor. No confundir estos datos con las preferencias visuales del dispositivo.
2. Abrir `/machines/new`. Crear una máquina con nombre único, tipo Láser,
   desactivada y precio de compra `123456.7891`. Confirmar los datos y guardar.
   Recargar su detalle y comprobar que conserva los valores. Dejarla desactivada
   evita ocupar un cupo de máquinas activas del entorno.
3. Abrir `/assets`, pulsar Crear recurso, completar Nombre y Descripción y pulsar
   Guardar recurso. En el detalle, adjuntar un archivo de texto sintético mediante
   Archivo para cargar y Adjuntar archivo. Descargarlo y comparar su contenido.
   Guardar la URL del Asset para la comprobación posterior al reinicio.
4. Recorrer el [flujo funcional manual](frontend_prueba_manual_es.md): producto y
   receta → Quick Quote → guardar y formalizar → aprobar → convertir → planificar
   → iniciar y cerrar ejecuciones. Comprobar que cada transición requiere su
   acción explícita y que consultar presupuestos históricos conserva sus valores.
   Registrar las URLs y cantidades utilizadas; un bloqueo o resultado inesperado
   se informa, no se resuelve borrando la base.
5. Desde Producto/variante, Probar receta. Completar los intentos y promover
   explícitamente la cantidad autorizada a stock. Comprobar que cerrar un intento
   y promover son acciones separadas. Consultar el stock resultante en Inventario.
6. Revisar el recorrido con teclado y con un ancho móvil de aproximadamente
   360 px. Comprobar que los controles principales se pueden alcanzar y que el
   menú Más permite abrir Configuración de instalación.

Los puntos 4 y 5 requieren completar los datos reales de receta, recursos e
insumos que solicite la UI. Esta lista es una pauta de aceptación; los tutoriales
con un conjunto de datos paso a paso están en preparación.

## Persistencia y parada

```bash
./scripts/test-env-down.sh
docker ps --filter label=com.docker.compose.project=rrii-community-test
./scripts/test-env-up.sh
```

Después de down, el listado no debe mostrar contenedores del proyecto. Tras up,
abrir las URLs guardadas: deben conservarse la configuración, la máquina, el Asset,
su archivo descargable y los resultados operativos. Verificar el contenido exacto
del archivo nuevamente. No se exige vaciar imágenes o cachés: ocupan disco y no
mantienen los procesos de aplicación en memoria.

Al terminar:

```bash
./scripts/test-env-down.sh
```

Si se cambiaron los puertos, usar los mismos valores de entorno en todos los
comandos, según la [guía del entorno](human_test_environment_es.md).

## Comunicar el resultado

Informar commit, sistema/navegador, fecha, puntos aprobados y cualquier fallo.
Para un fallo, incluir ruta, pasos, resultado esperado y observado, sin secretos
ni archivos personales. Indicar expresamente si se probó down/up con descarga
posterior del archivo y si el entorno quedó detenido.

Un formato breve suficiente:

```text
Commit:
Sistema y navegador:
Fecha:
Configuración / máquina / Asset y archivo:
Producto → Quote → producción:
Test Print → promoción a stock:
Teclado y móvil:
Persistencia tras down/up:
Entorno detenido:
Incidencias:
```

La aceptación completa permanece pendiente hasta revisar este resultado humano. La instalación
para un usuario externo y el empaquetado de release se validan además sobre la RC;
este entorno utiliza imágenes de desarrollo y no debe exponerse públicamente.
