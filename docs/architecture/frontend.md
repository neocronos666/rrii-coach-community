# Arquitectura del frontend — 10A, 10B y continuidad comercial

La SPA Community ofrece un shell responsive y un [dashboard conectado](../modules/dashboard_live_ui_es.md) personalizable. La demostración inicial de 10A fue sustituida por registros reales en el cierre del frontend. El backend conserva las reglas de negocio.

10B incorpora una Biblioteca de Assets conectada a la API real: listado, alta
básica, revisiones, archivos y miniaturas. El dashboard actual consulta los dominios operativos.
El alcance y la validación están en [Biblioteca](../modules/asset_library_ui_es.md).
El catálogo de [Producto, opciones y receta](../modules/product_editor_ui_es.md)
también usa la API real, con borradores locales separados del estado remoto y
resolución de prueba calculada exclusivamente en backend.
[Quick Quote](../modules/quick_quote_ui_es.md) agrega preview, borradores con
historial y formalización única; el Quote formal se consulta sin recalcular costos.
[Test print](../modules/test_print_ui_es.md) ejecuta pruebas de receta completa
desde la variante, con intentos, consumos y promoción explícita a stock.
La [continuidad comercial](../modules/commercial_ui_es.md) incorpora edición de
borradores formales, aprobación/rechazo, conversión explícita y consulta/cancelación
de pedidos y proyectos. Todas las transiciones se resuelven por API.
La [producción comercial](../modules/production_ui_es.md) conecta esos destinos
con planes de receta, cola, prerrequisitos, intentos, consumos y stock de salida.
[Compras e inventario](../modules/inventory_ui_es.md) agrega insumos, compras,
ajustes, reservas y asignaciones/entregas explícitas. Las escrituras sin clave
idempotente conservan un aviso de revisión ante respuestas inciertas y no se
reenvían automáticamente.

La [administración de máquinas](../modules/machines_ui_es.md) agrega catálogo,
alta, edición y activación/desactivación con límite validado por backend.

La [configuración de instalación](../modules/installation_ui_es.md) expone los
parámetros funcionales completos, con revisión explícita de cambios y resultados
inciertos. Se distingue de las preferencias de apariencia del navegador.

El [catálogo de servicios](../modules/services_ui_es.md) permite editar servicios
compartidos y probar sus frases guardadas mediante el backend, sin renderizado
local de plantillas.

La [administración global de opciones](../modules/options_ui_es.md) agrega edición
de características/valores y vínculos opcionales, conservando la configuración
específica de cada producto en su editor existente.

La [estructura de Assets](../modules/asset_structure_ui_es.md) incorpora familias,
compatibilidades positivas y composición con revisiones hijas fijadas. Publicar
crea una revisión nueva por API y conserva los archivos del padre.

La [edición de datos de Assets y categorías](../modules/asset_details_ui_es.md)
completa la metadata actual con PATCH parcial, preservando revisiones y archivos.
La eliminación de categoría exige confirmación de reasignación al respaldo.

La [composición comercial independiente](../modules/quote_composition_ui_es.md)
permite cálculos técnicos y Quotes de varios ítems. La [producción avanzada](../modules/production_editor_ui_es.md)
incorpora tareas manuales, edición, dependencias y opciones de ejecución.

## Stack y organización

Nuxt 4, Vue 3, TypeScript estricto, `ssr: false`, Nuxt UI y Tailwind. Se conserva
TanStack Query para el estado remoto de Biblioteca, Productos y presupuestos, Pinia cuando el estado UI lo requiera,
Zod, openapi-fetch y contratos generados. No se crean stores ni queries vacíos.
Las preferencias actuales usan `useState`/estado Vue; no duplican estado remoto.

| Zona | Responsabilidad |
| --- | --- |
| `app/components/shell` | Navegación, apariencia, perfiles y launcher global |
| `app/features/preferences` | Contrato versionado de dispositivo |
| `app/features/launcher` | Catálogo de acciones y preferencias del launcher |
| `app/features/dashboard` | Consultas API, vistas y preferencias de bloques |
| `app/features/assets` | Cliente tipado de la API de Assets |
| `app/pages/assets` | Listado y detalle por revisión con TanStack Query |
| `app/features/products` | Clientes, formularios de configuración/receta y proyección de contratos |
| `app/features/shared` | Errores HTTP, paginación, reintentos persistidos y aviso de borradores |
| `app/features/test-prints`, `app/pages/test-prints` | Pruebas completas, intentos, consumos y promoción |
| `app/features/quick-quotes` | Contratos comerciales, formularios, snapshots y reintentos de escrituras |
| `app/pages/quick-quotes`, `app/pages/quotes` | Borradores, historial, formalización y consulta del Quote |
| `app/features/production`, `app/pages/production` | Planes desde destinos, cola, dependencias y ejecuciones comerciales |
| `app/features/asset-details`, `app/pages/asset-details`, `app/pages/asset-categories` | Metadata de Assets y categorías personalizadas |
| `app/features/asset-structure`, `app/pages/asset-structure`, `app/pages/families` | Familias, compatibilidades y composición por revisión |
| `app/features/options`, `app/pages/options` | Características, valores y vínculos con familias/insumos |
| `app/features/services`, `app/pages/services` | Catálogo de servicios, edición y preview contextual |
| `app/features/installation`, `app/pages/settings.vue` | Configuración compartida de instalación, seña y costos |
| `app/features/machines`, `app/pages/machines` | Catálogo de equipos, edición parcial y vínculo a producción |
| `app/features/inventory`, `app/pages/inventory` | Insumos, compras, stock, reservas, asignaciones y entregas |
| `app/features/commercial`, `app/pages/orders`, `app/pages/projects` | Edición comercial, transiciones y snapshots de pedidos/proyectos |
| `app/pages/products` | Catálogo físico, variantes y coordinación del editor |
| `app/theme/skin.ts` | Contrato interno de skin y fallback de perfiles |
| `app/assets/css/tokens.css` | Tokens semánticos y mapeo a Nuxt UI |
| `app/assets/css/main.css` | Layout, componentes y adaptación responsive |
| `app/i18n/es.ts` | Catálogo castellano tipado, incluidos estados técnicos |
| `app/i18n/products.ts` | Textos tipados del editor de producto y receta |
| `app/i18n/quick-quotes.ts` | Textos tipados de presupuestos rápidos y formales |
| `app/composables/useI18n.ts` | Resolución centralizada de claves de producto |
| `app/types/api.generated.ts` | Contratos generados; nunca editar a mano |

