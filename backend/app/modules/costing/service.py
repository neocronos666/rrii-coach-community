import logging
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.exceptions import PersistenceError
from app.modules.costing.calculator import TechnicalCostCalculator
from app.modules.costing.exceptions import CostCalculationNotFoundError
from app.modules.costing.models import CostCalculation, CostCalculationLine
from app.modules.costing.preview_schemas import StepCostEstimate
from app.modules.costing.providers import (
    LastPurchaseSupplyCostProvider,
    SupplyCostProvider,
)
from app.modules.costing.repository import CostCalculationRepository
from app.modules.costing.schemas import (
    CostCalculationRead,
    CostCalculationRequest,
    CostCategory,
    CostLineRead,
    LaborType,
)
from app.modules.costing.types import CalculatedBreakdown, ResolvedCostItem
from app.modules.installation.schemas import InstallationSettings
from app.modules.installation.service import InstallationSettingsService
from app.modules.machines.exceptions import MachineNotFoundError
from app.modules.machines.models import Machine
from app.modules.machines.repository import MachineRepository
from app.modules.supplies.conversion import UnitConversionService
from app.modules.supplies.exceptions import SupplyNotFoundError
from app.modules.supplies.repository import (
    StockMovementRepository,
    SupplyPurchaseRepository,
    SupplyRepository,
)
from app.modules.supplies.schemas import SupplyCategory, SupplyUnit

logger = logging.getLogger(__name__)


