from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from app.db.session import SessionFactory
from app.main import app
from app.modules.options.configuration_schemas import ResolvedConfiguration
from app.modules.options.configuration_service import ProductConfigurationService
from app.modules.production.models import ProductionTaskDependency
from app.modules.production.plan_models import ProductionPlan
from app.modules.production.plan_schemas import ProductionPlanCreate
from app.modules.production.plan_service import ProductionPlanService
from app.modules.products.allocation_models import ProductStockAllocation
from app.modules.supplies.reservation_models import SupplyReservation
from tests.integration import test_hito10b_options as catalog
from tests.integration.test_hito10b_configuration import configure, selections
from tests.integration.test_hito10b_machine_assignment import machine
from tests.integration.test_hito10b_recipe_conditions import save, setup, steps
from tests.integration.test_production_api import create_order

pytestmark = pytest.mark.integration
client = catalog.client


def body(recipe: str, variant: str, **changes: Any) -> dict[str, Any]:
    return {
        "request_id": str(uuid4()),
        "recipe_id": recipe,
        "variant_id": variant,
        "target_quantity": "3",
        **changes,
    }


def test_selected_steps_dependencies_reservations_and_snapshot(
    client: TestClient,
) -> None:
    product, variant, recipe, entry = setup(client)
    supply = client.post(
        "/api/v1/supplies",
        json={"name": "Pintura", "category": "consumable", "base_unit": "ml"},
    ).json()["id"]
    recipe_steps = steps(entry)
    recipe_steps[1]["supply_inputs"] = [
        {"supply_id": supply, "quantity_per_batch": "2"}
    ]
    save(client, recipe, recipe_steps)
    order = create_order(client)
    for count in (0, 1):
        chosen = [selections(entry, count)]
        payload = body(recipe, variant, selections=chosen)
        preview = client.post(
            f"/api/v1/recipes/{recipe}/production-preview",
            json={"variant_id": variant, "target_quantity": "3", "selections": chosen},
        )
        assert preview.status_code == 200, preview.text
        created = client.post(f"/api/v1/orders/{order}/production-plans", json=payload)
        assert created.status_code == 201, created.text
        result = created.json()
        assert result["snapshot"]["configuration"] == preview.json()["configuration"]
        assert result["snapshot"]["configuration"]["product_id"] == product
        assert result["snapshot"]["planning"] == preview.json()["steps"]
        tasks = {task["recipe_step_key"]: task for task in result["tasks"]}
        assert set(tasks) == (
            {"print", "box", "pack"}
            if count == 0
            else {"print", "paint", "dry", "box", "pack"}
        )
        with SessionFactory() as session:
            prerequisite_ids = set(
                session.scalars(
                    select(ProductionTaskDependency.depends_on_task_id).where(
                        ProductionTaskDependency.task_id == UUID(tasks["pack"]["id"])
                    )
                )
            )
            expected = {
                UUID(tasks[key]["id"])
                for key in (["print", "box"] if count == 0 else ["dry", "box"])
            }
            assert prerequisite_ids == expected
            reservations = list(
                session.scalars(
                    select(SupplyReservation).where(
                        SupplyReservation.task_id.in_(
                            [UUID(task["id"]) for task in tasks.values()]
                        )
                    )
                )
            )
            assert len(reservations) == count
            if reservations:
                assert reservations[0].quantity == Decimal("6")
        assert (f"insufficient_supply_stock:{supply}" in result["warnings"]) == bool(
            count
        )


def test_defaults_and_historical_retry_after_options_removed(
    client: TestClient,
) -> None:
    product, variant, recipe, entry = setup(client)
    entry["values"][0]["default_quantity"] = "1"
    configure(client, product, [entry])
    save(client, recipe, steps(entry))
    order = create_order(client)
    path = f"/api/v1/orders/{order}/production-plans"
    payload = body(recipe, variant)
    created = client.post(path, json=payload)
    assert created.status_code == 201, created.text
    assert created.json()["snapshot"]["omitted_step_keys"] == []
    configure(client, product, [])
    retried = client.post(path, json=payload)
    assert retried.status_code == 201, retried.text
    assert retried.json()["snapshot"] == created.json()["snapshot"]
    assert retried.json()["id"] == created.json()["id"]
    assert (
        client.post(
            path, json={**payload, "selections": [selections(entry, 0)]}
        ).status_code
        == 409
    )
    assert (
        client.post(path, json={**payload, "request_id": str(uuid4())}).status_code
        == 409
    )


def test_old_request_without_selections_is_idempotent(client: TestClient) -> None:
    _product, variant, recipe, entry = setup(client)
    save(client, recipe, steps(entry))
    order = create_order(client)
    path = f"/api/v1/orders/{order}/production-plans"
    payload = body(recipe, variant)
    created = client.post(path, json=payload).json()
    with SessionFactory() as session:
        plan = session.get(ProductionPlan, UUID(created["id"]))
        assert plan is not None
        old = {
            key: value
            for key, value in plan.request_payload.items()
            if key != "selections"
        }
        plan.request_payload = old
        session.commit()
    retry = client.post(path, json=payload)
    assert retry.status_code == 201, retry.text
    assert retry.json()["id"] == created["id"]
    with SessionFactory() as session:
        plan = session.get(ProductionPlan, UUID(created["id"]))
        assert plan is not None and plan.request_payload == old


