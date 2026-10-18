# Entidades implementadas

Este catálogo resume los modelos actuales; el contrato de cada operación está
publicado en OpenAPI y en [módulos](../modules/). No es una lista de funciones
futuras.

| Dominio | Entidades principales |
| --- | --- |
| Instalación | `SystemSetting`, utilizado por el servicio tipado de configuración |
| Máquinas | `Machine` |
| Assets | `AssetCategory`, `Asset`, `AssetFamily`, `AssetRevision`, `StoredFile`, `AssetRevisionFile`, `AssetCompatibility`, `AssetCompositionComponent` |
| Productos | `Product`, `ProductVariant`, `OptionDefinition`, `OptionValue`, `ProductOption`, `ProductOptionValue` |
| Recetas | `Recipe`, `RecipeStep`, dependencias, recursos e inputs de insumos/productos |
| Servicios | `ServiceDefinition` |
| Insumos | `Supply`, `SupplyPresentation`, `SupplyPurchase`, `SupplyStockMovement`, `SupplyReservation` |
| Costos | `CostCalculation`, `CostCalculationLine` |
| Quick Quote | `QuickQuote`, `QuickQuoteRevision` |
| Presupuestos | `Quote`, `QuoteItem`, `QuoteAdjustment`, `QuoteConversion` |
| Destinos operativos | `Order`, `Project`, `ProjectComponent` |
| Producción | `ProductionPlan`, `ProductionTask`, `ProductionTaskDependency`, `ProductionRun` y registros de consumo |
| Pruebas de receta | `TestPrint`, `TestPrintStep` |
| Productos en stock | `ProductStockMovement`, `ProductStockAllocation` |

No hay entidades de usuarios, organizaciones, depósitos, dispositivos, facturas,
encuestas de calidad ni telemetría. Las revisiones, snapshots y movimientos
existentes proporcionan la trazabilidad documentada por cada módulo.
