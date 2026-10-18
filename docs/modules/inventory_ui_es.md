# Interfaz de compras e inventario

## Rutas y accesos

- `/inventory`: catálogo de insumos, filtro por actividad/categoría y selector de
  producto/variante para stock. Sin sumas de existencias ni costos en navegador.
- `/inventory/supplies/new`: alta de insumo; listado actual para revisar un alta
  cuya respuesta se perdió.
- `/inventory/supplies/{id}`: stock físico/reservado/disponible, costo de última
  compra, edición/activación, presentaciones, compras, ajustes e historial.
- `/inventory/variants/{id}`: stock físico/asignado/disponible y movimientos de
  una variante. Se abre también desde «Ver stock» en Producto.
- `/inventory/reservations/{task_id}`: acceso desde tarea. Reserva absoluta en
  unidad base; cero libera, no consume. Lista las reservas actuales de la tarea.
- `/inventory/allocations`: historial de asignaciones. Desde pedido o componente
  se abre con `?order={id}` o `?project={id}&component={id}`, habilitando alta
  contextual cuando el destino existe y está pendiente.
- `/inventory/allocations/{id}`: cantidad inicial y pendiente, stock actual,
  entregas registradas y acciones explícitas de entrega/liberación. Se abre
  también desde un plan con asignación de salida.

## Compras, ajustes y costo

Comprar sin presentación expresa cantidad en unidad base. Con presentación,
expresa número de presentaciones; el servidor convierte el contenido y guarda
cantidad base. El costo total ingresado corresponde a toda la compra, no a una
presentación. Cantidades, importes y precios de referencia se mantienen como
texto; no se multiplican ni dividen en frontend. Precio/moneda de presentación
son opcionales y no se copian como costo real de compra.

Un ajuste declara dirección, cantidad positiva en unidad base, motivo y fecha.
No acredita costo de compra. El historial identifica movimientos originados en
compras y consumos. No se edita ni elimina historia; los ajustes son movimientos
nuevos. La API valida existencia y bloqueo de unidad base por movimientos,
recetas o reservas. La edición envía sólo campos modificados.

El costo estimado es el de última compra informado por API. Ausencia se muestra
como desconocido, nunca cero. Un error de lectura se muestra como error. No es
valoración FIFO del stock; la simulación FIFO sigue en pricing preview. No se
suman monedas. Fechas locales se convierten a ISO con zona horaria al enviar;
la consulta muestra la zona local del navegador.

## Escrituras y respuestas perdidas

Compras, ajustes, altas/presentaciones y edición no se reenvían automáticamente.
Antes de enviar se conserva un aviso con resumen y fecha en sessionStorage. Ante
red/timeout/5xx se bloquea una nueva escritura del mismo formulario, se consultan
los registros y se exige revisión explícita para habilitar otra operación. Tras
recargar el aviso permanece; es necesario consultar registros actuales antes de
reconocerlo. No se infiere que dos compras iguales sean el mismo registro.

HTTP definitivo 4xx (excepto timeout) permite corregir entradas. Un aviso ilegible
no se descarta silenciosamente. Al bloquearse el almacenamiento se informa que
el aviso sólo se conserva en memoria mientras siga abierta la pestaña. No existe
garantía de deduplicación de compras entre pestañas o después de borrar avisos.
La UI no promete idempotencia que esos endpoints no ofrecen.

Movimientos de variantes, asignaciones y entregas sí usan request_id y cuerpo
persistidos con namespace inventory. Reintentar tras recarga conserva ambos y
recupera la operación. Liberar asignación es idempotente por ID; el UUID local del
sobre de recuperación no se envía a ese endpoint. Mientras una entrega/liberación
está pendiente se bloquea la otra acción para evitar cruces desde esta pantalla.

Reservas usan PUT absoluto: se relee ante respuesta incierta y no se reenvía sin
revisión, para no pisar cambios concurrentes de la cantidad reservada.

## Efectos y límites

Asignar compromete cantidad al destino, sin fabricar ni entregar. Entregar
registra salida física y reduce pendiente, sin cerrar el estado comercial.
Liberar pone pendiente a cero, sin devolver entregas ni borrar historia. La UI
muestra existencia física y faltantes del servidor; no añade reglas propias para
bloquear operaciones que la API permite. Pendiente cero no se rotula como
«entregado»: también puede resultar de una liberación.

Las listas paginadas de movimientos/asignaciones recorren todas las páginas.
Insumos, presentaciones, compras y ledger de insumos usan sus listados existentes
sin paginación aparente. Las reservas sólo se enumeran por tarea: no hay endpoint
global inverso por insumo. Consumos detallados se siguen consultando desde los
intentos de producción/Test Print. No hay almacenes, proveedores ni edición de
presentaciones o movimientos históricos en los contratos actuales.

Sin cambios de backend, migraciones, OpenAPI ni dependencias.
