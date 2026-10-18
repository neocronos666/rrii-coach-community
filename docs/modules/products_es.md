# Catálogo físico

Product agrupa identidades físicas ProductVariant. La creación de un producto
incluye su primera variante en una transacción. El catálogo no depende de
fabricación, recetas ni stock. No representa servicios.

Las variantes tienen UUID, nombre, SKU opcional normalizado a mayúsculas, unidad
base inmutable y atributos descriptivos de texto. Cambiar la especificación
física requiere una variante nueva. La máquina y el método de abastecimiento
no forman parte obligatoria de la identidad. No hay borrado por API.

Desactivar un producto no modifica sus variantes. Para nuevas operaciones deben
estar activos ambos. El SKU permanece reservado después de desactivar.

API: POST/GET /products, GET/PATCH /products/{id}, POST/GET
/products/{id}/variants, GET/PATCH /product-variants/{id}, bajo /api/v1.
Listados con offset >= 0 y limit entre 1 y 100; productos admiten search y active,
variantes admiten active. La búsqueda trata comodines como texto literal.

No se duplica stock de Supply. El [stock de productos](product_stock_es.md) tiene su propio ledger.
Las [recetas](recipes_es.md) declaran inputs y recursos de fabricación.
