"""Registro explícito de modelos para la metadata de Alembic."""

from app.db.models.system_setting import SystemSetting
from app.modules.assets.file_models import AssetRevisionFile, StoredFile
from app.modules.assets.models import Asset, AssetCategory, AssetRevision
from app.modules.assets.structure_models import (
    AssetCompatibility,
    AssetCompositionComponent,
    AssetFamily,
)
from app.modules.costing.models import CostCalculation, CostCalculationLine
from app.modules.machines.models import Machine
from app.modules.options.configuration_models import ProductOption, ProductOptionValue
from app.modules.options.models import OptionDefinition, OptionValue
from app.modules.orders.models import Order
from app.modules.production.models import (
    ProductionTask,
    ProductionTaskAssetRevision,
    ProductionTaskDependency,
)
from app.modules.production.plan_models import ProductionPlan
from app.modules.production.run_models import ProductionRun
from app.modules.production.test_print_models import (
    TestPrint,
    TestPrintAssetRevision,
    TestPrintStep,
)
from app.modules.products.allocation_models import ProductStockAllocation
from app.modules.products.consumption_models import ProductionRunProductConsumption
from app.modules.products.models import Product, ProductVariant
from app.modules.products.stock_models import ProductStockMovement
from app.modules.projects.models import Project, ProjectComponent
from app.modules.quick_quotes.formalization_models import QuickQuoteFormalization
from app.modules.quick_quotes.models import QuickQuote, QuickQuoteRevision
from app.modules.quotes.conversion_models import QuoteConversion
from app.modules.quotes.models import Quote, QuoteAdjustment, QuoteItem
from app.modules.recipes.models import (
    Recipe,
    RecipeProductInput,
    RecipeSelectedSupplyInput,
    RecipeStep,
    RecipeStepDependency,
    RecipeStepResource,
    RecipeSupplyInput,
)
from app.modules.recipes.service_models import ServiceDefinition
from app.modules.supplies.consumption_models import ProductionRunSupplyConsumption
from app.modules.supplies.models import (
    Supply,
    SupplyPresentation,
    SupplyPurchase,
    SupplyStockMovement,
)
from app.modules.supplies.reservation_models import SupplyReservation

__all__ = [
    "Asset",
    "AssetCategory",
    "AssetCompatibility",
    "AssetCompositionComponent",
    "AssetFamily",
    "AssetRevision",
    "AssetRevisionFile",
    "CostCalculation",
    "CostCalculationLine",
    "Machine",
    "OptionDefinition",
    "OptionValue",
    "Order",
    "Product",
    "ProductOption",
    "ProductOptionValue",
    "ProductStockAllocation",
    "ProductStockMovement",
    "ProductVariant",
    "ProductionPlan",
    "ProductionRun",
    "ProductionRunProductConsumption",
    "ProductionRunSupplyConsumption",
    "ProductionTask",
    "ProductionTaskAssetRevision",
    "ProductionTaskDependency",
    "Project",
    "ProjectComponent",
    "QuickQuote",
    "QuickQuoteFormalization",
    "QuickQuoteRevision",
    "Quote",
    "QuoteAdjustment",
    "QuoteConversion",
    "QuoteItem",
    "Recipe",
    "RecipeProductInput",
    "RecipeSelectedSupplyInput",
    "RecipeStep",
    "RecipeStepDependency",
    "RecipeStepResource",
    "RecipeSupplyInput",
    "ServiceDefinition",
    "StoredFile",
    "Supply",
    "SupplyPresentation",
    "SupplyPurchase",
    "SupplyReservation",
    "SupplyStockMovement",
    "SystemSetting",
    "TestPrint",
    "TestPrintAssetRevision",
    "TestPrintStep",
]
