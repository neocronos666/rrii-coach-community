from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class OptionDefinition(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "option_definitions"
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="name_nonempty"),
        UniqueConstraint("name", name="uq_option_definitions_name"),
    )
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())


class OptionValue(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "option_values"
    __table_args__ = (
        CheckConstraint("length(trim(name)) > 0", name="name_nonempty"),
        UniqueConstraint("definition_id", "name", name="uq_option_values_name"),
        UniqueConstraint("definition_id", "id", name="uq_option_values_identity"),
    )
    definition_id: Mapped[UUID] = mapped_column(
        ForeignKey("option_definitions.id", ondelete="RESTRICT"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    family_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("asset_families.id", ondelete="RESTRICT"), index=True
    )
    supply_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("supplies.id", ondelete="RESTRICT"), index=True
    )
