# Interfaz comercial: presupuestos, pedidos y proyectos

El listado de presupuestos incorpora accesos a Pedidos y Proyectos. El detalle
muestra el snapshot económico antes de las acciones comerciales.

## Presupuestos

- Un borrador permite editar título, descripción, notas y vigencia. El PATCH
  omite campos no modificados y campos económicos si no se elige modificarlos.
- La edición económica es optativa: markup, ajustes fijos/porcentuales y precio
  manual o sugerido. No hay operaciones monetarias en JavaScript. Total, seña,
  redondeo y validación se obtienen del servidor. Importes y cantidades son texto.
- Los ítems técnicos se gestionan en el [editor de composición independiente](quote_composition_ui_es.md). Se respeta la inmutabilidad de ítems formalizados desde Quick Quote.
- Aprobar y rechazar requieren confirmaciones separadas. No están disponibles
  durante la edición. La aprobación no crea pedidos, proyectos ni producción.
- Rechazo admite un motivo opcional. Presupuestos aprobados/rechazados/vencidos
  se leen sin ofrecer edición. El backend valida siempre las transiciones.
- Un aprobado ofrece conversión explícita. El servidor decide pedido o proyecto;
  la UI navega según el resultado y permite abrir el destino existente, incluso
  cancelado. No se decide ni calcula el destino en el navegador.

## Pedidos y proyectos

Listados y detalles muestran códigos, estados, precios y costos guardados,
componentes/cantidades y notas. El enlace de origen vuelve al Quote. La
cancelación de pendientes requiere confirmación y consulta el estado posterior.
No recalcula snapshots ni toca stock por cuenta propia. Los controles para
[planificar y ejecutar producción](production_ui_es.md) se abren desde cada pedido
o componente del proyecto.

## Conflictos y transporte

- La edición fallida conserva entradas; refetch no las reemplaza. Hay aviso al
  salir con edición comercial sin guardar. Descartar sólo cierra la edición local.
- PATCH no cuenta con versión/ETag: no se promete detectar ediciones simultáneas
  entre dos borradores. Los cambios de estado sí producen conflictos del servidor.
- Aprobar/rechazar/cancelar no se reenvían automáticamente. Ante error se consulta
  el estado; una respuesta perdida puede mostrar el estado ya confirmado junto
  al aviso de transporte. Un rechazo HTTP definitivo no se presenta como incierto.
- Convertir es idempotente por Quote. Se reutiliza la persistencia de solicitudes
  pendientes en un namespace comercial, sin enviar el request_id local al endpoint.
  Recargar y reintentar permite recuperar el mismo destino sin duplicarlo.
- Los listados usan los endpoints existentes sin paginación. No se crea una
  paginación aparente que oculte registros. El catálogo actual no es requerido
  para consultar los snapshots comerciales.

La validación se realiza con las pruebas comerciales y de composición del
frontend; ver [calidad](../development/quality_es.md). Los resultados corresponden
a cada ejecución y no sustituyen la prueba humana.
