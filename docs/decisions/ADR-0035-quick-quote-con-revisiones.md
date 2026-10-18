# ADR-0035: Quick Quote independiente con revisiones

## Estado

Aceptada el 28 de septiembre de 2026. El usuario confirmó guardar un borrador
independiente para retomarlo; Quote formal y conversión corresponden a 10B.8.

## Decisión

Persistir Quick Quote en un dominio propio, separado de Quote y CostCalculation.
Crear, reemplazar entrada y recalcular agregan revisiones inmutables. Consultar
no reevalúa ni modifica historia. Se admiten evaluaciones incompletas y multimoneda.

Guardar entrada, configuración efectiva, plan resuelto y desglose de costo en
una misma instantánea transaccional. Reutilizar el motor de pricing preview;
la ruta de consulta de preview conserva su transacción de sólo lectura.

Usar request_id único por operación para reintentos y expected_revision para
impedir sobrescrituras concurrentes. Conservar revisiones anteriores y rechazar
un downgrade que eliminaría borradores existentes.

## Consecuencias

Los borradores no consumen numeración comercial ni crean reservas, consumos o
producción. Un resultado guardado puede quedar desactualizado respecto del
catálogo, y sólo una acción explícita lo recalcula en otra revisión.

El costo sigue representando el total de la demanda. 10B.8 deberá resolver su
paso al contrato de costo unitario de QuoteItem sin multiplicarlo nuevamente ni
alterar snapshots. No aplicar autoredondeo comercial sin su fórmula definida.

Contrato: [Quick Quote](../modules/quick_quotes_es.md).
