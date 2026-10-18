from collections.abc import Iterator
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.db.session import SessionFactory
from app.main import app
from app.modules.orders.models import Order
from app.modules.production.models import ProductionTaskDependency
from app.modules.projects.models import Project
from app.modules.supplies.models import SupplyStockMovement
from tests.integration.test_production_api import (
    clean_data,
    create_order,
    create_project,
    create_task,
    mark_legacy,
    task_payload,
)

pytestmark = pytest.mark.integration
MISSING_ID = "00000000-0000-0000-0000-000000000000"


@pytest.fixture(autouse=True)
def clean_dependency_data() -> Iterator[None]:
    clean_data()
    yield
    clean_data()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def add_dependency(client: TestClient, task_id: object, prerequisite_id: object) -> Any:
    return client.post(
        f"/api/v1/production-tasks/{task_id}/dependencies",
        json={"depends_on_task_id": prerequisite_id},
    )


def project_component_ids(client: TestClient, project_id: str) -> list[str]:
    project = client.get(f"/api/v1/projects/{project_id}").json()
    return [str(value["id"]) for value in project["components"]]


def create_component_task(client: TestClient, component_id: str) -> dict[str, object]:
    response = client.post(
        f"/api/v1/project-components/{component_id}/production-tasks",
        json=task_payload(),
    )
    assert response.status_code == 201
    mark_legacy(str(response.json()["id"]))
    return cast(dict[str, object], response.json())


