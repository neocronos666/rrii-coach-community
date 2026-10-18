# Datos de Assets y categorías personalizadas

Desde un Asset, «Editar datos del Asset» abre `/asset-details/{id}`. Modifica
metadata actual: nombre, descripción, categoría, familia, terceros, autor,
origen, licencia, URL, notas de uso y archivado. Código, revisión actual y campos
de auditoría no se envían. PATCH contiene sólo diferencias; vacíos opcionales
son null. Categoría sigue obligatoria. La API valida URL y referencias.

Guardar metadata no crea revisiones ni cambia archivos/composición. Información
sobre autoría/licencia es descriptiva; no incorpora validación jurídica. El detalle
«Datos guardados» permite revisar el estado remoto sin sobrescribir el borrador.
Se conserva la protección al navegar con cambios. Después de guardar se adopta la
respuesta normalizada del servidor como nueva base de comparación.

Biblioteca → Administrar categorías abre `/asset-categories`; alta en
`/asset-categories/new`, renombrado/eliminación en `/asset-categories/{id}`.
El listado recorre todas las páginas. No existe endpoint GET individual: el
detalle se obtiene del catálogo, sin inventar contratos.

La categoría de sistema identificada por system_key es protegida: la UI la
muestra sin acciones habilitadas, y el backend conserva la validación efectiva.
Eliminar una personalizada requiere confirmación que explica la reasignación a
la categoría de respaldo. No elimina Assets, revisiones ni archivos.

Escrituras inciertas no se reenvían automáticamente. El aviso persiste por pestaña
con scope propio; en eliminación sigue visible aunque el catálogo actualizado
ya no contenga la categoría, también después de recargar. La ausencia no provoca
un segundo DELETE ni recrea el registro. Se consultan los registros para revisar.
Con almacenamiento bloqueado el aviso sólo persiste en memoria y se informa.
No se garantiza concurrencia entre pestañas ni existe ETag en estos contratos.

Se conservan el alta básica y los flujos ya validados de Biblioteca. Sin cambios
de backend, esquema, OpenAPI, dependencias ni servicios principales.
