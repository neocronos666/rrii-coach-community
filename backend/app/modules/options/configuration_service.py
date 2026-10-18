from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

from sqlalchemy import and_, delete, or_, select, text, update
from sqlalchemy.orm import Session

from app.modules.assets.models import Asset
from app.modules.assets.structure_models import AssetCompatibility
from app.modules.options.configuration_models import ProductOption, ProductOptionValue
from app.modules.options.configuration_schemas import (
    AllowedOptionValue,
    ConfigurationResolveInput,
    ProductConfigurationInput,
    ProductConfigurationRead,
    ProductOptionInput,
    ResolvedConfiguration,
    ResolvedOptionSelection,
    ResolvedOptionValue,
    SelectedOptionValue,
)
from app.modules.options.exceptions import OptionConflictError, OptionNotFoundError
from app.modules.options.service import OptionService
from app.modules.products.models import Product
from app.modules.supplies.models import Supply


def context_order(options: list[ProductOptionInput]) -> list[UUID]:
    """Orden topológico estable, sin recursión ni reglas condicionales arbitrarias."""
    pending = {option.definition_id: option.context_definition_id for option in options}
    if any(target is not None and target not in pending for target in pending.values()):
        raise OptionConflictError("El contexto debe pertenecer al mismo producto")
    result: list[UUID] = []
    while pending:
        ready = sorted(key for key, target in pending.items() if target not in pending)
        if not ready:
            raise OptionConflictError("Las referencias de contexto forman un ciclo")
        for key in ready:
            del pending[key]
        result.extend(ready)
    return result


