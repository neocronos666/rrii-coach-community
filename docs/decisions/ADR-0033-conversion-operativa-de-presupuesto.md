# ADR-0033: conversión operativa explícita de presupuestos

## Estado

Aceptada.

## Contexto

La aprobación congela el acuerdo comercial, pero no debe iniciar trabajo ni
alterar existencias. Se necesita proyectar ese acuerdo a una unidad operativa
sin perder trazabilidad ni recalcular valores históricos.

## Decisión

La conversión es una acción explícita posterior a la aprobación. Un `Quote`
con un item crea un `Order`; con dos o más crea un `Project` y un
`ProjectComponent` por item. El cliente no elige el tipo.

`QuoteConversion` registra un único destino por presupuesto. La fila del Quote
se bloquea durante la transacción y restricciones únicas refuerzan la
idempotencia. Order y Project solo nacen por esta conversión y copian snapshots
desde Quote y QuoteItem.

## Consecuencias

- Aprobar no convierte automáticamente.
- Repetir la conversión devuelve el mismo destino.
- No se recalculan costos ni se distribuyen ajustes globales por componente.
- Convertir no consume o reserva stock, ni crea producción o facturación.
- Los estados iniciales se limitan a `pending` y `cancelled`.
