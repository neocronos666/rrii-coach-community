from decimal import Decimal
from uuid import uuid4

import pytest

from app.modules.production.planning import calculate_plan
from app.modules.recipes.exceptions import InvalidRecipeError
from app.modules.recipes.schemas import RecipePlan


def test_shared_component_demand_is_summed_before_rounding() -> None:
    final, component = uuid4(), uuid4()
    common = {
        "task_type": "manual",
        "unit": "unit",
        "quantity_per_output": "1",
        "batch_yield": "1",
    }
    plan = RecipePlan.model_validate(
        {
            "steps": [
                {
                    **common,
                    "key": "a",
                    "title": "A",
                    "batch_yield": "5",
                    "output_variant_id": component,
                },
                {
                    **common,
                    "key": "b",
                    "title": "B",
                    "depends_on": ["a"],
                    "product_inputs": [
                        {
                            "product_variant_id": component,
                            "quantity_per_batch": "3",
                            "source_step_key": "a",
                        }
                    ],
                },
                {
                    **common,
                    "key": "c",
                    "title": "C",
                    "depends_on": ["a", "b"],
                    "output_variant_id": final,
                    "product_inputs": [
                        {
                            "product_variant_id": component,
                            "quantity_per_batch": "4",
                            "source_step_key": "a",
                        }
                    ],
                },
            ]
        }
    )
    calculated = {step.key: step for step in calculate_plan(plan, final, Decimal(2))}
    assert calculated["a"].required_quantity == 14
    assert calculated["a"].batches == 3
    assert calculated["a"].planned_capacity == 15
    with pytest.raises(InvalidRecipeError):
        calculate_plan(plan, final, Decimal("999999999999"))