class ProductConfigurationService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.catalog = OptionService(session)

    def product(self, product_id: UUID, *, lock: bool = False) -> Product:
        query = select(Product).where(Product.id == product_id)
        if lock:
            query = query.with_for_update().execution_options(populate_existing=True)
        row = self.session.scalar(query)
        if row is None:
            raise OptionNotFoundError("No existe el producto")
        return row

    @contextmanager
    def snapshot(self) -> Iterator[None]:
        """Entrada de lectura: sesión sin consultas previas; no persiste resultados."""
        with self.catalog.transaction():
            self.session.execute(
                text("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            )
            yield

    def _configuration(self, product_id: UUID) -> ProductConfigurationRead:
        values: dict[UUID, list[AllowedOptionValue]] = {}
        for row in self.session.scalars(
            select(ProductOptionValue)
            .where(ProductOptionValue.product_id == product_id)
            .order_by(ProductOptionValue.value_id)
        ):
            values.setdefault(row.definition_id, []).append(
                AllowedOptionValue.model_validate(row)
            )
        options = [
            ProductOptionInput(
                definition_id=row.definition_id,
                min_selections=row.min_selections,
                max_selections=row.max_selections,
                context_asset_id=row.context_asset_id,
                context_definition_id=row.context_definition_id,
                values=values.get(row.definition_id, []),
            )
            for row in self.session.scalars(
                select(ProductOption)
                .where(ProductOption.product_id == product_id)
                .order_by(ProductOption.definition_id)
            )
        ]
        return ProductConfigurationRead(product_id=product_id, options=options)

    def get(self, product_id: UUID) -> ProductConfigurationRead:
        with self.snapshot():
            self.product(product_id)
            return self._configuration(product_id)

    def replace(
        self, product_id: UUID, payload: ProductConfigurationInput
    ) -> ProductConfigurationRead:
        order = context_order(payload.options)
        options = {option.definition_id: option for option in payload.options}
        with self.catalog.transaction():
            self.product(product_id, lock=True)
            for definition_id in sorted(options):
                option = options[definition_id]
                definition = self.catalog.definition(definition_id, lock=True)
                if not definition.active:
                    raise OptionConflictError("La característica está inactiva")
                for entry in option.values:
                    value = self.catalog.value(definition_id, entry.value_id)
                    if not value.active:
                        raise OptionConflictError("La opción está inactiva")
                if option.context_asset_id is not None:
                    self.context_asset(option.context_asset_id)
            self.session.execute(
                delete(ProductOptionValue).where(
                    ProductOptionValue.product_id == product_id
                )
            )
            self.session.execute(
                update(ProductOption)
                .where(ProductOption.product_id == product_id)
                .values(context_definition_id=None)
            )
            self.session.execute(
                delete(ProductOption).where(ProductOption.product_id == product_id)
            )
            for definition_id in order:
                option = options[definition_id]
                self.session.add(
                    ProductOption(
                        product_id=product_id, **option.model_dump(exclude={"values"})
                    )
                )
                # El contexto de otra característica debe existir antes de insertar.
                self.session.flush()
                self.session.add_all(
                    [
                        ProductOptionValue(
                            product_id=product_id,
                            definition_id=definition_id,
                            **entry.model_dump(),
                        )
                        for entry in option.values
                    ]
                )
            self.session.flush()
            result = self._configuration(product_id)
        return result

    def context_asset(self, asset_id: UUID) -> Asset:
        asset = self.session.get(Asset, asset_id)
        if asset is None:
            raise OptionNotFoundError("No existe el recurso de contexto")
        if asset.archived or asset.current_revision_id is None:
            raise OptionConflictError("El recurso de contexto no está disponible")
        return asset

    def resolve(
        self, product_id: UUID, payload: ConfigurationResolveInput
    ) -> ResolvedConfiguration:
        with self.snapshot():
            return self.resolve_in_snapshot(product_id, payload)

    def resolve_in_snapshot(
        self, product_id: UUID, payload: ConfigurationResolveInput
    ) -> ResolvedConfiguration:
        """Resolver dentro de la instantánea abierta por el caso de uso llamador."""
        if not self.product(product_id).active:
            raise OptionConflictError("El producto está inactivo")
        configuration = self._configuration(product_id)
        options = {option.definition_id: option for option in configuration.options}
        selections = {
            selection.definition_id: selection.values
            for selection in payload.selections
        }
        if selections.keys() - options.keys():
            raise OptionConflictError(
                "La selección contiene características ajenas al producto"
            )
        resolved: dict[UUID, ResolvedOptionSelection] = {}
        for definition_id in context_order(configuration.options):
            option = options[definition_id]
            chosen = selections.get(
                definition_id,
                [
                    SelectedOptionValue(
                        value_id=value.value_id, quantity=value.default_quantity
                    )
                    for value in option.values
                    if value.default_quantity is not None
                ],
            )
            if len(chosen) < option.min_selections or (
                option.max_selections is not None
                and len(chosen) > option.max_selections
            ):
                raise OptionConflictError(
                    f"Cantidad de selecciones fuera de rango: {definition_id}"
                )
            if chosen and not self.catalog.definition(definition_id).active:
                raise OptionConflictError(
                    "La característica seleccionada está inactiva"
                )
            allowed = {value.value_id for value in option.values}
            if any(value.value_id not in allowed for value in chosen):
                raise OptionConflictError("La opción no está permitida en el producto")
            context_id = self._context(option, resolved) if chosen else None
            values = [
                self._resolve_value(definition_id, entry, context_id)
                for entry in sorted(chosen, key=lambda value: value.value_id)
            ]
            resolved[definition_id] = ResolvedOptionSelection(
                definition_id=definition_id,
                context_asset_id=context_id,
                values=values,
            )
        return ResolvedConfiguration(
            product_id=product_id, selections=list(resolved.values())
        )

    def _context(
        self, option: ProductOptionInput, resolved: dict[UUID, ResolvedOptionSelection]
    ) -> UUID | None:
        if option.context_asset_id is not None:
            return self.context_asset(option.context_asset_id).id
        if option.context_definition_id is not None:
            source = resolved[option.context_definition_id].values
            if len(source) != 1 or source[0].asset_id is None:
                raise OptionConflictError(
                    "El contexto seleccionado debe resolver un único recurso"
                )
            return source[0].asset_id
        return None

    def _resolve_value(
        self, definition_id: UUID, entry: SelectedOptionValue, context_id: UUID | None
    ) -> ResolvedOptionValue:
        value = self.catalog.value(definition_id, entry.value_id)
        if not value.active:
            raise OptionConflictError("La opción seleccionada está inactiva")
        asset: Asset | None = None
        if value.family_id is not None:
            query = select(Asset).where(
                Asset.family_id == value.family_id,
                Asset.archived.is_(False),
                Asset.current_revision_id.is_not(None),
            )
            if context_id is not None:
                query = query.join(
                    AssetCompatibility,
                    or_(
                        and_(
                            AssetCompatibility.left_asset_id == context_id,
                            AssetCompatibility.right_asset_id == Asset.id,
                        ),
                        and_(
                            AssetCompatibility.right_asset_id == context_id,
                            AssetCompatibility.left_asset_id == Asset.id,
                        ),
                    ),
                )
            candidates = list(self.session.scalars(query.order_by(Asset.id).limit(2)))
            if not candidates:
                raise OptionConflictError(
                    "No hay implementación declarada para la opción y contexto: "
                    f"{value.id}"
                )
            if len(candidates) > 1:
                raise OptionConflictError(
                    f"Implementación ambigua para la opción y contexto: {value.id}"
                )
            asset = candidates[0]
        elif context_id is not None:
            raise OptionConflictError(
                "Una opción con contexto físico necesita una familia de diseño"
            )
        supply = (
            self.session.get(Supply, value.supply_id)
            if value.supply_id is not None
            else None
        )
        if value.supply_id is not None and (supply is None or not supply.active):
            raise OptionConflictError("El insumo de la opción no está disponible")
        return ResolvedOptionValue(
            supply_id=supply.id if supply else None,
            supply_unit=supply.base_unit if supply else None,
            value_id=value.id,
            quantity=entry.quantity,
            family_id=value.family_id,
            asset_id=asset.id if asset else None,
            revision_id=asset.current_revision_id if asset else None,
        )
