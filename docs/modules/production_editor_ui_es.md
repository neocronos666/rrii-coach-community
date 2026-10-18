# Producción avanzada y ejecuciones

16/10/2026. Desde cada pedido/componente: `/production/tasks/new?order={id}` o
`?project={id}&component={id}`. La UI valida el origen leído antes de presentar
el formulario; la API mantiene pertenencia y estado. Cada tarea nace manual,
con ejecuciones; no se crean tareas huérfanas ni se recalculan costos del pedido.

`/task-edit/{id}` edita título, descripción, prioridad, cola, máquina, cantidad,
notas y parámetros técnicos JSON. PATCH envía diferencias y admite limpieza null.
En curso sólo notas/parámetros; pausada no cambia cantidad. Cantidades de receta
y tareas cerradas quedan protegidas. Los borradores sobreviven a consultas.
Los parámetros técnicos no deben contener secretos.

Dependencias: selección entre tareas del pedido o del proyecto completo, incluidas
las de otro componente. El backend valida ciclos, estado y pertenencia. Retirar
una dependencia requiere confirmación y nunca borra una tarea. Las dependencias
de recetas son inmutables. Alta/PATCH/dependencias sin reenvío ante respuesta
incierta; consulta y revisión explícitas antes de habilitar otra operación.

Las tareas manuales muestran intentos, progreso y cierre usando la misma API de
Runs. La variante de salida es opcional y exige su unidad base; las unidades buenas
se incorporan al stock según el servidor. Se pueden agregar consumos de insumos y
componentes desde catálogos, en unidad base y con cantidad real textual. No se
copian estimaciones como consumo. La lista visual inicial vacía de una tarea manual
no se persiste como receta ni modifica su origen.

Producción y Test Print comparten opciones de ejecución: fecha/hora de inicio o fin
opcional (zona del navegador convertida a UTC), override explícito de parámetros y
consumos adicionales. Vacío conserva hora del servidor y parámetros heredados.
El backend valida cronología, solapamientos, recursos y consumos obligatorios.
La identidad y payload de reintentos pendientes se conservan sin reinterpretarlos.
Parámetros guardados del intento se consultan incluso después del cierre.

Tareas históricas legacy muestran start/pause/resume/finish/cancel según estado;
finish confirma fin físico, no cierre comercial. La API sigue validando todas las
transiciones. No hay DELETE de tareas ni edición del estado mediante PATCH.
