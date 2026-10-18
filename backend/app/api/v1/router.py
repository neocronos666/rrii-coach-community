from fastapi import APIRouter

from app.api.health import health, readiness
from app.modules.assets.file_router import router as asset_files_router
from app.modules.assets.router import router as assets_router
from app.modules.assets.structure_router import router as asset_structure_router
from app.modules.costing.preview_router import router as pricing_preview_router
from app.modules.costing.router import router as costing_router
from app.modules.installation.router import router as installation_router
from app.modules.machines.router import router as machines_router
from app.modules.options.configuration_router import router as configuration_router
from app.modules.options.router import router as options_router
from app.modules.orders.router import router as orders_router
from app.modules.production.plan_router import router as plans_router
from app.modules.production.router import router as production_router
from app.modules.production.run_router import router as runs_router
from app.modules.production.test_print_router import router as test_prints_router
from app.modules.products.allocation_router import router as allocations_router
from app.modules.products.router import router as products_router
from app.modules.products.stock_router import router as product_stock_router
from app.modules.projects.router import router as projects_router
from app.modules.quick_quotes.router import router as quick_quotes_router
from app.modules.quotes.router import router as quotes_router
from app.modules.recipes.router import router as recipes_router
from app.modules.recipes.service_router import router as service_definitions_router
from app.modules.supplies.reservation_router import router as reservations_router
from app.modules.supplies.router import router as supplies_router
from app.schemas.health import HealthResponse, ReadinessResponse

router = APIRouter()

router.add_api_route(
    "/health",
    health,
    methods=["GET"],
    response_model=HealthResponse,
    tags=["health"],
)
router.add_api_route(
    "/ready",
    readiness,
    methods=["GET"],
    response_model=ReadinessResponse,
    tags=["health"],
)
router.include_router(installation_router)
router.include_router(machines_router)
router.include_router(supplies_router)
router.include_router(costing_router)
router.include_router(quotes_router)
router.include_router(orders_router)
router.include_router(projects_router)
router.include_router(production_router)

router.include_router(products_router)

router.include_router(recipes_router)

router.include_router(runs_router)

router.include_router(reservations_router)

router.include_router(product_stock_router)

router.include_router(allocations_router)

router.include_router(plans_router)

router.include_router(assets_router)

router.include_router(asset_files_router)

router.include_router(asset_structure_router)

router.include_router(options_router)

router.include_router(configuration_router)

router.include_router(service_definitions_router)
router.include_router(test_prints_router)

router.include_router(pricing_preview_router)

router.include_router(quick_quotes_router)
