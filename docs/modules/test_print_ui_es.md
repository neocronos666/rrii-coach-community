# Interfaz de pruebas de receta completa

10B.9 conecta las APIs existentes de TestPrint y ProductionRun. En Producto,
cada variante ofrece «Probar receta» y «Ver pruebas». No hay prueba de Asset
independiente ni ejecución implícita de una única impresión.

## Recorrido

- Alta con variante fijada, receta base/heredada, cantidad y selecciones.
  Defaults y selección explícita vacía se transmiten de forma distinta. Una
  selección incompatible con una receta heredada se rechaza por API.
- Listado paginado por variante y detalle con snapshot, pasos omitidos,
  dependencias, recursos, materiales, cantidades, configuración elegida y progreso
  informado por API.
- Cada paso muestra sus intentos y permite iniciar otro cuando la prueba está
  abierta. El backend valida prerequisitos, tipos y ocupación de máquinas.
  La máquina puede tomar la asignación guardada, ser explícita o quedar ausente.
- Cierre con buenas, fallidas, motivo, duración real opcional y notas. Inicio/fin usan la hora del servidor por defecto; las opciones de ejecución permiten fechas explícitas y override de parámetros.
- Consumos obligatorios del snapshot, con cantidades reales ingresadas por el
  operador. No se copian cantidades estimadas como consumos reales. Puede omitirse
  una fila de consumo de forma explícita; el backend rechaza faltantes obligatorios
  cuando hay unidades buenas. Se pueden agregar materiales/componentes adicionales desde el selector de consumos reales.
- El consumo total incluye el desperdicio. Se identifica el paso proveedor de
  componentes internos. Los cierres no ingresan automáticamente la salida al stock.
- Promoción con cantidad y confirmación explícitas: una sola por prueba, incluso
  parcial, siempre a su variante. El movimiento guardado y su cantidad se consultan en el ledger tras promover.
- Cancelación explícita sin borrar historia ni revertir consumos; la API rechaza
  pruebas con intentos abiertos. El estado y la cantidad promovible son del backend.

## Historia y recuperación

Se lee el snapshot guardado, validando su estructura antes de ejecutar un paso.
Las ayudas de nombres se identifican como nombres actuales y son opcionales:
si el catálogo no responde, permanecen los identificadores y las unidades guardadas.
No se reconstruye ni se cambia la historia usando nombres actuales.

Los reintentos de transporte se comparten con Quick Quote en `features/shared`.
Se conserva compatibilidad con las claves de solicitudes pendientes de ese módulo.
Test print usa su propio namespace, separado por API, operación y entidad.
Crear, iniciar y promover conservan request_id/cuerpo; cerrar conserva su cuerpo
exacto y el run_id, retirando del envío el UUID del sobre local. Cancelar es
idempotente por ID. Lecturas posteriores no eliminan un reintento todavía pendiente.

Un resultado incierto se puede recuperar tras recargar en la misma pestaña si
sessionStorage está disponible. Con almacenamiento bloqueado se conserva en
memoria y se informa su limitación. Un error definitivo permite corregir la entrada;
refetch no la sobrescribe. Hay aviso al abandonar resultados sin guardar.

## Validación

Unitarias: transporte decimal, omisión de máquina frente a null explícito,
paginación de intentos/movimientos, conflictos y estructura de snapshot. E2E real sobre PostgreSQL:
receta con impresión, servicio, espera y ensamblado; fallos y tandas parciales;
consumo interno, exclusividad, rechazo de cancelación con intento abierto,
finalización sin entrada automática a stock, promoción parcial única, reintentos
tras respuesta perdida en creación/inicio/cierre/promoción y cancelación.
Axe y capturas móvil/escritorio complementan las pruebas funcionales.

El [dashboard actual](dashboard_live_ui_es.md) consulta datos reales. La cobertura
descrita debe verificarse ejecutando las pruebas; ver
[calidad](../development/quality_es.md). No equivale a aceptación humana.

## Vista previa antes de crear

«Previsualizar receta» consulta `production-preview` con la variante, receta,
cantidad y selecciones elegidas. Muestra las claves de todos los pasos activos,
cantidades requeridas, tandas, capacidades y omisiones calculadas por backend.
No escribe TestPrint ni stock. Cambiar una entrada invalida el resultado, incluso
si la petición anterior termina después. La creación vuelve a resolver y guarda
la receta vigente; la vista previa no constituye una reserva ni un snapshot.