def test_dependency_persistence_constraints_and_foreign_keys(
    client: TestClient,
) -> None:
    order_id = create_order(client)
    prerequisite = create_task(client, order_id)
    dependent = create_task(client, order_id)

    with SessionFactory() as session:
        valid = ProductionTaskDependency(
            task_id=UUID(str(dependent["id"])),
            depends_on_task_id=UUID(str(prerequisite["id"])),
        )
        session.add(valid)
        session.commit()
        assert valid.created_at is not None
        task_id = valid.task_id
        depends_on_task_id = valid.depends_on_task_id
        session.expunge(valid)
        session.add(
            ProductionTaskDependency(
                task_id=task_id,
                depends_on_task_id=depends_on_task_id,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()

    with SessionFactory() as session:
        identifier = UUID(str(dependent["id"]))
        session.add(
            ProductionTaskDependency(
                task_id=identifier,
                depends_on_task_id=identifier,
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()

    with SessionFactory() as session:
        session.add(
            ProductionTaskDependency(
                task_id=UUID(str(dependent["id"])),
                depends_on_task_id=uuid4(),
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_same_order_api_add_list_remove_and_conflicts(client: TestClient) -> None:
    order_id = create_order(client)
    prerequisite = create_task(client, order_id, title="Prerequisito")
    dependent = create_task(client, order_id, title="Dependiente")

    created = add_dependency(client, dependent["id"], prerequisite["id"])
    assert created.status_code == 201
    assert created.json()["task_id"] == dependent["id"]
    assert created.json()["depends_on_task_id"] == prerequisite["id"]
    assert created.json()["prerequisite"]["title"] == "Prerequisito"
    listed = client.get(f"/api/v1/production-tasks/{dependent['id']}/dependencies")
    assert listed.status_code == 200
    assert [value["depends_on_task_id"] for value in listed.json()] == [
        prerequisite["id"]
    ]
    assert (
        add_dependency(client, dependent["id"], prerequisite["id"]).status_code == 409
    )
    assert add_dependency(client, dependent["id"], dependent["id"]).status_code == 409
    assert add_dependency(client, dependent["id"], MISSING_ID).status_code == 404
    assert add_dependency(client, MISSING_ID, prerequisite["id"]).status_code == 404
    invalid = client.post(
        f"/api/v1/production-tasks/{dependent['id']}/dependencies",
        json={"depends_on_task_id": prerequisite["id"], "extra": True},
    )
    assert invalid.status_code == 422

    removed = client.delete(
        f"/api/v1/production-tasks/{dependent['id']}/dependencies/{prerequisite['id']}"
    )
    assert removed.status_code == 204
    assert (
        client.get(f"/api/v1/production-tasks/{dependent['id']}/dependencies").json()
        == []
    )
    assert (
        client.delete(
            f"/api/v1/production-tasks/{dependent['id']}/dependencies/{prerequisite['id']}"
        ).status_code
        == 404
    )
    assert (
        client.delete(f"/api/v1/production-tasks/{dependent['id']}").status_code == 405
    )


def test_cross_order_and_order_project_dependencies_are_rejected(
    client: TestClient,
) -> None:
    first_order_task = create_task(client, create_order(client))
    second_order_task = create_task(client, create_order(client))
    project_id, component_id = create_project(client)
    project_task = create_component_task(client, component_id)

    assert (
        add_dependency(
            client, second_order_task["id"], first_order_task["id"]
        ).status_code
        == 409
    )
    assert (
        add_dependency(client, first_order_task["id"], project_task["id"]).status_code
        == 409
    )
    assert (
        add_dependency(client, project_task["id"], first_order_task["id"]).status_code
        == 409
    )
    assert client.get(f"/api/v1/projects/{project_id}").status_code == 200


def test_same_project_cross_component_allowed_and_distinct_projects_rejected(
    client: TestClient,
) -> None:
    project_id, _ = create_project(client)
    project_status = client.get(f"/api/v1/projects/{project_id}").json()["status"]
    first_component, second_component = project_component_ids(client, project_id)
    first = create_component_task(client, first_component)
    second = create_component_task(client, second_component)
    assert add_dependency(client, second["id"], first["id"]).status_code == 201
    for task in (first, second):
        assert (
            client.post(f"/api/v1/production-tasks/{task['id']}/start").status_code
            == 200
        )
        assert (
            client.post(f"/api/v1/production-tasks/{task['id']}/finish").status_code
            == 200
        )
    assert (
        client.get(f"/api/v1/projects/{project_id}").json()["status"] == project_status
    )

    other_project_id, other_component = create_project(client)
    other = create_component_task(client, other_component)
    assert add_dependency(client, other["id"], first["id"]).status_code == 409
    assert project_id != other_project_id


def test_direct_indirect_cycles_chain_and_multiple_prerequisites(
    client: TestClient,
) -> None:
    order_id = create_order(client)
    first = create_task(client, order_id, title="A")
    second = create_task(client, order_id, title="B")
    third = create_task(client, order_id, title="C")
    fourth = create_task(client, order_id, title="D")

    assert add_dependency(client, second["id"], first["id"]).status_code == 201
    assert add_dependency(client, first["id"], second["id"]).status_code == 409
    assert add_dependency(client, third["id"], second["id"]).status_code == 201
    assert add_dependency(client, fourth["id"], third["id"]).status_code == 201
    assert add_dependency(client, first["id"], fourth["id"]).status_code == 409
    assert add_dependency(client, third["id"], first["id"]).status_code == 201
    dependencies = client.get(
        f"/api/v1/production-tasks/{third['id']}/dependencies"
    ).json()
    assert {value["depends_on_task_id"] for value in dependencies} == {
        first["id"],
        second["id"],
    }


@pytest.mark.parametrize(
    "prerequisite_state",
    ["queued", "in_progress", "paused", "cancelled"],
)
def test_start_blocked_by_unsatisfied_prerequisite(
    client: TestClient, prerequisite_state: str
) -> None:
    order_id = create_order(client)
    prerequisite = create_task(client, order_id)
    dependent = create_task(client, order_id)
    assert (
        add_dependency(client, dependent["id"], prerequisite["id"]).status_code == 201
    )

    if prerequisite_state in {"in_progress", "paused"}:
        assert (
            client.post(
                f"/api/v1/production-tasks/{prerequisite['id']}/start"
            ).status_code
            == 200
        )
    if prerequisite_state == "paused":
        assert (
            client.post(
                f"/api/v1/production-tasks/{prerequisite['id']}/pause"
            ).status_code
            == 200
        )
    if prerequisite_state == "cancelled":
        assert (
            client.post(
                f"/api/v1/production-tasks/{prerequisite['id']}/cancel"
            ).status_code
            == 200
        )

    blocked = client.post(f"/api/v1/production-tasks/{dependent['id']}/start")
    assert blocked.status_code == 409
    assert "prerrequisitos" in blocked.json()["detail"]


def test_all_prerequisites_must_finish_and_no_scheduler_runs(
    client: TestClient,
) -> None:
    order_id = create_order(client)
    first = create_task(client, order_id)
    second = create_task(client, order_id)
    dependent = create_task(client, order_id)
    assert add_dependency(client, dependent["id"], first["id"]).status_code == 201
    assert add_dependency(client, dependent["id"], second["id"]).status_code == 201

    for prerequisite in (first, second):
        assert (
            client.post(
                f"/api/v1/production-tasks/{prerequisite['id']}/start"
            ).status_code
            == 200
        )
        assert (
            client.post(
                f"/api/v1/production-tasks/{prerequisite['id']}/finish"
            ).status_code
            == 200
        )
        if prerequisite is first:
            assert (
                client.post(
                    f"/api/v1/production-tasks/{dependent['id']}/start"
                ).status_code
                == 409
            )
    still_queued = client.get(f"/api/v1/production-tasks/{dependent['id']}").json()
    assert still_queued["status"] == "queued"
    assert (
        client.post(f"/api/v1/production-tasks/{dependent['id']}/start").status_code
        == 200
    )


def test_cancelled_prerequisite_cannot_be_added_and_later_cancel_is_retained(
    client: TestClient,
) -> None:
    order_id = create_order(client)
    cancelled = create_task(client, order_id)
    dependent = create_task(client, order_id)
    assert (
        client.post(f"/api/v1/production-tasks/{cancelled['id']}/cancel").status_code
        == 200
    )
    assert add_dependency(client, dependent["id"], cancelled["id"]).status_code == 409

    prerequisite = create_task(client, order_id)
    assert (
        add_dependency(client, dependent["id"], prerequisite["id"]).status_code == 201
    )
    assert (
        client.post(f"/api/v1/production-tasks/{prerequisite['id']}/cancel").status_code
        == 200
    )
    dependencies = client.get(
        f"/api/v1/production-tasks/{dependent['id']}/dependencies"
    ).json()
    assert [value["depends_on_task_id"] for value in dependencies] == [
        prerequisite["id"]
    ]
    assert (
        client.get(f"/api/v1/production-tasks/{dependent['id']}").json()["status"]
        == "queued"
    )
    assert (
        client.post(f"/api/v1/production-tasks/{dependent['id']}/start").status_code
        == 409
    )


@pytest.mark.parametrize(
    "dependent_state",
    ["in_progress", "paused", "physically_completed", "cancelled"],
)
def test_only_queued_task_can_modify_dependencies(
    client: TestClient, dependent_state: str
) -> None:
    order_id = create_order(client)
    prerequisite = create_task(client, order_id)
    another = create_task(client, order_id)
    dependent = create_task(client, order_id)
    assert (
        add_dependency(client, dependent["id"], prerequisite["id"]).status_code == 201
    )

    if dependent_state != "cancelled":
        assert (
            client.post(
                f"/api/v1/production-tasks/{prerequisite['id']}/start"
            ).status_code
            == 200
        )
        assert (
            client.post(
                f"/api/v1/production-tasks/{prerequisite['id']}/finish"
            ).status_code
            == 200
        )
        assert (
            client.post(f"/api/v1/production-tasks/{dependent['id']}/start").status_code
            == 200
        )
        if dependent_state in {"paused", "physically_completed"}:
            action = "pause" if dependent_state == "paused" else "finish"
            assert (
                client.post(
                    f"/api/v1/production-tasks/{dependent['id']}/{action}"
                ).status_code
                == 200
            )
    else:
        assert (
            client.post(
                f"/api/v1/production-tasks/{dependent['id']}/cancel"
            ).status_code
            == 200
        )

    assert add_dependency(client, dependent["id"], another["id"]).status_code == 409
    assert (
        client.delete(
            f"/api/v1/production-tasks/{dependent['id']}/dependencies/{prerequisite['id']}"
        ).status_code
        == 409
    )


def test_dependency_flow_changes_neither_stock_nor_commercial_origin(
    client: TestClient,
) -> None:
    order_id = create_order(client)
    prerequisite = create_task(client, order_id)
    dependent = create_task(client, order_id)
    with SessionFactory() as session:
        movements_before = session.scalar(
            select(func.count()).select_from(SupplyStockMovement)
        )
        order = session.get(Order, order_id)
        assert order is not None
        order_status = order.status

    assert (
        add_dependency(client, dependent["id"], prerequisite["id"]).status_code == 201
    )
    for task in (prerequisite, dependent):
        assert (
            client.post(f"/api/v1/production-tasks/{task['id']}/start").status_code
            == 200
        )
        assert (
            client.post(f"/api/v1/production-tasks/{task['id']}/finish").status_code
            == 200
        )

    with SessionFactory() as session:
        assert (
            session.scalar(select(func.count()).select_from(SupplyStockMovement))
            == movements_before
        )
        order = session.get(Order, order_id)
        assert order is not None
        assert order.status == order_status
        assert session.scalar(select(func.count()).select_from(Project)) == 0
        assert (
            session.scalar(select(func.count()).select_from(ProductionTaskDependency))
            == 1
        )
