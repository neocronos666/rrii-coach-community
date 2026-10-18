# Producto, opciones y receta — interfaz Community

`/products` reemplaza el placeholder por un catálogo conectado a la API. Desde
allí se crea un producto junto con su primera variante; el detalle permite
editar el producto, su actividad y sus variantes. La unidad de una variante
existente permanece inmutable. SKU y atributos descriptivos se guardan mediante
los contratos de catálogo. Desactivar no borra historia ni modifica otras filas.

## Opciones

El editor declara las características del producto, sus valores permitidos,
mínimos/máximos, cantidades por defecto y contexto fijo o desde otra
característica. Guardar envía la configuración completa; el backend decide si
es válida y realiza el reemplazo atómico. Un error conserva el borrador visible.

Se pueden crear características y valores reutilizables sin salir del producto.
Los valores pueden enlazar familias e insumos ya existentes. La [administración global de opciones y valores](options_ui_es.md) permite
editar nombres, descripciones, actividad y vínculos fuera del producto.
Compatibilidades, familias y composición de Assets se administran desde la
[interfaz de estructura](asset_structure_ui_es.md). Los elementos inactivos existentes permanecen identificables; la API
valida su utilización al guardar o resolver.

## Receta base

El editor crea o edita la única receta base del producto. No cambia las recetas
heredadas ligadas a variantes. Permite editar pasos de operación, impresión,
servicio y espera, tipo de tarea, cantidades, unidad, salida final/intermedia,
requisito de máquina, instrucciones, dependencias, condiciones y escala por
selección. La máquina física se elige al planificar, fuera de este recorrido.

Cada paso permite revisiones fijas de Assets o recursos desde opciones,
materiales fijos/dinámicos y productos consumidos con proveedor opcional. Las
referencias de revisión no se actualizan silenciosamente. Los servicios se
seleccionan del catálogo y pueden crearse en el editor; su administración global
y preview contextual están en [Servicios reutilizables](services_ui_es.md); los campos explícitos
vacíos dejan actuar al contexto automático del backend. El usuario puede
proporcionar textos explícitos con precedencia.

La proyección de lectura a escritura retira identidad y campos resueltos, conserva
parámetros técnicos arbitrarios existentes y mantiene cantidades como cadenas.
Los parámetros se muestran como información conservada; su edición continúa por
API. No se implementan fórmulas, ordenamiento de DAG, compatibilidades, consumos
ni cálculo de cantidades en el navegador. Renombrar o quitar un paso no reescribe
sus referencias automáticamente: la API rechaza dependencias incoherentes.

## Probar la configuración

La sección final usa la configuración y receta **guardadas**. Se elige variante,
cantidad y, para cada característica, defaults o selección explícita. Una
selección explícita puede quedar vacía: no equivale a omitirla y aplicar defaults.
El resultado muestra pasos activos, omitidos, demanda, lotes, capacidad, recursos,
materiales y frase del servicio devueltos por la API. Cambiar los controles o
guardar producto/configuración/receta retira el resultado anterior.

Resolver no guarda Quote, producción ni stock. Quick Quote, formalización y Test
print ya tienen pantallas propias (ver sus módulos). Un error de receta ausente se distingue
de un fallo de servidor: sólo 404 habilita el alta de receta base.

## Estado local y navegación

TanStack Query mantiene el estado remoto. Los formularios conservan un borrador
separado; una recarga automática de datos no reemplaza cambios sin guardar.
Las operaciones deshabilitan su formulario mientras se envían. Al abandonar la
ruta con cambios del producto, variante, configuración o plan se solicita
confirmación; recargar/cerrar la pestaña utiliza el aviso nativo del navegador.
Esto no constituye almacenamiento persistente de borradores.

Los catálogos de referencia se cargan con toda su paginación; el endpoint de
insumos devuelve su lista completa sin offset. Variantes y revisiones se
consultan cuando se elige su producto o Asset. Los textos se centralizan en
`app/i18n/products.ts`, con contratos tipados. No se agregaron dependencias.

## Verificación

Usar Node 24/pnpm 11, una API con PostgreSQL y almacenamiento aislados y CORS
para `http://127.0.0.1:3100`. Nunca apuntar estas pruebas a datos comerciales:
crean productos, variantes, características, servicios, familias, Assets e insumos.
No ejecutar limpieza de fixtures backend durante Playwright.

```bash
pnpm test
pnpm typecheck
pnpm lint
NUXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8100/api/v1 pnpm build
NUXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8100/api/v1 RRII_E2E_API_BASE=http://127.0.0.1:8100/api/v1 PLAYWRIGHT_PREVIEW=1 CI=1 pnpm exec playwright test --workers=1
```

En contenedores, reemplazar la dirección por la accesible desde Chromium y
configurar `PLAYWRIGHT_BROWSERS_PATH` si corresponde. Sin `RRII_E2E_API_BASE`,
Playwright falla antes de ejecutar. La cobertura declarada debe contrastarse
con los resultados de la ejecución local; ver [calidad](../development/quality_es.md).
Las pruebas no requieren un servidor remoto.
