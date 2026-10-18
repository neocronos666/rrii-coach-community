# Relaciones y persistencia del dominio

## Convenciones

Los modelos usan SQLAlchemy 2.x tipado, identificadores UUID y timestamps con
zona horaria. Dinero y cantidades persistentes utilizan `Decimal` y `NUMERIC`.
Las migraciones históricas de Alembic son la fuente del esquema instalado.

## Presupuesto y destino operativo

`QuoteItem` conserva el snapshot del costo técnico referenciado. Aprobar un Quote
no crea un destino ni inicia producción. La conversión explícita crea un `Order`
para un ítem o un `Project` con `ProjectComponent` para varios. `QuoteConversion`
preserva el vínculo único. Los destinos no recalculan históricos al consultarse.

## Catálogo y recetas

`Product` agrupa variantes. `ProductVariant` tiene unidad base y atributos;
las opciones configurables se asocian al producto y a valores permitidos.
`Recipe` define pasos, dependencias, inputs y recursos. Los servicios reutilizables
se modelan mediante `ServiceDefinition`. Ver [recetas](../modules/recipes_es.md).

## Assets

`Asset` tiene categoría, familia opcional, atribución y una revisión actual.
`AssetRevision` conserva revisiones numeradas; restaurar crea otra revisión.
`AssetRevisionFile` relaciona la revisión con `StoredFile` y su rol. Los bytes se
guardan localmente por contenido, separados de sus metadatos en PostgreSQL.
Composición y compatibilidad se documentan en
[estructura](../modules/asset_structure_ui_es.md).

## Producción y stock

`ProductionTask` pertenece a un pedido o a un componente de proyecto, nunca a
ambos. Sus dependencias forman un DAG. `ProductionRun` pertenece a una tarea
comercial o a un `TestPrintStep`. Los consumos y la salida de stock se registran
junto con el cierre del intento, de acuerdo con el origen y las opciones explícitas.
Una promoción de Test Print a stock es otra acción explícita.

Los stocks físicos se derivan de movimientos. Reservas de insumos y asignaciones
de productos conservan sus propios vínculos; no son depósitos ni lotes seriales.
