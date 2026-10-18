# Motor de costos técnicos

## Alcance

El módulo calcula el costo técnico de ejecutar un trabajo maker. No determina
margen, ganancia, impuestos, recargos ni precio de venta. La capa comercial
futura consumirá este resultado sin modificar su significado.

## Arquitectura

Las fuentes se resuelven antes de la aritmética. `SupplyCostProvider` desacopla
el origen del costo unitario; Community utiliza
`LastPurchaseSupplyCostProvider`. `TechnicalCostCalculator` recibe valores
normalizados y no depende de FastAPI, SQLAlchemy ni PostgreSQL.

Cada resultado se persiste como un `CostCalculation` inmutable con líneas
`CostCalculationLine`. Se congelan cantidad, unidad, costo unitario, moneda,
subtotal, fuente y referencia. Consultar un cálculo histórico nunca vuelve a
resolver precios actuales. Recalcular creará en el futuro otro snapshot.

## Componentes

- Supplies: se convierten a su unidad base y usan la última compra válida.
- Mano de obra: minutos enteros se convierten a horas `Decimal` y aplican la
  tarifa tipada de la instalación.
- Máquina: depreciación técnica básica `purchase_price / useful_life_hours`.
- Energía: prioriza `energy_kwh` manual; en su ausencia estima con potencia
  nominal por duración. No representa una medición real.
- Extras: líneas manuales explícitas con importe y moneda.

Calcular no consume ni reserva stock. Una necesidad superior a la existencia
genera una advertencia pero permite obtener el costo.

## Resultados incompletos y monedas

Una fuente o tarifa faltante produce una línea incompleta con subtotal nulo,
nunca costo cero. `complete` y `multi_currency` son indicadores independientes:
un resultado puede ser simultáneamente incompleto y multimoneda. Los totales se
agrupan por moneda y no se convierten.

## Precisión

Toda aritmética usa `Decimal`. Las duraciones se intercambian como minutos
enteros y se calculan como horas decimales. El costo unitario se congela con
ocho decimales y el subtotal con cuatro, usando `ROUND_HALF_UP` al crear el
snapshot. No se asume que una moneda posea dos decimales.

## API

- `POST /api/v1/cost-calculations`: resuelve, calcula y persiste (`201`).
- `GET /api/v1/cost-calculations/{id}`: devuelve el snapshot (`200`).

No existen listado, PATCH, PUT, DELETE ni recalculación.

El módulo de presupuestos solo admite cálculos completos y monomoneda. Copia el
total como snapshot comercial y nunca modifica ni recalcula el costo técnico.

## Vista previa de recetas

10B.6 agrega [pricing preview](pricing_preview_es.md), de sólo lectura, con FIFO
simulado o última compra. El endpoint persistente descrito aquí conserva su
proveedor e inmutabilidad. Véase ADR-0034 para la ampliación de alcance.

## Cálculo de demanda formalizado

10B.8 agrega `recipe_demand`, con cantidad y unidad de demanda explícitas, desde
una revisión de Quick Quote. Su total corresponde a esa demanda y no a una unidad.
Los cálculos `technical` existentes conservan la semántica anterior. Véase el
[puente a Quote](quick_quote_formalization_es.md).
