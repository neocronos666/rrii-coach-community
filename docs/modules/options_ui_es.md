# Administración global de opciones y valores

Acceso desde Más → Opciones y valores y desde el editor de configuración de producto.

- `/options`: características con búsqueda/actividad por API y paginación completa.
- `/options/new`: alta y consulta de registros para revisar un resultado incierto.
- `/options/{definition}`: datos guardados, edición/actividad y listado de valores.
- `/options/{definition}/values/new`: alta de valor dentro de la característica.
- `/options/{definition}/values/{value}`: edición, actividad y vínculos opcionales.

El backend comprueba pertenencia; una URL con un valor de otra característica
muestra error y no habilita un editor. No existen borrados ni cambio de identidad.
Desactivar característica no desactiva sus valores ni modifica productos. La
validez de selecciones y resolución sigue en la API, no en esta pantalla.

Valores pueden enlazar una familia y un insumo. Catálogos incluyen registros
inactivos identificados y conservan una referencia actual aunque falle su lectura.
Sin vínculo envía null explícito al guardar. No cambia familia/insumo ni consume
stock. El backend rechaza agregar un insumo inactivo. PATCH sólo envía campos
modificados, por lo que una edición de nombre no reenvía vínculos sin cambios.

Datos guardados se separan del formulario; consultar no descarta borradores.
Guardar actualiza la base de comparación, permitiendo volver a un valor anterior.
Opcionales vacíos se normalizan a null. POST/PATCH no se reenvían automáticamente
ante respuesta incierta: aviso por pestaña con scope de característica/valor,
consulta y revisión explícita antes de otra escritura. Sin sessionStorage, se
informa que el aviso sólo queda en memoria. No hay ETag ni garantías de resolución
de ediciones simultáneas.

Se preserva el editor de configuración por producto, donde se definen valores
permitidos, mínimos/máximos y defaults. Este catálogo no calcula cantidades, no
reescribe recetas ni snapshots y no agrega reglas de negocio en frontend.
Familias, compatibilidades y composición están en la
[interfaz de estructura](asset_structure_ui_es.md).
Sin cambios de backend, esquema, OpenAPI, dependencias ni despliegue.
