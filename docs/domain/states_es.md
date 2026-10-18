# Estados implementados

Las transiciones se validan en servicios. Este resumen no define estados futuros.

| Entidad | Estados actuales |
| --- | --- |
| Quote | `draft`, `approved`, `rejected`, `expired` |
| Order / Project | `pending`, `cancelled` |
| ProductionTask | `queued`, `in_progress`, `paused`, `physically_completed`, `cancelled` |
| ProductionRun | `running`, `closed` |
| TestPrint | `open`, `completed`, `cancelled` |

Un presupuesto sólo se edita en draft. La expiración se materializa al consultar
u operar sobre un borrador vencido, sin scheduler. La conversión se registra
aparte: no es un estado nuevo del presupuesto aprobado.

Las tareas nuevas alcanzan `physically_completed` mediante buenas acumuladas de
Runs cerrados. Las tareas históricas legacy mantienen `finish`; no se inventan
Runs para migrar su historia. El cierre físico no cambia el estado de Order o
Project. Las condiciones exactas están en [producción](../modules/production_es.md)
y [ejecuciones](../modules/production_runs_es.md).

Asset utiliza `archived` y una referencia a su revisión actual. Las revisiones se
numeran y se conservan, sin un ciclo de estados separado.
Quick Quote conserva revisiones numeradas y un vínculo de formalización, sin
reutilizar el ciclo de estados de Quote.

No hay estados de cobro, facturas externas ni encuestas de evaluación.