def test_omitted_assignment_is_rejected_without_partial_writes(
    client: TestClient,
) -> None:
    _product, variant, recipe, entry = setup(client)
    recipe_steps = steps(entry)
    recipe_steps[0]["when_selected"] = recipe_steps[1]["when_selected"]
    save(client, recipe, recipe_steps)
    printer = machine(client, "Primera")
    order = create_order(client)
    path = f"/api/v1/orders/{order}/production-plans"
    payload = body(recipe, variant, machine_assignments={"print": printer})
    assert client.post(path, json=payload).status_code == 409
    with SessionFactory() as session:
        assert session.scalar(select(func.count()).select_from(ProductionPlan)) == 0
        assert (
            session.scalar(select(func.count()).select_from(ProductStockAllocation))
            == 0
        )
    response = client.post(path, json={**payload, "selections": [selections(entry, 1)]})
    assert response.status_code == 201, response.text
    task = next(
        task for task in response.json()["tasks"] if task["recipe_step_key"] == "print"
    )
    assert task["machine_id"] == printer


def test_concurrent_configured_generation_is_idempotent(client: TestClient) -> None:
    _product, variant, recipe, entry = setup(client)
    save(client, recipe, steps(entry))
    order = create_order(client)
    path = f"/api/v1/orders/{order}/production-plans"
    payload = body(recipe, variant, selections=[selections(entry, 1)])

    def create(_: int) -> str:
        with TestClient(app) as parallel:
            response = parallel.post(path, json=payload)
            assert response.status_code == 201, response.text
            return str(response.json()["id"])

    with ThreadPoolExecutor(max_workers=2) as executor:
        ids = list(executor.map(create, [0, 1]))
    assert ids[0] == ids[1]
    with SessionFactory() as session:
        assert session.scalar(select(func.count()).select_from(ProductionPlan)) == 1
        assert (
            session.scalar(select(func.count()).select_from(ProductStockAllocation))
            == 1
        )


def test_configuration_edit_during_generation_uses_same_snapshot(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    product, variant, recipe, entry = setup(client)
    save(client, recipe, steps(entry))
    order = create_order(client)
    original = ProductConfigurationService.resolve_in_snapshot

    def concurrent_edit(
        self: ProductConfigurationService, *args: Any, **kwargs: Any
    ) -> ResolvedConfiguration:
        result = original(self, *args, **kwargs)
        configure(client, product, [])
        return result

    monkeypatch.setattr(
        ProductConfigurationService, "resolve_in_snapshot", concurrent_edit
    )
    with SessionFactory() as session:
        service = ProductionPlanService(session)
        plan = service.create(
            ProductionPlanCreate.model_validate(
                body(recipe, variant, selections=[selections(entry, 1)])
            ),
            order_id=UUID(order),
        )
        assert (
            plan.snapshot["configuration"]["selections"][0]["values"][0]["value_id"]
            == entry["values"][0]["value_id"]
        )
        assert plan.snapshot["omitted_step_keys"] == []


@pytest.mark.parametrize("failures", [1, 3])
def test_commit_serialization_retry_rolls_back_all_rows(
    client: TestClient, monkeypatch: pytest.MonkeyPatch, failures: int
) -> None:
    from psycopg.errors import SerializationFailure
    from sqlalchemy.exc import OperationalError

    from app.modules.products.stock_service import ProductStockConflictError

    _product, variant, recipe, entry = setup(client)
    save(client, recipe, steps(entry))
    order = create_order(client)
    payload = ProductionPlanCreate.model_validate(
        body(recipe, variant, selections=[selections(entry, 1)])
    )
    with SessionFactory() as session:
        original_commit = session.commit
        attempts = 0

        def commit() -> None:
            nonlocal attempts
            attempts += 1
            if attempts <= failures:
                raise OperationalError(
                    "COMMIT",
                    {},
                    SerializationFailure("Conflicto simulado al confirmar"),
                )
            original_commit()

        monkeypatch.setattr(session, "commit", commit)
        service = ProductionPlanService(session)
        if failures == 3:
            with pytest.raises(ProductStockConflictError, match="concurrente"):
                service.create(payload, order_id=UUID(order))
            assert attempts == 3
        else:
            plan = service.create(payload, order_id=UUID(order))
            assert attempts == 2
            assert len(service.read(plan).tasks) == 5
    with SessionFactory() as session:
        expected = 0 if failures == 3 else 1
        assert (
            session.scalar(select(func.count()).select_from(ProductionPlan)) == expected
        )
        assert (
            session.scalar(select(func.count()).select_from(ProductStockAllocation))
            == expected
        )


def test_invalid_selections_and_physical_shortfall_leave_no_plan(
    client: TestClient,
) -> None:
    from tests.integration.test_hito10b_base_recipe import final, product
    from tests.integration.test_hito10b_recipe_conditions import condition

    _product, variant, recipe, entry = setup(client)
    _, component = product(client)
    save(
        client,
        recipe,
        [
            {
                "key": "piece",
                "title": "Pieza",
                "output_variant_id": component,
                "when_selected": condition(entry),
            },
            final(
                depends_on=["piece"],
                product_inputs=[
                    {
                        "product_variant_id": component,
                        "quantity_per_batch": "1",
                        "source_step_key": "piece",
                    }
                ],
            ),
        ],
    )
    order = create_order(client)
    path = f"/api/v1/orders/{order}/production-plans"
    assert client.post(path, json=body(recipe, variant)).status_code == 409
    foreign = {"definition_id": str(uuid4()), "values": []}
    assert (
        client.post(path, json=body(recipe, variant, selections=[foreign])).status_code
        == 409
    )
    duplicate = selections(entry, 1)
    assert (
        client.post(
            path, json=body(recipe, variant, selections=[duplicate, duplicate])
        ).status_code
        == 422
    )
    with SessionFactory() as session:
        assert session.scalar(select(func.count()).select_from(ProductionPlan)) == 0
