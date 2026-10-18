from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.modules.production.schemas import ProductionTaskCreate, ProductionTaskUpdate
from app.modules.production.types import ProductionTaskType


def test_create_schema_applies_api_defaults() -> None:
    payload = ProductionTaskCreate(
        task_type=ProductionTaskType.MANUAL,
        title="Preparar pieza",
        planned_quantity=Decimal("2.5"),
    )

    assert payload.priority.value == "normal"
    assert payload.queue_position == 1000
    assert payload.machine_id is None
    assert payload.production_parameters == {}


@pytest.mark.parametrize(
    "forbidden",
    [
        {"status": "in_progress"},
        {"code": "T-2026-999999"},
        {"order_id": str(uuid4())},
        {"project_component_id": str(uuid4())},
        {"started_at": "2026-09-05T10:00:00Z"},
    ],
)
def test_create_schema_rejects_server_managed_fields(forbidden: dict[str, str]) -> None:
    with pytest.raises(ValidationError):
        ProductionTaskCreate.model_validate(
            {
                "task_type": "manual",
                "title": "Tarea",
                "planned_quantity": "1",
                **forbidden,
            }
        )


def test_update_distinguishes_omitted_from_explicit_null() -> None:
    payload = ProductionTaskUpdate.model_validate(
        {"machine_id": None, "description": None, "notes": None}
    )

    assert payload.model_dump(exclude_unset=True) == {
        "description": None,
        "machine_id": None,
        "notes": None,
    }


def test_update_rejects_status_and_null_for_required_fields() -> None:
    with pytest.raises(ValidationError):
        ProductionTaskUpdate.model_validate({"status": "in_progress"})
    with pytest.raises(ValidationError):
        ProductionTaskUpdate.model_validate({"queue_position": None})