Nuxt UI proporciona menús, paneles, diálogos, botones y toast. No se crean
wrappers que sólo renombran sus componentes. No hay autenticación, usuarios
ficticios ni capacidades fuera del alcance Community.

## Apariencia, skin y perfiles

Nebula utiliza dark inicial y light explícito, con color mode de Nuxt. No toma
la preferencia del sistema como default. Los componentes consumen tokens
semánticos para fondos, superficies, texto, bordes, estados, radios y movimiento.
Se ajustaron el verde light y los textos secundarios para contraste legible.

El contrato de skin define overrides parciales por perfil. `resolveProfile`
hereda del sistema y finalmente de desktop si faltan datos. Los tokens base CSS
son el fallback visual. No hay formato de terceros ni motor arbitrario de skins.
La configuración de bloques es independiente de la apariencia y del perfil.

- Automático: mobile con ancho menor a 768 px, touch con puntero principal grueso
  en pantallas mayores, desktop en los demás casos.
- Mobile forzado: navegación inferior también en una pantalla grande.
- Desktop forzado: navegación lateral, compactada si el espacio es estrecho.
- Touch: targets de 52 px, mayor separación y navegación según espacio.
- Densidad cómoda inicial; compacta ajusta desktop sin achicar targets mínimos.

El launcher permanece en la topbar sticky, también en mobile, para no cubrir
filas. Navegación inferior contempla safe areas y espacio de contenido final.

## Preferencias locales

| Clave localStorage | Contenido |
| --- | --- |
| `rrii-coach.appearance.v1` | `dark` o `light` |
| `rrii-coach.device.v1` | Perfil y densidad |
| `rrii-coach.launcher.v1` | Visibilidad y orden de acciones |
| `rrii-coach.dashboard.v1` | Visibilidad, orden, tamaño y vista de bloques |

Se validan los documentos con Zod, se recuperan valores inválidos con defaults
y se normalizan duplicados/vistas incompatibles. El almacenamiento bloqueado no
impide usar la UI: los cambios se mantienen en memoria y se informa en los
paneles de preferencias. Son preferencias del navegador y origen, sin sincronizar
con backend ni entre dispositivos. No se guardan secretos ni datos de negocio.

Personalizar el launcher sigue disponible incluso sin acciones visibles.
El dashboard permite ocultar todos los bloques y recuperarlos desde su estado
vacío. Restablecer distribución vuelve a producción, presupuestos, atención y
actividad; máquinas queda oculto. No hay redimensionado libre.

## Idioma y datos conectados

Los textos de producto se resuelven por claves tipadas. Nuxt UI usa locale es.
La base sólo incluye castellano: no hay selector de idioma ni traducciones
adicionales prometidas. Los estados técnicos conservan nombres como
`in_progress`; la traducción se realiza en frontend.

El dashboard usa adaptadores tipados y TanStack Query; se retiró `demo.ts` al
conectar los bloques con registros reales. Los importes se conservan como cadenas,
sin cálculos monetarios. Los estados de carga, vacío y error se distinguen por bloque.

## Validación

Vitest valida preferencias, normalización y recuperación. Playwright valida
recorridos sobre la compilación de producción, personalización, teclado,
responsive y persistencia. Axe complementa la revisión visual y de teclado;
no sustituye una evaluación con usuarios o tecnologías de asistencia reales.

Desde `frontend`, con Node 24 y pnpm 11:

```bash
pnpm install --frozen-lockfile
pnpm test
pnpm lint
pnpm typecheck
pnpm build
```

Para E2E reproducibles, ejecutar `./scripts/check-local.sh` desde la raíz.
El ejecutor configura API, CORS, base aislada y proyectos Chromium explícitos;
ver [calidad](../development/quality_es.md). Una ejecución directa requiere
`RRII_E2E_API_BASE`, sin omisiones silenciosas.

El script lint heredado ejecuta `nuxt typecheck`; no se presenta como ESLint.
Para desarrollo: `pnpm dev`. E2E usa el puerto 3100 y guarda capturas/trazas en
`test-results` (no versionadas). Los iconos se incluyen en el bundle y no
requieren un servicio externo durante el uso de la aplicación.
