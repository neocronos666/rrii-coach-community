# Dashboard conectado y navegación

16/10/2026. `/` consulta APIs reales y conserva la distribución personalizable de
10A. Se retira la fuente de demostración porque sus métricas ficticias ya no
representan el producto operativo.

- Producción: tareas en cola, en curso o pausadas; orden de la API.
- Presupuestos: borradores, con importe y moneda guardados, sin sumas locales.
- Atención: tareas pausadas y presupuestos vencidos; no presume alertas de stock.
- Actividad: última actualización de tareas y presupuestos ordenada por timestamp;
  no es historial de eventos ni auditoría.
- Máquinas: activas/inactivas; no se infiere disponibilidad operativa.

Cada bloque consulta por separado, muestra carga/error/vacío y permite actualizar.
Si falla una actualización conserva los últimos datos con aviso; no reemplaza un
error por cero registros. La lista muestra hasta ocho registros e informa el límite,
el total corresponde a la respuesta completa. Los resúmenes agrupan estados ya
informados por el servidor, sin fórmulas de negocio. Cada registro abre su detalle.

El launcher Cotizar pedido abre `/quotes/new`; Quick Quote mantiene su ruta.
La búsqueda del shell busca nombres de secciones; no promete buscar registros
remotos. Más → Insumos abre Inventario. `/supplies` redirige a `/inventory` por
compatibilidad y una ruta desconocida muestra 404, sin pantalla «próximamente».

Los estados y reglas de negocio siguen exclusivamente en backend. Sin servicios
externos adicionales, cambios de esquema, autenticación o dependencias nuevas.
