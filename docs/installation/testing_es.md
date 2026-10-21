# Probar Community y compartir resultados

[Inicio](../../README.md) · [Instalación](README.md) · [Guías de uso](../user-guide/README.md) · [Ayuda](../troubleshooting/README.md)

Gracias por ayudar a probar. No hace falta revisar todo en una sola sesión:
una prueba breve con pasos claros también aporta información útil.

## Elegí cómo arrancar

- **Desde el repositorio:** [arranque y parada](../development/human_test_environment_es.md),
  normalmente en `http://localhost:13000`.
- **Paquete preparado por el responsable:** [instalación de usuario](linux_es.md),
  normalmente en `http://localhost:18080`. Mientras no haya imágenes publicadas,
  necesitás que el responsable prepare las imágenes en esa PC.

## Prueba breve

Usá nombres y archivos de muestra que puedas compartir.

1. Abrí Inicio y recorré las secciones principales.
2. En Biblioteca, creá un recurso y adjuntá un archivo de texto. Descargalo y
   comprobá que conserva su contenido; guardá la URL del Asset.
3. En Máquinas, creá un equipo con nombre reconocible. Podés dejarlo desactivado
   para no ocupar uno de los dos lugares de máquinas activas.
4. Recargá las páginas y comprobá que siguen los datos.
5. Detené y volvé a arrancar con los scripts de **ese mismo entorno**.
6. Abrí la URL guardada y descargá nuevamente el archivo. Al terminar, detené
   la aplicación para liberar la memoria de sus procesos.

No uses reset durante este recorrido: borraría precisamente los datos que
queremos comprobar. Si ya tenés datos propios, no hace falta empezar de cero.

## Prueba del flujo completo

Seguí [productos](../modules/product_editor_ui_es.md), [Quick Quote](../modules/quick_quote_ui_es.md),
[presupuestos](../modules/commercial_ui_es.md), [producción](../modules/production_editor_ui_es.md)
y [Test Print](../modules/test_print_ui_es.md). El [recorrido de aceptación](../development/local_acceptance_es.md)
detalla qué observar; sus comandos de preparación son los del entorno del repositorio.
Si usás el paquete, reemplazalos por los de la [guía del paquete](linux_es.md).

Anotá cantidades, precios y URLs utilizadas. No marques como probado un paso que
no llegaste a completar. Una prueba superficial no equivale a aceptación completa.

## Reportar un problema

Abrí un [reporte de error](https://github.com/neocronos666/rrii-coach-community/issues/new?template=bug_report_es.yml)
con esta información:

```text
Versión o commit:
Sistema y navegador:
Entorno: paquete / repositorio / desarrollo
Pasos para reproducir:
Qué esperaba:
Qué ocurrió:
¿Se repite al recargar?:
```

Si usás el paquete, `./status.sh` muestra la versión, el estado y los últimos logs.
Desde un clon, `git rev-parse --short HEAD` identifica el commit. Una captura puede
ayudar, siempre que no incluya datos personales. No adjuntes `.env`, contraseñas,
backups ni archivos privados; revisá los logs antes de compartirlos.

Para una duda de uso podés abrir una [consulta en Issues](https://github.com/neocronos666/rrii-coach-community/issues/new).
Los [tests automatizados](../development/quality_es.md) se ejecutan aparte y usan
sus propios datos; no reemplazan este recorrido humano.
