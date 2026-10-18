# Quick Quote: borradores independientes

El módulo permite guardar y retomar una cotización rápida para una receta y variante.
Cada operación explícita conserva una revisión inmutable con entrada y evaluación.
No crea un Quote formal, no consume su numeración ni genera efectos operativos.
La [formalización explícita](quick_quote_formalization_es.md) es una acción separada.

## API

| Método y ruta bajo `/api/v1` | Resultado |
| --- | --- |
| POST `/quick-quotes` | Crea borrador y revisión 1; 201 |
| GET `/quick-quotes` | Última revisión de cada borrador |
| GET `/quick-quotes/{id}` | Última revisión guardada |
| PUT `/quick-quotes/{id}` | Reemplaza entrada completa, evalúa y agrega revisión |
| POST `/quick-quotes/{id}/recalculate` | Reevalúa la entrada guardada con fuentes actuales |
| GET `/quick-quotes/{id}/revisions` | Historial, más reciente primero |
| GET `/quick-quotes/{id}/revisions/{revision}` | Revisión histórica específica |

Listados paginados con `limit` entre 1 y 100 (default 50) y `offset` no negativo.
Los borradores se ordenan por creación descendente e ID, no por última edición.
El borrador no usa los estados de Quote y no tiene PATCH ni DELETE.
La formalización explícita se describe en su contrato separado.

## Entrada y revisiones

Crear requiere `request_id`, `title` y `pricing`; `notes` es opcional. `pricing`
usa exactamente la entrada de [pricing preview](pricing_preview_es.md): receta,
variante, cantidad, selecciones, estrategia, estimaciones totales por paso y markup.
Título se recorta y exige entre 1 y 255 caracteres; notas hasta 10000 caracteres.

PUT requiere además `expected_revision`. Es reemplazo completo: no enviar notas
las deja nulas; no enviar selecciones o estimaciones usa sus defaults de contrato.
Esta operación evalúa explícitamente la nueva entrada con las fuentes actuales.
Recalcular sólo recibe `request_id` y `expected_revision`, y reutiliza la entrada
anterior. Si esa entrada omitía selecciones, se aplican los defaults actuales.

Una revisión anterior permanece consultable con el mismo resultado aunque cambien
receta, nombres, opciones, compras o tarifas. Los GET nunca recalculan ni modifican
estado. Un catálogo ahora inactivo puede impedir una evaluación nueva sin impedir
consultar historia o reintentar una operación ya completada.

La respuesta identifica el borrador mediante `id` y la evaluación guardada mediante
`revision`, `request_id`, `operation` y `created_at` UTC de esa revisión. No debe
interpretarse un reintento histórico como si fuera la revisión vigente; GET del
borrador devuelve la última.

## Información conservada

Cada revisión guarda:

- Entrada normalizada: título, notas y petición de pricing.
- Configuración efectiva, incluidos defaults y selecciones resueltas.
- Plan resuelto con recursos, instrucciones y textos de servicios.
- Nombres de producto, variante y receta, y unidad de la variante.
- Cantidades planificadas, omisiones, desglose de costos, monedas, referencias a
  fuentes, advertencias, markup y precio sugerido de la misma instantánea.

Se admite guardar resultados incompletos o multimoneda para retomarlos. No se
inventa costo ni precio final. Markup ausente sigue ausente y cero explícito sigue
siendo cero. El costo técnico guardado corresponde al **total de la demanda**,
no a un costo unitario para multiplicar nuevamente al formalizar.

## Transacciones y concurrencia

`PricingPreviewService.evaluate_in_snapshot` comparte el motor sin confirmar ni
escribir. Quick Quote controla su propia transacción REPEATABLE READ y persiste
borrador y revisión juntos. La ruta pricing-preview conserva READ ONLY y su
respuesta anterior.

`expected_revision` evita sobrescrituras de una edición concurrente. Un conflicto
produce 409 y requiere consultar la versión actual. Cada operación usa un
`request_id` único en Quick Quote: repetir la misma operación, destino y entrada devuelve
la revisión original, incluso si el borrador ya avanzó. Reutilizarlo para otra
operación o entrada produce 409. Los reintentos de creación mantienen 201.

Los bloqueos de borrador, unicidad y reintentos acotados de serialización protegen
operaciones concurrentes. Un error revierte tanto la revisión como el avance del
borrador. No se guarda una revisión fallida ni se modifican las anteriores.

## Persistencia y límites

0036 agrega `quick_quotes` y `quick_quote_revisions`. Las revisiones referencian
receta y variante con FK y conservan snapshots tipados en JSONB. No se almacenan
secretos. La historia no depende de consultar el catálogo vivo. El downgrade se
rechaza si existen borradores, para evitar eliminar historia.

Guardar revisiones no reserva capas FIFO, consume stock ni crea CostCalculation
o Quote formal. La formalización es explícita. La gestión visual está en
[Quick Quote UI](quick_quote_ui_es.md).
