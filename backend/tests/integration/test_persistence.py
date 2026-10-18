from collections.abc import Iterator
from uuid import UUID

import pytest
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db.models import SystemSetting
from app.db.repositories import SystemSettingsRepository
from app.db.services import SystemSettingsService
from app.db.session import SessionFactory

pytestmark = pytest.mark.integration


@pytest.fixture
def db_session() -> Iterator[Session]:
    with SessionFactory() as session:
        session.execute(delete(SystemSetting).where(SystemSetting.key.like("test.%")))
        session.commit()
        yield session
        session.rollback()
        session.execute(delete(SystemSetting).where(SystemSetting.key.like("test.%")))
        session.commit()


def test_repository_and_service_persist_uuid_jsonb_and_timestamps(
    db_session: Session,
) -> None:
    service = SystemSettingsService(db_session)
    setting = service.create(
        key="test.persistence",
        value={"enabled": True, "attempts": 1},
    )

    assert isinstance(setting.id, UUID)
    assert setting.created_at.tzinfo is not None
    assert setting.updated_at.tzinfo is not None

    previous_updated_at = setting.updated_at
    service.update(
        key="test.persistence",
        value={"enabled": False, "attempts": 2},
    )

    repository = SystemSettingsRepository(db_session)
    persisted = repository.get_by_key("test.persistence")

    assert persisted is not None
    assert persisted.value == {"enabled": False, "attempts": 2}
    assert persisted.updated_at >= previous_updated_at
