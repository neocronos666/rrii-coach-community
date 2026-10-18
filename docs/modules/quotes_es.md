# Presupuestos Community

## Alcance

El módulo transforma uno o más cálculos técnicos existentes en una propuesta
comercial. Mantiene separados costo técnico, precio sugerido y precio final. No
crea clientes, pedidos, proyectos, producción, reservas ni facturas.

## Snapshots

Cada `QuoteItem` referencia un `CostCalculation` completo y monomoneda, y copia
su costo unitario, cantidad comercial, total y moneda. Consultar un presupuesto
no vuelve a resolver compras, tarifas ni settings. Los cálculos incompletos o
multimoneda se rechazan en este MVP.

## Precio sugerido

Community usa markup:

```text
subtotal = costo técnico × (1 + markup / 100)
```

Si el request no indica markup se usa el default de instalación; si tampoco
está configurado se congela cero. Todos los ajustes porcentuales se calculan
sobre ese mismo subtotal. Luego se suman recargos fijos y se restan descuentos
fijos. Ningún ajuste puede producir un precio negativo.

El precio final toma inicialmente el sugerido. Un valor manual queda marcado
como override y se conserva durante recálculos del draft. Enviar `null` permite
restablecerlo al sugerido.

## Seña

La política, tipo y valor se copian desde la configuración al crear el
presupuesto. El importe se calcula sobre el precio final. Una seña fija no puede
superarlo; una porcentual se limita a 100 %. Cambios posteriores de settings no
alteran el snapshot.

## Estados y numeración

Los estados son `draft`, `approved`, `rejected` y `expired`. Solo `draft` es
editable. La expiración de un draft vencido se materializa al consultarlo u
operar sobre él; no existe scheduler. Aprobar o rechazar vuelve inmutable el
presupuesto.

PostgreSQL genera un número mediante `quote_code_sequence` y el servicio forma
`Q-AAAA-NNNNNN`. La secuencia es global y no se reinicia por año.

## API

- `POST /api/v1/quotes`
- `GET /api/v1/quotes`
- `GET /api/v1/quotes/{id}`
- `PATCH /api/v1/quotes/{id}` (solo draft)
- `POST /api/v1/quotes/{id}/approve`
- `POST /api/v1/quotes/{id}/reject`

No existen endpoints DELETE ni edición de estados mediante PATCH.

## Origen Quick Quote

El [puente de 10B.8](quick_quote_formalization_es.md) conserva cantidad física y
total técnico de una revisión, sin volver a multiplicar el costo de demanda.
Su costo unitario es informativo y sus items técnicos no se reemplazan desde
QuoteUpdate. Los ajustes comerciales siguen disponibles en draft. La respuesta
expone el borrador y revisión de origen; los Quotes ordinarios mantienen su contrato.
