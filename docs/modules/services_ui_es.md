# Servicios reutilizables

Acceso desde Más → Servicios reutilizables y desde el editor de receta.

- `/services`: búsqueda y actividad por API, recorriendo todas las páginas.
- `/services/new`: alta y registros actuales para revisar un resultado incierto.
- `/services/{id}`: datos guardados, edición parcial, activación/desactivación y
  vista previa de frase contextual.

Nombre, instrucciones y plantilla se guardan por contratos existentes. Opcionales
vacíos son null. PATCH envía sólo diferencias y actualiza su base tras guardar,
permitiendo volver a un valor anterior. No existe eliminación ni reescritura de
snapshots históricos. Cambios globales afectan usos futuros del catálogo.

El backend valida la plantilla, admitiendo piece/design/product/quantity entre
llaves sin formatos. La vista previa usa action-preview sobre el servicio guardado;
los campos del formulario sin guardar no se aplican. Contextos son etiquetas de
presentación, incluida cantidad: no se calculan consumos ni producción. Valores
vacíos se omiten para que el backend detecte contexto faltante. No hay renderer
local de plantillas ni reinterpretación de sustituciones.

Cambiar contexto, editar servicio, refrescar o salir invalida el resultado. Una
respuesta tardía de un contexto anterior no vuelve a mostrar información obsoleta.
La resolución automática desde opciones continúa en la prueba del producto.

Reutiliza el guard de inventario con scope service para escrituras inciertas.
POST/PATCH no se reenvían automáticamente; aviso por pestaña, consulta de registros
y revisión explícita. Si el almacenamiento está bloqueado, se informa su límite.
Refrescar no sobrescribe borradores. Se avisa al salir con cambios sin guardar.
La API no ofrece ETag: no se garantiza resolución de ediciones simultáneas.

Familias y compatibilidades/composición están disponibles en la [interfaz de
estructura](asset_structure_ui_es.md); características/valores en [Opciones](options_ui_es.md).
Este módulo no cambia backend, OpenAPI ni esquema.
