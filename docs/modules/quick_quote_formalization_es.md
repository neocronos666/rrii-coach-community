# Formalización de Quick Quote

10B.8 crea **un único Quote formal por borrador**, vinculado a una revisión
explícitamente elegida. No hace falta que sea la última revisión. No reevalúa
recetas, compras, recursos ni tarifas actuales.

## API

- `POST /api/v1/quick-quotes/{id}/formalize`: crea cálculo técnico, Quote y vínculo
  en una transacción; devuelve 201 con el vínculo.
- `GET /api/v1/quick-quotes/{id}/formalization`: consulta el vínculo o devuelve 404.

La entrada requiere `request_id` y `source_revision`. Admite `title`, `valid_until`,
`adjustments` y `final_price`, siguiendo las reglas comerciales de Quote. Sin título
explícito toma el título guardado. Notas y descripción del item provienen del
borrador. Markup se toma de la revisión; no se sustituye por settings actuales.

La respuesta incluye `quick_quote_id`, `source_revision_id`, `source_revision`,
`quote_id`, `cost_calculation_id`, `request_id` y `created_at` UTC del vínculo.
No devuelve una copia mutable del Quote: se consulta mediante su ruta existente.
`QuoteRead` expone `source_quick_quote_id` y `source_quick_quote_revision`; son
nulos para los presupuestos ordinarios. Así se puede consultar directamente la
revisión histórica que originó el presupuesto.

## Condiciones y efectos

La revisión debe tener costo completo, exactamente una moneda y markup definido.
Cero explícito de markup es válido. Faltantes o multimoneda producen 422 y no
persisten resultados parciales. Los importes deben caber en la precisión comercial.

Se crea un Quote sujeto a las reglas existentes de vigencia: normalmente draft;
una vigencia ya vencida puede producir expired. Seña y demás datos comerciales se
congelan al formalizar. Aprobar y convertir a Order/Project siguen siendo acciones
separadas. No se crean reservas, consumos, planes ni producción.

La revisión puede formalizarse aunque el catálogo actual esté inactivo: su costo
y configuración ya están guardados. La operación no representa disponibilidad
física garantizada ni una asignación FIFO.

## Cantidad física y costo total exacto

Los cálculos ordinarios conservan la interpretación unitaria. El puente crea un
`CostCalculation` de tipo `recipe_demand`, con `demand_quantity` y `demand_unit`,
copiando fuentes, costos unitarios y subtotales de la evaluación. `calculated_at`
corresponde a la revisión evaluada; `created_at` indica cuándo se persistió este
nuevo cálculo. Las cantidades de líneas usan la precisión de almacenamiento
existente (seis decimales); la revisión conserva el desglose original completo.

QuoteItem conserva la cantidad física de la demanda y su total exacto. El costo
unitario es un promedio informativo redondeado a cuatro decimales y **no reconstruye
el total**. Para costo 1 y cantidad 3 se guardan total 1, cantidad 3 y unitario 0,3333.
Order conserva esos mismos cantidad y total cuando posteriormente se aprueba y
convierte el Quote. Los rendimientos de lote no se escalan nuevamente.

El cálculo de demanda sólo se utiliza mediante su puente. Las rutas generales de
Quote no permiten reutilizarlo para crear otra oferta o aplicar otra cantidad.
Los cálculos ordinarios y su multiplicación por cantidad mantienen su comportamiento.

## Edición y concurrencia

El Quote draft admite cambios comerciales: título, descripción general, notas,
vigencia, markup, ajustes y precio final. Sus items técnicos quedan fijados; no
se puede reemplazar costo, cantidad, descripción o notas del item. Reenviar los
mismos items es válido. Los cambios de condiciones comerciales conservan el total técnico.
Otra demanda requiere otra evaluación y otro borrador para una nueva formalización.
Recalcular el Quick Quote original no actualiza el Quote ya creado.

Las operaciones de edición, aprobación y rechazo bloquean y refrescan el Quote
antes de validar su estado. Un estado draft guardado en una sesión vieja no
habilita editar un presupuesto aprobado posteriormente.

El puente bloquea el borrador y usa unicidad en PostgreSQL. Repetir el mismo
request_id, destino y payload devuelve el vínculo original (201), incluso tras
editar o aprobar el Quote. Reutilizar el ID con otra petición da 409. Un nuevo
request_id para un borrador ya formalizado también da 409: consultar su vínculo.
Los IDs de formalización son únicos dentro de este conjunto de operaciones.

Cálculo, Quote y vínculo se confirman juntos. Cualquier error los revierte juntos.
Los huecos de numeración por transacciones fallidas no se reutilizan.

## Migración y límites

0037 agrega la base de demanda nullable en CostCalculation y la tabla de vínculos
con FK y restricciones únicas. Los cálculos anteriores conservan ambos campos
nulos, sin reinterpretación de historia. El downgrade rechaza eliminar vínculos o
cálculos de demanda existentes.

No se implementa sincronización automática de revisiones con Quote, agrupación
de varios Quick Quotes en un presupuesto, impuestos ni UI nueva.
Desde 10B.9 el total final ARS aplica el [redondeo comercial al peso inferior](commercial_rounding_es.md);
la evaluación histórica de Quick Quote y el costo de demanda no cambian.
El flujo formalizado actual contiene un item y, al convertirlo, origina Order;
la conversión ordinaria de Quotes con varios items a Project se conserva.
