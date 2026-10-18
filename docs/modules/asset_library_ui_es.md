# Biblioteca de Assets — interfaz Community

La Biblioteca se abre desde la barra lateral o desde «Más» en móvil. Consume
la API configurada en `NUXT_PUBLIC_API_BASE_URL`, incluida su terminación
`/api/v1`. El servidor debe permitir el origen del frontend mediante CORS.

## Recorrido

- `/assets`: búsqueda, filtro de archivados, paginación y alta básica con nombre,
  descripción y categoría existente. La categoría vacía delega el default al backend.
- `/assets/{id}`: revisión actual o histórica, nota, archivos, descargas y
  miniatura de la revisión elegida. Crear una revisión comienza sin archivos;
  restaurar crea otra revisión conservando las referencias de la original.
- Adjuntar envía bytes originales y el rol elegido. El backend valida formatos,
  límites, nombres, conflictos y normalización de thumbnails. La UI conserva
  la selección ante errores y explica que un adjunto no se reemplaza.
- Comparar presenta las diferencias calculadas por la API entre la revisión
  seleccionada y la elegida como destino. Archivar y reactivar preservan la historia.

El cliente usa contratos OpenAPI generados y TanStack Query para carga,
invalidación y recuperación explícita de errores. No calcula diferencias ni
aplica reglas de archivos en el navegador. Las miniaturas se muestran en el
detalle, después de comprobar su existencia en los metadatos de archivos.

El incremento original se limitaba a Biblioteca. La continuidad ya incorpora
[datos y atribución de terceros](asset_details_ui_es.md), categorías,
[estructura/familias](asset_structure_ui_es.md), [Productos](product_editor_ui_es.md),
[Quick Quote](quick_quote_ui_es.md) y [Test Print](test_print_ui_es.md). El alta
básica conserva `third_party: false`; la atribución se edita desde los datos del Asset.

## Validación reproducible

Usar una API con PostgreSQL y almacenamiento de archivos **aislados**: las pruebas
crean recursos, adjuntan archivos, restauran revisiones y archivan los recursos.
No ejecutar fixtures backend que vacían la base durante Playwright.

Desde `frontend`, con Node 24, pnpm 11 y Chromium instalado:

```bash
pnpm test
pnpm typecheck
pnpm lint
NUXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8100/api/v1 pnpm build
NUXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8100/api/v1 RRII_E2E_API_BASE=http://127.0.0.1:8100/api/v1 PLAYWRIGHT_PREVIEW=1 CI=1 pnpm exec playwright test --workers=1
```

Autorizar `http://127.0.0.1:3100` en CORS de esa API. Si se usan contenedores,
reemplazar la dirección de ejemplo por una accesible desde Chromium y configurar
`PLAYWRIGHT_BROWSERS_PATH` cuando los navegadores estén fuera del directorio habitual.
Sin `RRII_E2E_API_BASE`, la configuración falla antes de ejecutar casos.
Para el cierre reproducible usar [el ejecutor aislado](../development/quality_es.md).

Las pruebas cubren subida binaria, errores, paginación de revisiones y filtros
en Vitest; el recorrido persistente con API real, descarga, miniatura, conflicto,
comparación, restauración, archivo, teclado y error recuperable en Playwright.
Axe comprueba móvil de 360 px y escritorio de 1440 px, claro y oscuro; las capturas
quedan en `test-results`, fuera de Git. Axe no sustituye pruebas con usuarios.

## Continuidad de catálogo

La [edición completa de datos y categorías](asset_details_ui_es.md) y la
[estructura por revisión](asset_structure_ui_es.md) están disponibles mediante
enlaces desde Biblioteca, conservando los flujos de archivos/revisiones existentes.
