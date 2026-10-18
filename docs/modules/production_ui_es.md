# Interfaz de producción comercial

## Acceso

- `/orders/{id}` → **Planificar producción** para el pedido.
- `/projects/{id}` → **Planificar producción** dentro del componente elegido.
- `/production/plans/new?order={id}` o
  `/production/plans/new?project={id}&component={id}`: alta contextual.
- `/production/plans/{id}`: snapshot, configuración, omisiones, tareas y
  advertencias de disponibilidad actual. La asignación de salida se identifica
  si se solicitó al crear.
- `/production`: cola con filtros de estado, prioridad y máquina. Los enlaces
  desde destinos filtran por pedido o componente; también admite `?project={id}`.
- `/production/tasks/{id}`: objetivo, descripción, prerrequisitos enlazados,
  recursos guardados, progreso, intentos y resultados/consumos.

## Planificar

El operador elige producto, variante, receta base o heredada, cantidad física y
opciones. Omitir una característica usa sus defaults; la selección explícita
vacía los desactiva. La cantidad comercial se muestra como referencia, nunca se
convierte en demanda física automáticamente. El presupuesto de origen está a un
clic. El contrato del destino no fija receta ni configuración: la elección debe
contrastarse con lo presupuestado.

La vista previa sólo lee. Cambiar entradas la invalida incluso si una petición
anterior sigue en vuelo. Se muestran cantidades, tandas, capacidades y omisiones
calculadas por el servidor. Crear exige preview y confirmación, pero vuelve a
resolver la receta vigente y puede diferir si el catálogo cambió entre ambas.
No es reserva ni garantía de congelación previa.

Reserva de insumos y asignación de salida son casillas independientes, activadas
por defecto como en el contrato. Sus efectos se explican antes de confirmar.
Máquinas pueden asignarse a los pasos en esta etapa o al iniciar cada intento;
la API valida tipo y que servicios/esperas no asignen máquina.

## Ejecutar y recuperar

Iniciar distingue asignación guardada, máquina explícita y sin máquina. La API
valida ocupación, estado y prerrequisitos. No se calcula habilitación del DAG en
el navegador. El progreso (buenas, fallidas, faltantes y excedentes) viene de API.

Cerrar declara resultados y consumos reales; nunca precarga consumos estimados.
El total consumido incluye desperdicio. A diferencia de Test Print, el cierre
comercial ingresa la salida inventariable buena al stock: no tiene promoción
posterior. Tampoco entrega ni finaliza comercialmente el pedido/proyecto.

Creación de plan e inicio de intento conservan request_id y cuerpo. El cierre
conserva el cuerpo para reenvío idempotente por run_id. Namespace `production`
separa solicitudes de Test Print; puede retomarse tras recarga en la misma pestaña
si sessionStorage está disponible. Al faltar almacenamiento, hay aviso y estado
en memoria. Un error HTTP definitivo permite corregir; transporte incierto exige
recuperar la misma solicitud. El UUID del sobre local no se envía en el cierre.

Pausar, reanudar y cancelar requieren confirmación. No se reenvían automáticamente;
se relee el estado para resolver conflictos/respuestas perdidas. Cancelar no
revierte consumos ni libera la asignación comercial del plan. Los mensajes se
conservan aunque la tarea haya cambiado de estado durante la petición.

Las unidades de insumos abiertas se consultan en catálogo actual (identificado
como tal); los consumos históricos muestran sus propias unidades persistidas.
Los nombres actuales ayudan a reconocer identificadores sin reemplazar snapshots.

## Límites

No hay edición de cantidades/dependencias del plan generado. El [editor operativo](production_editor_ui_es.md) incorpora alta manual, edición, dependencias, lifecycle legacy, timestamps y consumos adicionales. Los controles de
[inventario](inventory_ui_es.md) permiten gestionar reservas desde tarea y
liberar asignaciones o entregar desde el enlace del plan/destino.
Una tarea con snapshot ilegible no habilita nuevos intentos ni formulario de
cierre; informa el problema en lugar de reconstruirlo desde el catálogo vigente.
No existe listado independiente de planes en la API: se retoman desde sus tareas.

Sin cambios de backend, esquema, contratos generados ni dependencias.