class CostCalculationService:
    def __init__(
        self,
        session: Session,
        calculations: CostCalculationRepository | None = None,
        supply_costs: SupplyCostProvider | None = None,
        calculator: TechnicalCostCalculator | None = None,
    ) -> None:
        self._session = session
        self._calculations = calculations or CostCalculationRepository(session)
        self._supplies = SupplyRepository(session)
        self._movements = StockMovementRepository(session)
        self._machines = MachineRepository(session)
        self._settings = InstallationSettingsService(session)
        self._supply_costs = supply_costs or LastPurchaseSupplyCostProvider(
            SupplyPurchaseRepository(session)
        )
        self._calculator = calculator or TechnicalCostCalculator()

    def create(self, request: CostCalculationRequest) -> CostCalculationRead:
        try:
            settings = self._settings.get()
            items = self._resolve_supplies(request)
            machine = self._resolve_machine(request.machine_id)
            items.extend(self._resolve_machine_costs(request, machine, settings))
            items.extend(self._resolve_labor(request, settings))
            items.extend(self._resolve_extras(request))
            breakdown = self._calculator.calculate(items)
            calculation = self._persist(breakdown)
            self._session.commit()
            logger.info("cost_calculation_created calculation_id=%s", calculation.id)
            if breakdown.multi_currency:
                logger.info(
                    "multi_currency_calculation calculation_id=%s", calculation.id
                )
            return self._to_read(calculation)
        except (SupplyNotFoundError, MachineNotFoundError):
            self._session.rollback()
            raise
        except SQLAlchemyError as error:
            self._session.rollback()
            logger.error(
                "cost_calculation_failed (%s); rollback ejecutado",
                type(error).__name__,
            )
            raise PersistenceError("No se pudo guardar el cálculo") from error

    def get(self, calculation_id: UUID) -> CostCalculationRead:
        calculation = self._calculations.get(calculation_id)
        if calculation is None:
            raise CostCalculationNotFoundError("No existe el cálculo solicitado")
        return self._to_read(calculation)

    def _resolve_supplies(
        self, request: CostCalculationRequest
    ) -> list[ResolvedCostItem]:
        items: list[ResolvedCostItem] = []
        for requested in request.supplies:
            supply = self._supplies.get(requested.supply_id)
            if supply is None:
                raise SupplyNotFoundError("No existe el insumo solicitado")
            base_unit = SupplyUnit(supply.base_unit)
            quantity = UnitConversionService.convert(
                requested.quantity, requested.unit, base_unit
            )
            quote = self._supply_costs.get_unit_cost(supply.id, base_unit.value)
            warning: str | None = None
            if quote is None:
                warning = f"Costo no disponible para {supply.name}"
                logger.warning("cost_source_missing supply_id=%s", supply.id)
            available = self._movements.stock(supply.id)
            if quantity > available:
                stock_warning = (
                    f"Stock insuficiente para {supply.name}: "
                    f"solicitado {quantity} {base_unit.value}, "
                    f"disponible {available} {base_unit.value}"
                )
                warning = f"{warning}; {stock_warning}" if warning else stock_warning
                logger.warning("insufficient_stock_warning supply_id=%s", supply.id)
            items.append(
                ResolvedCostItem(
                    category=self._supply_cost_category(supply.category).value,
                    description=supply.name,
                    quantity=quantity,
                    unit=base_unit.value,
                    unit_cost=quote.amount if quote else None,
                    currency=quote.currency if quote else None,
                    source=quote.source if quote else "unavailable",
                    source_reference=quote.source_reference
                    if quote
                    else str(supply.id),
                    warning=warning,
                )
            )
        return items

    def _resolve_machine(self, machine_id: UUID | None) -> Machine | None:
        if machine_id is None:
            return None
        machine = self._machines.get(machine_id)
        if machine is None:
            raise MachineNotFoundError("No existe la máquina solicitada")
        return machine

    def _resolve_machine_costs(
        self,
        request: CostCalculationRequest | StepCostEstimate,
        machine: Machine | None,
        settings: InstallationSettings,
    ) -> list[ResolvedCostItem]:
        items: list[ResolvedCostItem] = []
        hours = (
            self._calculator.hours_from_minutes(request.machine_duration_minutes)
            if request.machine_duration_minutes is not None
            else None
        )
        if machine is not None and hours is not None:
            depreciation = None
            warning = None
            if machine.purchase_price is not None and machine.useful_life_hours:
                depreciation = self._calculator.basic_depreciation_hourly(
                    machine.purchase_price, machine.useful_life_hours
                )
            else:
                warning = f"Datos de depreciación incompletos para {machine.name}"
                logger.warning("cost_source_missing machine_id=%s", machine.id)
            items.append(
                ResolvedCostItem(
                    category=CostCategory.MACHINE_TIME.value,
                    description=f"Tiempo de máquina: {machine.name}",
                    quantity=hours,
                    unit="h",
                    unit_cost=depreciation,
                    currency=machine.currency if depreciation is not None else None,
                    source="basic_depreciation"
                    if depreciation is not None
                    else "unavailable",
                    source_reference=str(machine.id),
                    warning=warning,
                )
            )

        energy_kwh = request.energy_kwh
        energy_source = "manual"
        energy_reference: str | None = "manual"
        energy_warning: str | None = None
        if energy_kwh is None and machine is not None and hours is not None:
            energy_source = "rated_power_estimate"
            energy_reference = str(machine.id)
            if machine.rated_power_w is not None:
                energy_kwh = self._calculator.estimated_energy_kwh(
                    machine.rated_power_w, hours
                )
            else:
                energy_kwh = Decimal(0)
                energy_warning = f"Potencia nominal no configurada para {machine.name}"
        if energy_kwh is not None:
            rate = settings.electricity_price_per_kwh
            if energy_source == "rated_power_estimate" and energy_warning is not None:
                rate = None
            if rate is None:
                missing = "Tarifa eléctrica no configurada"
                energy_warning = (
                    f"{energy_warning}; {missing}" if energy_warning else missing
                )
                logger.warning("cost_source_missing source=electricity_rate")
            items.append(
                ResolvedCostItem(
                    category=CostCategory.ENERGY.value,
                    description="Electricidad estimada",
                    quantity=energy_kwh,
                    unit="kWh",
                    unit_cost=rate,
                    currency=settings.currency if rate is not None else None,
                    source=energy_source if rate is not None else "unavailable",
                    source_reference=energy_reference,
                    warning=energy_warning,
                )
            )
        return items

    def _resolve_labor(
        self,
        request: CostCalculationRequest | StepCostEstimate,
        settings: InstallationSettings,
    ) -> list[ResolvedCostItem]:
        items: list[ResolvedCostItem] = []
        for labor in request.labor:
            category, description, rate = self._labor_config(labor.labor_type, settings)
            warning = None
            if rate is None:
                warning = f"Tarifa de {description.lower()} no configurada"
                logger.warning("cost_source_missing labor_type=%s", labor.labor_type)
            items.append(
                ResolvedCostItem(
                    category=category.value,
                    description=description,
                    quantity=self._calculator.hours_from_minutes(
                        labor.duration_minutes
                    ),
                    unit="h",
                    unit_cost=rate,
                    currency=settings.currency if rate is not None else None,
                    source="installation_settings"
                    if rate is not None
                    else "unavailable",
                    source_reference="community.installation_settings",
                    warning=warning,
                )
            )
        return items

    def _resolve_extras(
        self, request: CostCalculationRequest
    ) -> list[ResolvedCostItem]:
        return [
            ResolvedCostItem(
                category=CostCategory.EXTRA.value,
                description=extra.description,
                quantity=Decimal(1),
                unit="item",
                unit_cost=extra.amount,
                currency=extra.currency,
                source="manual",
                source_reference="manual",
            )
            for extra in request.extras
        ]

    def _persist(self, breakdown: CalculatedBreakdown) -> CostCalculation:
        calculation = CostCalculation(
            calculation_type="technical",
            complete=breakdown.complete,
            multi_currency=breakdown.multi_currency,
            warnings=list(breakdown.warnings),
            calculated_at=datetime.now(UTC),
        )
        calculation.lines = [
            CostCalculationLine(
                position=position,
                category=line.category,
                description=line.description,
                quantity=line.quantity,
                unit=line.unit,
                unit_cost=line.unit_cost,
                currency=line.currency,
                subtotal=line.subtotal,
                source=line.source,
                source_reference=line.source_reference,
                complete=line.complete,
            )
            for position, line in enumerate(breakdown.lines)
        ]
        return self._calculations.add(calculation)

    def _to_read(self, calculation: CostCalculation) -> CostCalculationRead:
        lines = [CostLineRead.model_validate(line) for line in calculation.lines]
        totals: dict[str, Decimal] = {}
        for line in lines:
            if line.currency is not None and line.subtotal is not None:
                totals[line.currency] = (
                    totals.get(line.currency, Decimal(0)) + line.subtotal
                )
        return CostCalculationRead(
            id=calculation.id,
            calculation_type=calculation.calculation_type,
            demand_quantity=calculation.demand_quantity,
            demand_unit=calculation.demand_unit,
            complete=calculation.complete,
            multi_currency=calculation.multi_currency,
            lines=lines,
            totals_by_currency=totals,
            warnings=list(calculation.warnings),
            calculated_at=calculation.calculated_at,
            created_at=calculation.created_at,
        )

    @staticmethod
    def _supply_cost_category(category: str) -> CostCategory:
        mapping = {
            SupplyCategory.MATERIAL.value: CostCategory.MATERIAL,
            SupplyCategory.COMPONENT.value: CostCategory.COMPONENT,
            SupplyCategory.CONSUMABLE.value: CostCategory.CONSUMABLE,
            SupplyCategory.PACKAGING.value: CostCategory.PACKAGING,
            SupplyCategory.SPARE_PART.value: CostCategory.COMPONENT,
            SupplyCategory.MERCHANDISE.value: CostCategory.COMPONENT,
            SupplyCategory.OTHER.value: CostCategory.EXTRA,
        }
        return mapping[category]

    @staticmethod
    def _labor_config(
        labor_type: LaborType, settings: InstallationSettings
    ) -> tuple[CostCategory, str, Decimal | None]:
        if labor_type is LaborType.DESIGN:
            return CostCategory.DESIGN_LABOR, "Diseño", settings.design_hour_rate
        if labor_type is LaborType.PREPRODUCTION:
            return (
                CostCategory.PREPRODUCTION_LABOR,
                "Preproducción",
                settings.preproduction_hour_rate,
            )
        if labor_type is LaborType.POSTPRODUCTION:
            return (
                CostCategory.POSTPRODUCTION_LABOR,
                "Posproducción",
                settings.postproduction_hour_rate,
            )
        if labor_type is LaborType.ASSEMBLY:
            return (
                CostCategory.ASSEMBLY_LABOR,
                "Ensamblaje",
                settings.assembly_hour_rate,
            )
        if labor_type is LaborType.SUPPORT:
            return CostCategory.SUPPORT_LABOR, "Soporte", settings.support_hour_rate
        if labor_type is LaborType.TRAINING:
            return (
                CostCategory.TRAINING_LABOR,
                "Capacitación",
                settings.training_hour_rate,
            )
        return (
            CostCategory.PRETRANSPORT,
            "Pretransporte",
            settings.pretransport_hour_rate,
        )
