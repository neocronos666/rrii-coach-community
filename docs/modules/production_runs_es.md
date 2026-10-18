# Ejecución real

Desde 10B.5, ProductionRun también admite origen exclusivo TestPrintStep. Task
mantiene su contrato comercial; la ejecución experimental y sus diferencias de
stock se describen en [test print](test_prints_es.md). En RunRead, task_id puede
ser null únicamente cuando test_print_step_id identifica el paso experimental.

ProductionTask es el objetivo; ProductionRun es un intento físico con máquina,
parámetros y tiempos propios. Un Run abierto por Task y por Machine; las tareas
manuales pueden ejecutarse sin máquina. Una tarea en progreso entre tandas no
ocupa máquina. Los Runs cerrados aportan cantidades buenas y fallidas; el motivo
de fallo puede coexistir con buenas. No se inventan ejecuciones históricas.

Las tareas anteriores a la migración conservan temporalmente el modo legacy,
su finish manual y la exclusividad histórica. Las nuevas usan runs y no pueden
completarse sin alcanzar la cantidad objetivo mediante Runs cerrados. El modo
es una transición de datos, no una edición ni un feature flag. No se acepta
por API de creación/PATCH. La máquina sugerida de Task no cambia la máquina
real ya registrada en un Run.

Iniciar el primer Run valida el DAG y activa la Task si estaba queued. Una Task
paused no admite Runs nuevos. Pausar o cancelar requiere cerrar primero el Run
abierto. Cerrar un Run libera la máquina y completa físicamente la Task sólo si
las buenas acumuladas alcanzan el objetivo. Nunca cierra Order/Project.

Cerrar dos veces el mismo Run con el mismo resultado devuelve el registro;
otro resultado produce conflicto. No hay edición ni borrado de resultados
cerrados. Correcciones productivas y compensaciones de inventario necesitarán
operaciones explícitas; no se reescriben silenciosamente hechos históricos.

La adaptación debe preservar tareas Hito 8 sin Runs ficticios y validar
exclusividad cruzada entre tareas legacy y Runs con bloqueos de máquina.
