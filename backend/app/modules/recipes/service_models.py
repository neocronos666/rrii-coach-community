from sqlalchemy import Boolean, CheckConstraint, String, Text, true
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class ServiceDefinition(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "service_definitions"
    __table_args__ = (CheckConstraint("length(trim(name)) > 0", name="name_nonempty"),)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    instructions: Mapped[str | None] = mapped_column(Text)
    action_template: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
