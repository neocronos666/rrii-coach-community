# Reservas de insumos

Una reserva pertenece a una ProductionTask y a un Supply existentes. Su cantidad
pendiente se expresa en la unidad base del insumo; cero libera la reserva. No
produce movimientos de stock. La falta de stock se informa y no bloquea.

Disponibilidad = suma del ledger físico menos reservas pendientes. Una reserva
mayor que el stock físico es válida. El backend devuelve la advertencia y el
saldo proyectado. La API no acepta conversiones implícitas de unidades.

Las tareas cerradas, canceladas o de origen cancelado no aceptan nuevas reservas.
Cancelar una tarea, pedido o proyecto libera las reservas correspondientes en la
misma transacción. La producción parcial reducirá la reserva por el consumo real
en 9D.2; completar la Task liberará el remanente.

La unidad base de un Supply referenciado por recetas o reservas no puede cambiar,
además de la restricción existente para insumos con movimientos. Las operaciones
que afectan disponibilidad se serializan sobre el insumo; las operaciones de una
misma tarea también se serializan sobre ella.
