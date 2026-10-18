from datetime import datetime
from decimal import Decimal
from typing import cast
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.modules.production.exceptions import (
    InvalidProductionTaskTransitionError,
    ProductionTaskNotEditableError,
)
from app.modules.production.models import ProductionTask
from app.modules.production.repository import ProductionTaskRepository
from app.modules.production.service import ProductionTaskService


def build(status: str) -> tuple[ProductionTaskService, ProductionTask, MagicMock]:
    session = MagicMock(spec=Session)
    repository = MagicMock(spec=ProductionTaskRepository)
    value = ProductionTask(
        id=uuid4(),
        code="T-2026-000001",
        order_id=uuid4(),
        task_type="manual",
        title="Tarea",
        status=status,
        priority="normal",
        planned_quantity=Decimal("1"),
        queue_position=10,
        production_parameters={},
    )
    repository.get_by_id.return_value = value
    repository.list_unsatisfied_dependency_ids.return_value = []
    return ProductionTaskService(session, repository), value, session


@pytest.mark.parametrize(
    ("initial", "action", "expected", "timestamp"),
    [
        ("queued", "start", "in_progress", "started_at"),
        ("in_progress", "pause", "paused", "paused_at"),
        ("paused", "resume", "in_progress", None),
        ("in_progress", "finish", "physically_completed", "physically_completed_at"),
        ("queued", "cancel", "cancelled", "cancelled_at"),
        ("in_progress", "cancel", "cancelled", "cancelled_at"),
        ("paused", "cancel", "cancelled", "cancelled_at"),
    ],
)
def test_valid_transitions(
    initial: str, action: str, expected: str, timestamp: str | None
) -> None:
    service, task, session = build(initial)
    result = getattr(service, action)(task.id)
    assert result.status == expected
    if timestamp:
        assert isinstance(getattr(result, timestamp), datetime)
    session.commit.assert_called_once_with()


@pytest.mark.parametrize(
    ("initial", "action"),
    [
        ("queued", "pause"),
        ("queued", "finish"),
        ("paused", "finish"),
        ("cancelled", "start"),
        ("cancelled", "resume"),
        ("physically_completed", "start"),
        ("physically_completed", "cancel"),
    ],
)
def test_invalid_transitions(initial: str, action: str) -> None:
    service, task, session = build(initial)
    with pytest.raises(InvalidProductionTaskTransitionError):
        getattr(service, action)(task.id)
    session.rollback.assert_called_once_with()


def test_resume_preserves_started_at() -> None:
    service, task, _ = build("paused")
    original = datetime.now().astimezone()
    task.started_at = original
    service.resume(task.id)
    assert task.started_at is original


def test_resume_does_not_revalidate_dependencies() -> None:
    service, task, _ = build("paused")
    service.resume(task.id)

    assert task.status == "in_progress"
    dependency_query = cast(
        MagicMock, service._repository.list_unsatisfied_dependency_ids
    )
    dependency_query.assert_not_called()


@pytest.mark.parametrize(
    ("state", "changes", "allowed"),
    [
        ("queued", {"planned_quantity": Decimal("2")}, True),
        ("paused", {"planned_quantity": Decimal("2")}, False),
        ("in_progress", {"notes": "ok", "production_parameters": {"x": "1"}}, True),
        ("in_progress", {"machine_id": uuid4()}, False),
        ("physically_completed", {"notes": "x"}, False),
        ("cancelled", {"notes": "x"}, False),
    ],
)
def test_edit_matrix(state: str, changes: dict[str, object], allowed: bool) -> None:
    service, task, _ = build(state)
    if allowed:
        service.update(task.id, changes)
    else:
        with pytest.raises(ProductionTaskNotEditableError):
            service.update(task.id, changes)
