# Pruebas de receta completa

Test print prueba una variante mediante su receta completa, con todos sus pasos
activos y dependencias. Son decisiones confirmadas por el usuario: no parte de
Assets aislados ni equivale a ejecutar sólo un paso de impresión.

## Creación y snapshot

POST `/api/v1/test-prints` recibe request_id, recipe_id, variant_id,
target_quantity, selections y machine_assignments. Variante y receta son
obligatorias. Se admiten receta base y recetas heredadas de esa variante; las
heredadas no aceptan selecciones. La cantidad objetivo conserva las reglas de
producción: Decimal positivo y entero si la unidad final es unit.

La creación usa la resolución compartida de recetas dentro de REPEATABLE READ.
Conserva configuración, pasos aplicables, omisiones, cantidades planificadas,
recursos físicos, materiales, unidades de insumos, parámetros y frases resueltas.
Las revisiones usadas quedan protegidas también por FK, no sólo por JSON.
El snapshot y los pasos no se editan cuando cambia la receta o el catálogo.

Crear no genera Order, Project, ProductionTask ni ProductionPlan comercial.
Tampoco reserva stock, consume materiales o asigna producto a un pedido.
Repetir request_id con la misma petición recupera la prueba original antes de
consultar el catálogo actual; otro contenido devuelve 409. Conflictos de
serialización/deadlock o colisión de creación se reintentan hasta tres veces.

## Pasos e intentos reales

TestPrint tiene estados open, completed y cancelled. Sus TestPrintSteps son los
objetivos del DAG resuelto. ProductionTask mantiene exactamente su origen
Order XOR ProjectComponent: los pasos experimentales no son tareas comerciales.

ProductionRun identifica ahora exactamente uno de estos orígenes:

- task_id, para producción comercial existente;
- test_print_step_id, para un paso experimental.

Ambos usan la misma exclusividad de máquina, índice de Run abierto y registros de
consumo. Los Runs antiguos conservan task_id y test_print_step_id null. Los nuevos
Runs experimentales exponen task_id null; los clientes deben usar el origen
correspondiente. No se inventan Runs ni se reinterpretan datos anteriores.

POST `/test-prints/{id}/steps/{key}/runs` recibe el contrato RunCreate existente.
Debe haberse alcanzado la cantidad objetivo de cada prerrequisito y no quedar
intentos abiertos de esos pasos. No se inician pasos automáticamente. La máquina
real se elige en el intento o toma la asignación fijada al crear la prueba.
Print requiere impresora FDM/SLA compatible; service y wait no asignan máquina.
La misma máquina no puede ejecutar otra prueba, Run normal o tarea legacy activa.

El cierre se realiza con POST `/production-runs/{run_id}/close`. Conserva buenas,
fallidas, motivo, duración Decimal y tiempos UTC. Las cantidades reales siguen
el contrato Decimal de RunClose. Se admiten intentos fallidos y tandas parciales.
Un paso puede repetirse mientras la prueba siga abierta, por ejemplo para reponer
componentes desperdiciados al ensamblar. Se conserva cada intento y su consumo.

La prueba pasa a completed sólo cuando **todos** los pasos activos alcanzan sus
objetivos y no hay Runs abiertos. Una impresión terminada no omite servicios,
esperas o ensamblado. Wait sigue siendo un paso confirmado por el operador, sin
temporizador ni duración obligatoria. Cancelar exige estado open y ningún intento
abierto; no borra resultados, revierte consumos ni habilita promoción.

## Consumos e inventario experimental

Cerrar registra resultado y consumos en una sola transacción. Con unidades buenas
se exige declarar todos los insumos y componentes obligatorios del snapshot.
Las cantidades reales son explícitas, no se infieren de los valores estimados.
consumed incluye wasted: consumed=100, wasted=15 genera una salida de 100.
Un cierre idéntico es idempotente; un resultado diferente devuelve 409.

Insumos y componentes externos descuentan el ledger comercial existente una vez;
los faltantes producen advertencias como en producción normal. Un cambio de unidad
del insumo respecto del snapshot se rechaza, sin reinterpretar la cantidad guardada.
No se modifican reservas comerciales para cubrir una prueba.

Los componentes con source_step_key se obtienen de la producción interna de esa
misma prueba. Disponibilidad interna = buenas producidas por el paso proveedor
menos sus consumos internos registrados, incluido desperdicio. El servicio bloquea
la prueba para impedir sobreconsumo concurrente. No se usa el excedente de otra
prueba ni se sustituye silenciosamente por stock comercial.

Se conserva ProductionRunProductConsumption con internal_source_step_id para esos
consumos internos; **no** se genera una salida del ledger comercial. Los componentes
externos tienen ese campo null y su movimiento de consumo habitual. Así no hay
entradas/salidas ficticias de stock para las piezas intermedias experimentales.

Cerrar un Run experimental nunca ingresa productos al stock comercial. Esto también
aplica a la salida final y los excedentes; el comportamiento de Runs normales
continúa ingresando su salida automáticamente.

## Promoción explícita

POST `/test-prints/{id}/promote` recibe request_id y quantity. El destino es siempre
la variante fijada al crear la prueba: no se recibe otra variante. Requiere estado
completed, variante activa, unidad compatible y cantidad positiva que no supere
las buenas finales disponibles después de consumos internos, si los hubiera.

Este incremento admite **una promoción por prueba** a esa única variante, por
todas o parte de las unidades elegibles. Promover parte no habilita otra promoción
posterior del resto. El índice único y el bloqueo de la prueba impiden duplicar la
entrada. Repetir la petición devuelve el mismo movimiento; cambiarla devuelve 409.
La lectura expone promotable_quantity y promotion_movement_id.

Se crea ProductStockMovement de tipo test_print con test_print_id y request_id.
La promoción no consume insumos, no crea un Run y no vuelve a fabricar las piezas.
No reparte stock entre variantes ni asigna entregas comerciales. Resultados
fallidos, pruebas abiertas o canceladas no se promueven.

## Consulta y límites

- GET `/test-prints`: paginación offset/limit (máximo 100) y filtro variant_id.
- GET `/test-prints/{id}`: snapshot, pasos, progreso y promoción.
- GET `/test-prints/{id}/steps/{key}/runs`: intentos paginados.
- GET `/production-runs/{id}` y rutas existentes de consumos: historia de cada intento.
- POST `/test-prints/{id}/cancel`: cancelación sin borrado.

No hay DELETE, edición retrospectiva, autenticación, control físico de impresoras,
workers ni pricing/FIFO. La interfaz incorporada en 10B.9 se describe en
[Test print UI](test_print_ui_es.md). No se trasladan automáticamente piezas
internas sobrantes a otra prueba o al stock. Cualquier corrección futura de hechos
requiere operaciones explícitas, no reescribir el resultado original.

## Persistencia y validación

Migración incremental `20260926_0034` desde 0033: TestPrint, TestPrintStep,
referencias a revisiones; origen XOR de Run; origen de consumo interno y promoción
en el ledger. Downgrade protegido si existe cualquier prueba. La ida/vuelta vacía
conserva los Runs y movimientos comerciales anteriores.

Pruebas en `test_hito10b_test_print.py` y `test_hito10b_test_print_safety.py`:
DAG completo, omisión, recursos/materiales resueltos, historia, rollback,
consumo único, reposición interna, exclusividad cruzada, concurrencia,
promoción parcial/idempotente y migración. Los resultados efectivos corresponden
a cada ejecución; ver [calidad](../development/quality_es.md).
