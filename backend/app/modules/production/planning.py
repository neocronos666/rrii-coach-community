from decimal import ROUND_CEILING, Decimal, localcontext
from uuid import UUID

from app.modules.recipes.exceptions import InvalidRecipeError
from app.modules.recipes.schemas import PlannedStep, PlanRead, RecipePlan

LIMIT = Decimal("999999999999.999999")
QUANTUM = Decimal("0.000001")


def quantity(value: Decimal) -> Decimal:
    if value <= 0 or value > LIMIT:
        raise InvalidRecipeError("La cantidad calculada excede el rango permitido")
    return value.quantize(QUANTUM, rounding=ROUND_CEILING)


def calculate_plan(
    plan: RecipePlan | PlanRead, variant_id: UUID, target: Decimal
) -> list[PlannedStep]:
    finals = [step for step in plan.steps if step.output_variant_id == variant_id]
    if len(finals) != 1 or finals[0].quantity_per_output != 1:
        raise InvalidRecipeError(
            "La receta requiere una sola salida final con quantity_per_output=1"
        )
    by_key = {step.key: step for step in plan.steps}
    ordered: list[str] = []
    pending = set(by_key)
    while pending:
        ready = sorted(
            key for key in pending if set(by_key[key].depends_on) <= set(ordered)
        )
        if not ready:
            raise InvalidRecipeError("La receta no forma un DAG")
        ordered.extend(ready)
        pending.difference_update(ready)
    with localcontext() as context:
        context.prec = 60
        demands = {key: Decimal(0) for key in ordered}
        result: dict[str, PlannedStep] = {}
        for key in reversed(ordered):
            step = by_key[key]
            required = quantity(max(target * step.quantity_per_output, demands[key]))
            batches = (required / step.batch_yield).to_integral_value(
                rounding=ROUND_CEILING
            )
            capacity = quantity(batches * step.batch_yield)
            result[key] = PlannedStep(
                key=key,
                required_quantity=required,
                batches=batches,
                planned_capacity=capacity,
                unit=step.unit,
            )
            for item in step.product_inputs:
                needed = quantity(batches * item.quantity_per_batch)
                if item.source_step_key is not None:
                    demands[item.source_step_key] += needed
            for supply_input in step.supply_inputs:
                quantity(batches * supply_input.quantity_per_batch)
    return [result[key] for key in ordered]
