# Relaciones principales de Community

Este esquema resume relaciones actuales. No sustituye los modelos SQLAlchemy ni
las restricciones instaladas por las migraciones Alembic.

```text
Product → ProductVariant
Product → ProductOption → OptionDefinition / OptionValue
Recipe → RecipeStep → dependencias, inputs y recursos

AssetFamily ← Asset → AssetCategory
Asset → AssetRevision → AssetRevisionFile → StoredFile
AssetRevision → composición
Asset → compatibilidades

QuickQuote → QuickQuoteRevision → formalización explícita → Quote
CostCalculation → CostCalculationLine
Quote → QuoteItem → CostCalculation
Quote → QuoteAdjustment
Quote → QuoteConversion → Order
Quote → QuoteConversion → Project → ProjectComponent

Order o ProjectComponent → ProductionTask → ProductionRun
ProductionTask → ProductionTaskDependency
TestPrint → TestPrintStep → ProductionRun

Supply → SupplyPurchase / SupplyPresentation / SupplyStockMovement
ProductionTask → SupplyReservation
ProductionRun → consumos de insumos y productos
ProductVariant → ProductStockMovement / ProductStockAllocation
```

Los orígenes de ProductionTask y ProductionRun son exclusivos: no se asigna una
misma tarea a pedido y componente, ni un Run a tarea y paso experimental.
Las dependencias son DAG y se validan antes de iniciar ejecución.

No existe una raíz Organization ni entidades de identidad, depósitos o
telemetría. Los stocks se derivan de movimientos. Los detalles de fuentes y
vínculos están documentados en [módulos](../modules/).
