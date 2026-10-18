# ADR-0036: Puente único y costo de demanda

## Estado

Aceptada el 29 de septiembre de 2026. El usuario confirmó un único Quote formal
por borrador de Quick Quote, vinculado a la revisión elegida.

## Decisión

Crear explícitamente un cálculo de demanda, Quote y vínculo de origen en una
transacción. Preservar el snapshot seleccionado sin consultar precios actuales.
Sólo formalizar revisiones completas, monomoneda y con markup definido.

Distinguir cálculos unitarios existentes de `recipe_demand`. Conservar cantidad
física y total exacto como datos autoritativos; el promedio unitario redondeado no
se utiliza para reconstruir el total. Las modificaciones de condiciones comerciales del Quote no
pueden reemplazar o escalar sus items técnicos.

## Consecuencias

Evita doble multiplicación y diferencias de redondeo; Order conserva cantidad y
total. No se crea una cantidad ficticia de un lote. Nuevas demandas requieren otra
evaluación y otro borrador para formalizar otra oferta. Los reintentos devuelven
el vínculo original; distintas formalizaciones del mismo borrador se rechazan.

Quote aprobado conserva inmutabilidad; edición y aprobación se serializan bajo
bloqueo y refresco. No se crea producción ni se consume/reserva stock al formalizar.

Contrato: [formalización](../modules/quick_quote_formalization_es.md).
