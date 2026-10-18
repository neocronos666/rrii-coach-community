from typing import cast
from unittest.mock import MagicMock

from sqlalchemy.orm import Session

from app.db.repositories import SystemSettingsRepository


def test_repository_flushes_without_committing() -> None:
    session = MagicMock(spec=Session)
    repository = SystemSettingsRepository(cast(Session, session))

    setting = repository.create(key="technical.test", value={"enabled": True})

    assert setting.key == "technical.test"
    session.add.assert_called_once_with(setting)
    session.flush.assert_called_once_with()
    session.commit.assert_not_called()
