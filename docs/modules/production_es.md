# Núcleo de producción

## Modelo

`ProductionTask` es una unidad genérica de trabajo maker —FDM, SLA, CNC,
láser, posprocesado, ensamblaje, trabajo manual u otro proceso— y pertenece
exactamente a un `Order` o a un `ProjectComponent`. La máquina es opcional.

Las tareas se crean exclusivamente desde las rutas de su `Order` o
`ProjectComponent`; el origen, código, estado y timestamps no forman parte del
payload. Los [intentos](production_runs_es.md), [reservas](supply_reservations_es.md)
y [consumos](production_consumption_es.md) tienen contratos propios. No hay
evaluación de calidad ni cierre automático del origen.

## Ciclo de vida

Toda tarea nace `queued`. Puede iniciarse, pausarse, reanudarse, finalizarse
o cancelarse mediante `ProductionTaskService`. El fin físico de una tarea nueva
se calcula al cerrar Runs y acumular las unidades buenas objetivo; las tareas
históricas legacy conservan `finish`. Los estados posibles se relacionan así:

```text
queued → in_progress → physically_completed
              ↓ ↑
            paused

queued | in_progress | paused → cancelled
```

`physically_completed` sólo indica fin de ejecución física; no equivale al
cierre final del pedido o proyecto. `started_at` conserva el
primer inicio y `paused_at` la última pausa; sin historial de pausas no debe
inferirse tiempo activo restando timestamps.

## Edición y máquinas

En `queued` se edita la planificación completa. En `paused` la cantidad queda
congelada. Durante `in_progress` sólo cambian notas y parámetros técnicos. Los
estados terminales son inmutables.

Una máquina asignada debe estar activa. Sólo puede tener un Run abierto o una
tarea legacy en progreso, con validación cruzada y bloqueos. Cerrar el Run libera
la máquina; una tarea entre intentos no ocupa ese recurso. Pausar o cancelar una
tarea en modo runs requiere cerrar antes su intento abierto. En legacy, pausar
libera el recurso y reanudar vuelve a competir por él.

El código usa `T-AAAA-NNNNNN` y `production_task_code_seq`. Las transiciones de tarea no
recalculan costos ni cambian el origen. Los efectos de inventario se gestionan
por los contratos de intentos, consumos y reservas.

## API

La API expone:

```text
POST  /api/v1/orders/{order_id}/production-tasks
POST  /api/v1/project-components/{component_id}/production-tasks
GET   /api/v1/production-tasks
GET   /api/v1/production-tasks/{task_id}
PATCH /api/v1/production-tasks/{task_id}
POST  /api/v1/production-tasks/{task_id}/start
POST  /api/v1/production-tasks/{task_id}/pause
POST  /api/v1/production-tasks/{task_id}/resume
POST  /api/v1/production-tasks/{task_id}/finish
POST  /api/v1/production-tasks/{task_id}/cancel
POST  /api/v1/production-tasks/{task_id}/dependencies
GET   /api/v1/production-tasks/{task_id}/dependencies
DELETE /api/v1/production-tasks/{task_id}/dependencies/{prerequisite_id}
```

El listado acepta `status`, `priority`, `machine_id`, `order_id`,
`project_component_id` y `project_id`. Se ordena por prioridad (`urgent`,
`high`, `normal`, `low`), posición de cola, antigüedad e identificador.

`PATCH` distingue campos omitidos de valores `null` explícitos y delega la
matriz de edición al servicio. Nunca acepta estado, código, origen ni
timestamps. No existe `DELETE` de tareas. `finish` sólo opera en legacy y produce
`physically_completed`; en modo runs se usa el cierre de ejecuciones.

Los recursos inexistentes responden 404; un origen cancelado, una máquina
inactiva u ocupada y una transición o edición inválida responden 409. Los
payloads inválidos responden 422.

## Dependencias

`task_id depends_on depends_on_task_id` expresa que la segunda tarea es un
prerrequisito directo de la primera. Las dependencias forman un DAG: no se
admiten auto-dependencias, duplicados ni ciclos directos o indirectos.

Sólo se conectan tareas del mismo `Order` o del mismo `Project`. En un proyecto
pueden relacionarse tareas de componentes diferentes. El proyecto se resuelve
desde `ProjectComponent`; no se duplica `project_id` en la tarea.

El grafo de una tarea sólo puede modificarse mientras permanece `queued`. No
se admite agregar un prerrequisito ya cancelado. Si se cancela después, la
relación se conserva y bloquea el inicio de la dependiente.

`start` exige que todos los prerrequisitos directos estén
`physically_completed`. `resume` no vuelve a comprobarlos porque la tarea ya
ingresó al proceso; mantiene las validaciones de máquina. Finalizar un
prerrequisito no inicia automáticamente sus dependientes: no existe scheduler.

El `DELETE` documentado elimina únicamente la relación de planificación, nunca
una `ProductionTask`.
