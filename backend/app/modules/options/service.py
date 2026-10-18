from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.exceptions import PersistenceError
from app.modules.assets.structure_models import AssetFamily
from app.modules.options.exceptions import OptionConflictError, OptionNotFoundError
from app.modules.options.models import OptionDefinition, OptionValue
from app.modules.options.schemas import (
    OptionDefinitionCreate,
    OptionDefinitionUpdate,
    OptionValueCreate,
    OptionValueUpdate,
)
from app.modules.supplies.models import Supply


class OptionService:
    def __init__(self, session: Session) -> None:
        self.session = session

    @contextmanager
    def transaction(self) -> Iterator[None]:
        try:
            yield
            self.session.commit()
        except (OptionNotFoundError, OptionConflictError):
            self.session.rollback()
            raise
        except IntegrityError as error:
            self.session.rollback()
            raise OptionConflictError(
                "La característica u opción entra en conflicto con datos existentes"
            ) from error
        except SQLAlchemyError as error:
            self.session.rollback()
            raise PersistenceError("No se pudieron guardar las opciones") from error
        except Exception:
            self.session.rollback()
            raise

    def definition(
        self, definition_id: UUID, *, lock: bool = False
    ) -> OptionDefinition:
        query = select(OptionDefinition).where(OptionDefinition.id == definition_id)
        if lock:
            query = query.with_for_update().execution_options(populate_existing=True)
        row = self.session.scalar(query)
        if row is None:
            raise OptionNotFoundError("No existe la característica")
        return row

    def value(
        self, definition_id: UUID, value_id: UUID, *, lock: bool = False
    ) -> OptionValue:
        query = select(OptionValue).where(
            OptionValue.id == value_id, OptionValue.definition_id == definition_id
        )
        if lock:
            query = query.with_for_update().execution_options(populate_existing=True)
        row = self.session.scalar(query)
        if row is None:
            raise OptionNotFoundError("No existe la opción en esta característica")
        return row

    def check_family(self, family_id: UUID | None) -> None:
        if family_id is not None and self.session.get(AssetFamily, family_id) is None:
            raise OptionNotFoundError("No existe la familia de diseño")

    def check_supply(self, supply_id: UUID | None) -> None:
        if supply_id is not None:
            supply = self.session.get(Supply, supply_id)
            if supply is None:
                raise OptionNotFoundError("No existe el insumo de la opción")
            if not supply.active:
                raise OptionConflictError("El insumo de la opción está inactivo")

    def create_definition(self, payload: OptionDefinitionCreate) -> OptionDefinition:
        with self.transaction():
            row = OptionDefinition(**payload.model_dump())
            self.session.add(row)
        return row

    def update_definition(
        self, definition_id: UUID, payload: OptionDefinitionUpdate
    ) -> OptionDefinition:
        with self.transaction():
            row = self.definition(definition_id, lock=True)
            for key, value in payload.model_dump(exclude_unset=True).items():
                setattr(row, key, value)
        return row

    def create_value(
        self, definition_id: UUID, payload: OptionValueCreate
    ) -> OptionValue:
        with self.transaction():
            self.definition(definition_id, lock=True)
            self.check_family(payload.family_id)
            self.check_supply(payload.supply_id)
            row = OptionValue(definition_id=definition_id, **payload.model_dump())
            self.session.add(row)
        return row

    def update_value(
        self, definition_id: UUID, value_id: UUID, payload: OptionValueUpdate
    ) -> OptionValue:
        with self.transaction():
            self.definition(definition_id, lock=True)
            row = self.value(definition_id, value_id, lock=True)
            self.check_family(payload.family_id)
            self.check_supply(payload.supply_id)
            for key, value in payload.model_dump(exclude_unset=True).items():
                setattr(row, key, value)
        return row

    def definitions(
        self, active: bool | None, search: str | None, offset: int, limit: int
    ) -> list[OptionDefinition]:
        query = select(OptionDefinition)
        if active is not None:
            query = query.where(OptionDefinition.active == active)
        if search:
            query = query.where(
                OptionDefinition.name.icontains(search, autoescape=True)
            )
        return list(
            self.session.scalars(
                query.order_by(OptionDefinition.name, OptionDefinition.id)
                .offset(offset)
                .limit(limit)
            )
        )

    def values(
        self,
        definition_id: UUID,
        active: bool | None,
        search: str | None,
        offset: int,
        limit: int,
    ) -> list[OptionValue]:
        self.definition(definition_id)
        query = select(OptionValue).where(OptionValue.definition_id == definition_id)
        if active is not None:
            query = query.where(OptionValue.active == active)
        if search:
            query = query.where(OptionValue.name.icontains(search, autoescape=True))
        return list(
            self.session.scalars(
                query.order_by(OptionValue.name, OptionValue.id)
                .offset(offset)
                .limit(limit)
            )
        )
