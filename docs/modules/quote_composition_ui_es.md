# Composición comercial independiente

Desde Presupuestos: `/quotes/new` crea un borrador con uno o varios ítems técnicos;
`/quote-items/{id}` reemplaza la composición de un draft ordinario. Los presupuestos
formalizados desde Quick Quote y los estados no editables no ofrecen esta operación.

`/calculations/new` registra un snapshot de costos con máquina, energía, insumos,
trabajo y extras. `/calculations/{id}` lo consulta sin recalcular. El identificador
se copia al selector de ítems; no hay listado de cálculos en la API. El selector
muestra líneas, faltantes, moneda, demanda y totales guardados antes de agregar.
Los cálculos incompletos o multimoneda no se pueden seleccionar. El backend valida
la moneda conjunta y las cantidades al guardar. Una cantidad comercial multiplica
el costo del cálculo completo; no se confunde con cantidad de demanda informativa.

Se conserva precisión textual. No se calculan importes, se consumen existencias
ni se crean destinos desde este editor. El detalle existente permite ajustar las
condiciones económicas, aprobar y convertir de forma separada.

Escrituras inciertas no se reenvían. Para Quote, el listado permite revisar el
resultado y habilitar explícitamente otra operación. Para cálculos, la API no
ofrece listado ni idempotencia: una respuesta perdida queda bloqueada en esa
pestaña y requiere comprobar el resultado por fuera del flujo. No se promete
recuperar un identificador que el servidor no devolvió. No hay detección ETag de
ediciones simultáneas. Consultar registros conserva el borrador local.
