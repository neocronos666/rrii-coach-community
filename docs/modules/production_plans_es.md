# Generación desde recetas

ProductionPlan representa una generación concreta para un Order o ProjectComponent.
Conserva una copia inmutable de la receta y del cálculo de cantidades. No es una
versión de catálogo: Community sigue editando cada receta actual. El plan agrupa
las tareas generadas y permite reintentar la petición sin duplicarlas.

POST /recipes/{id}/production-preview recibe target_quantity y calcula sin crear
entidades. La receta debe declarar exactamente una salida de su variante final,
con quantity_per_output=1. Puede tener salidas intermedias y pasos sin inventario.

POST /orders/{id}/production-plans o
POST /project-components/{id}/production-plans recibe request_id, recipe_id,
target_quantity y las opciones reserve_supplies/allocate_output, ambas true por
defecto. Crea en una sola transacción el plan, tareas, DAG, reservas Supply por
paso y asignación de producto final al destino. Las opciones pueden desactivarse
explícitamente. Los faltantes advierten; no bloquean.
GET /production-plans/{id} devuelve snapshot, tareas y advertencias de disponibilidad
actual. El snapshot permanece igual aunque se edite o desactive la receta.

## Cantidades y rendimiento

Cada paso tiene cantidad de trabajo por unidad final y rendimiento por tanda.
Se calcula ceil(cantidad requerida / batch_yield). Los componentes ligados a un
source_step_key propagan su demanda hacia atrás: tandas del consumidor por
quantity_per_batch. Las demandas de consumidores compartidos se suman. Así una
tanda de 12 productos, con 4 piezas cada uno, requiere 48 piezas aunque sólo se
hayan pedido 10 productos. Las cantidades se limitan al rango NUMERIC(18,6),
redondeando necesidades hacia arriba a la precisión persistida.

Task conserva como objetivo la necesidad calculada, y el snapshot informa tandas
y capacidad. Run registra el resultado real; puede producir extras. El plan no
inventa consumo real ni ejecuta automáticamente tareas. Los consumos siguen
registrándose manualmente en el cierre de cada Run. Si hay unidades buenas,
se exige registrar el consumo de cada componente obligatorio declarado en el
snapshot. Un intento sin unidades buenas puede cerrarse sin consumo si falló
antes de utilizar material. No se infieren cantidades reales desde la receta.

Las cantidades y dependencias generadas no se editan individualmente. Sí se
pueden ajustar los campos operativos ya autorizados por el lifecycle, como notas,
prioridad o máquina sugerida. El Run verifica el tipo de máquina requerido en el
snapshot, incluyendo cuando el operador cambia la máquina o elige ejecución manual.

Una asignación de 10 y producción de 12 deja físico 12, asignado 10, disponible 2.
La entrega es explícita. Los pasos sin salida inventariable no duplican stock.
Finalizar las tareas no cambia el estado comercial de Order o Project.

## Límites

La planificación incorpora la [resolución configurable de recetas](recipes_es.md).
No hay expansión recursiva automática de recetas alternativas de componentes,
versionado de recetas, workers ni inventario por almacén. Cancelar el destino libera reservas y asignaciones. Cancelar sólo
una tarea no cancela la demanda comercial del plan; liberar su asignación es una
operación explícita. Una receta sin salida final puede guardarse como borrador,
pero no generar un plan productivo.
