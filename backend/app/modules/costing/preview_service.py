from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.modules.costing.calculator import TechnicalCostCalculator
from app.modules.costing.fifo import FifoLayer, FifoPool
from app.modules.costing.preview_schemas import (
    PreviewLine,
    PricingEvaluation,
    PricingPreviewCreate,
    PricingPreviewRead,
)
from app.modules.costing.service import CostCalculationService
from app.modules.costing.types import ResolvedCostItem
from app.modules.installation.service import InstallationSettingsService
from app.modules.production.planning import calculate_plan, quantity
from app.modules.quotes.calculator import QuoteCalculator
from app.modules.recipes.exceptions import InvalidRecipeError
from app.modules.recipes.resolution import RecipeResolutionService
from app.modules.recipes.service import RecipeService
from app.modules.recipes.types import RecipeStepKind
from app.modules.supplies.exceptions import SupplyNotFoundError
from app.modules.supplies.models import SupplyPurchase, SupplyStockMovement


class PricingPreviewService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def _pool(self, supply_id: UUID) -> FifoPool:
        pool = FifoPool()
        rows = self.session.execute(
            select(SupplyStockMovement, SupplyPurchase)
            .outerjoin(
                SupplyPurchase, SupplyStockMovement.purchase_id == SupplyPurchase.id
            )
            .where(SupplyStockMovement.supply_id == supply_id)
            .order_by(
                SupplyStockMovement.occurred_at,
                SupplyStockMovement.created_at,
                SupplyStockMovement.id,
            )
        )
        for movement, purchase in rows:
            if movement.quantity < 0:
                pool.take(-movement.quantity)
                continue
            # Una relación incoherente nunca se convierte en costo conocido.
            valid = (
                purchase is not None
                and purchase.supply_id == supply_id
                and purchase.quantity == movement.quantity
                and movement.movement_type == "purchase"
            )
            pool.add(
                FifoLayer(
                    movement.quantity,
                    movement.id,
                    purchase.id if valid else None,
                    purchase.total_cost / purchase.quantity if valid else None,
                    purchase.currency if valid else None,
                )
            )
        return pool

    def preview(self, payload: PricingPreviewCreate) -> PricingPreviewRead:
        resolution = RecipeResolutionService(self.session)
        with resolution.options.snapshot():
            self.session.execute(text("SET TRANSACTION READ ONLY"))
            return self.evaluate_in_snapshot(payload).preview

    def evaluate_in_snapshot(self, payload: PricingPreviewCreate) -> PricingEvaluation:
        """El caller controla aislamiento y transacción; no escribe ni confirma."""
        resolution = RecipeResolutionService(self.session)
        recipes = RecipeService(self.session)
        recipe = recipes.get(payload.recipe_id)
        variant = recipes.production_variant(recipe, payload.variant_id)
        product = recipes.products.get_product(variant.product_id)
        if not recipe.active or not variant.active or not product.active:
            raise InvalidRecipeError("Receta, variante y producto deben estar activos")
        if (
            variant.base_unit == "unit"
            and payload.target_quantity != payload.target_quantity.to_integral_value()
        ):
            raise InvalidRecipeError("La cantidad de unidades debe ser entera")
        plan, configuration, omitted = resolution.resolve_recipe_in_snapshot(
            recipe, variant, payload.target_quantity, payload.selections
        )
        planned = calculate_plan(plan, variant.id, payload.target_quantity)
        if set(payload.step_estimates) - {step.key for step in plan.steps}:
            raise InvalidRecipeError(
                "Hay estimaciones para pasos inexistentes u omitidos"
            )
        settings = InstallationSettingsService(self.session).get()
        costs = CostCalculationService(self.session)
        pools: dict[UUID, FifoPool] = {}
        lines: list[PreviewLine] = []
        warnings: list[str] = []
        calculator = TechnicalCostCalculator()

        def append(
            key: str,
            item: ResolvedCostItem,
            *,
            supply_id: UUID | None = None,
            layer: FifoLayer | None = None,
        ) -> None:
            breakdown = calculator.calculate([item])
            line = breakdown.lines[0]
            lines.append(
                PreviewLine(
                    step_key=key,
                    category=line.category,
                    description=line.description,
                    quantity=line.quantity,
                    unit=line.unit,
                    unit_cost=line.unit_cost,
                    subtotal=line.subtotal,
                    currency=line.currency,
                    source=line.source,
                    source_reference=line.source_reference,
                    supply_id=supply_id,
                    movement_id=layer.movement_id if layer else None,
                    purchase_id=layer.purchase_id if layer else None,
                    complete=line.complete,
                )
            )
            warnings.extend(breakdown.warnings)

        steps = {item.key: item for item in plan.steps}
        requested_totals: dict[UUID, Decimal] = {}
        for demand in planned:
            step = steps[demand.key]
            for requested in step.supply_inputs:
                supply = costs._supplies.get(requested.supply_id)
                if supply is None:
                    raise SupplyNotFoundError("No existe el insumo solicitado")
                if not supply.active:
                    raise InvalidRecipeError("Un insumo requerido está inactivo")
                needed = quantity(demand.batches * requested.quantity_per_batch)
                requested_totals[supply.id] = (
                    requested_totals.get(supply.id, Decimal(0)) + needed
                )
                if payload.strategy == "fifo":
                    if supply.id not in pools:
                        pools[supply.id] = self._pool(supply.id)
                    layers = pools[supply.id].take(needed)
                else:
                    quote = costs._supply_costs.get_unit_cost(
                        supply.id, supply.base_unit
                    )
                    layers = [
                        FifoLayer(
                            needed,
                            None,
                            UUID(quote.source_reference)
                            if quote and quote.source_reference
                            else None,
                            quote.amount if quote else None,
                            quote.currency if quote else None,
                        )
                    ]
                for layer in layers:
                    append(
                        step.key,
                        ResolvedCostItem(
                            category=costs._supply_cost_category(supply.category).value,
                            description=supply.name,
                            quantity=layer.quantity,
                            unit=supply.base_unit,
                            unit_cost=layer.unit_cost,
                            currency=layer.currency,
                            source=payload.strategy
                            if layer.unit_cost is not None
                            else "unavailable",
                            source_reference=str(layer.purchase_id)
                            if layer.purchase_id
                            else None,
                            warning=f"Costo FIFO desconocido: {supply.name}"
                            if layer.unit_cost is None
                            else None,
                        ),
                        supply_id=supply.id,
                        layer=layer,
                    )
            for component in step.product_inputs:
                if component.source_step_key is None:
                    append(
                        step.key,
                        ResolvedCostItem(
                            category="component",
                            description="Componente externo sin fuente de costo",
                            quantity=quantity(
                                demand.batches * component.quantity_per_batch
                            ),
                            unit=recipes.products.get_variant(
                                component.product_variant_id
                            ).base_unit,
                            unit_cost=None,
                            currency=None,
                            source="unavailable",
                            source_reference=str(component.product_variant_id),
                            warning="Falta costo del componente externo",
                        ),
                    )
            estimate = payload.step_estimates.get(step.key)
            if estimate is None:
                if step.kind != RecipeStepKind.WAIT:
                    append(
                        step.key,
                        ResolvedCostItem(
                            category="step_estimate",
                            description=f"Estimación pendiente: {step.title}",
                            quantity=Decimal(1),
                            unit="step",
                            unit_cost=None,
                            currency=None,
                            source="unavailable",
                            warning=f"Falta estimación del paso {step.key}",
                        ),
                    )
                continue
            machine = costs._resolve_machine(estimate.machine_id)
            if step.kind == RecipeStepKind.PRINT and machine is None:
                raise InvalidRecipeError(
                    "La estimación de impresión requiere máquina y duración"
                )
            if machine is not None and step.kind in {
                RecipeStepKind.SERVICE,
                RecipeStepKind.WAIT,
            }:
                raise InvalidRecipeError("Service y wait no asignan máquina")
            if (
                machine is not None
                and step.kind == RecipeStepKind.PRINT
                and machine.machine_type
                != step.task_type.value.removesuffix("_print") + "_printer"
            ):
                raise InvalidRecipeError(
                    "La máquina no coincide con el tipo de impresión"
                )
            if machine is not None and not machine.active:
                raise InvalidRecipeError("La máquina debe estar activa")
            if (
                machine
                and step.required_machine_type
                and machine.machine_type != step.required_machine_type.value
            ):
                raise InvalidRecipeError("La máquina no coincide con el tipo requerido")
            for item in costs._resolve_machine_costs(estimate, machine, settings):
                append(step.key, item)
            for item in costs._resolve_labor(estimate, settings):
                append(step.key, item)
            for extra in estimate.extras:
                append(
                    step.key,
                    ResolvedCostItem(
                        category="extra",
                        description=extra.description,
                        quantity=Decimal(1),
                        unit="item",
                        unit_cost=extra.amount,
                        currency=extra.currency,
                        source="manual",
                        source_reference="manual",
                    ),
                )
        for supply_id, requested_quantity in requested_totals.items():
            if requested_quantity > costs._movements.stock(supply_id):
                warnings.append(f"Stock físico insuficiente para el insumo {supply_id}")
        totals: dict[str, Decimal] = {}
        for line in lines:
            if line.currency is not None and line.subtotal is not None:
                totals[line.currency] = (
                    totals.get(line.currency, Decimal(0)) + line.subtotal
                )
        complete = all(line.complete for line in lines)
        markup = (
            payload.markup_percentage
            if payload.markup_percentage is not None
            else settings.default_markup_percentage
        )
        suggested = None
        currency = None
        if complete and len(totals) == 1 and markup is not None:
            currency, total = next(iter(totals.items()))
            suggested = QuoteCalculator().calculate(total, markup, []).suggested_price
        preview = PricingPreviewRead(
            recipe_id=recipe.id,
            variant_id=variant.id,
            target_quantity=payload.target_quantity,
            strategy=payload.strategy,
            planned_steps=planned,
            omitted_step_keys=omitted,
            lines=lines,
            totals_by_currency=totals,
            complete=complete,
            multi_currency=len(totals) > 1,
            warnings=list(dict.fromkeys(warnings)),
            markup_percentage=markup,
            suggested_price=suggested,
            suggested_currency=currency,
        )
        return PricingEvaluation(
            preview=preview,
            plan=plan,
            configuration=configuration,
            product_id=product.id,
            product_name=product.name,
            variant_name=variant.name,
            variant_unit=variant.base_unit,
            recipe_name=recipe.name,
        )
