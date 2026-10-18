# Interfaz de Quick Quote y presupuesto formal

Incremento de 10B.9 sobre los contratos existentes de pricing preview,
Quick Quote y formalización única. No modifica backend, migraciones ni OpenAPI.

## Recorrido

- `Crear → Presupuesto rápido`, `/quotes` o «Presupuestar este producto» abren
  `/quick-quotes/new`. Producto, variante y receta se eligen explícitamente.
- La entrada incluye cantidad, FIFO simulado/última compra, markup opcional,
  selecciones por característica y estimaciones **totales de la demanda** por
  paso: máquina/tiempo, energía, mano de obra y costos adicionales.
- «Evaluar sin guardar» llama pricing-preview. «Guardar borrador» vuelve a evaluar
  por API y conserva la primera revisión. Ninguna acción consume o reserva stock.
- `/quick-quotes` permite retomar borradores; el detalle muestra historial,
  evaluación y receta resuelta guardados. Consultarlos no requiere el catálogo vivo.
- «Editar última revisión» fija la revisión esperada al abrir el editor.
  «Recalcular última revisión» es otra escritura explícita que conserva la entrada
  guardada y consulta fuentes actuales. Ambas crean revisiones inmutables.
- Formalizar usa la revisión elegida, admite vigencia, ajustes y total propuesto.
  El backend exige costo completo, una moneda y markup conocido, y aplica el
  redondeo del total final ARS al peso inferior. La UI muestra los importes recibidos.
- Cada borrador sólo tiene un Quote formal. Su enlace y revisión de origen se
  muestran en el detalle. `/quotes` y `/quotes/[id]` consultan el presupuesto formal,
  con totales, ítems, estado y vínculo a su origen. La [continuidad comercial](commercial_ui_es.md) permite aprobar y convertir;
  [Test Print](test_print_ui_es.md) se abre desde Producto/variante.

## Integridad y recuperación

Dinero, energía y cantidades permanecen como cadenas decimales. No se calcula
FIFO, markup, ajustes, precios ni redondeo en navegador. Cero explícito, ausencia
para usar la configuración y fuente desconocida permanecen diferenciados.

Se conserva el borrador local ante errores y refetch. Un conflicto de versión
no reemplaza esa edición; consultar última revisión, descartar y volver a editar
son acciones explícitas. Hay aviso antes de abandonar cambios locales.

Cada escritura recibe un UUID y una copia fija de su cuerpo. Si se pierde la
respuesta, llega un timeout HTTP o un error de servidor, el reintento conserva ambos y bloquea
cambios hasta obtener resultado. `sessionStorage`, separado por API, operación
y borrador, permite retomar la solicitud en la misma pestaña tras recargar.
No es almacenamiento del historial: éste reside en PostgreSQL.
Si el navegador bloquea almacenamiento, se informa y el reintento permanece
sólo en memoria; no debe cerrarse la pestaña mientras el resultado sea incierto.
Un documento pendiente ilegible exige revisar el estado remoto y descartarlo
explícitamente. No se descarta silenciosamente para crear otra operación.

Una respuesta idempotente puede corresponder a una revisión histórica. Tras
escribir se refresca última revisión e historial, sin considerar aquella respuesta
como la versión actual. La formalización existente se consulta antes de ofrecer
alta; errores distintos de 404 se muestran como errores, no como ausencia.

## Alcance y validación

Se reutilizan Nuxt UI, TanStack Query, openapi-fetch y tipos generados. El aviso
al salir se comparte con Productos. El [dashboard actual](dashboard_live_ui_es.md) consulta datos reales.
La [interfaz comercial](commercial_ui_es.md) agrega edición posterior, aprobación y conversión explícitas sobre el Quote formal.

Unitarias cubren transporte decimal, estados HTTP, historial paginado y
persistencia de identidad/cuerpo pendiente. E2E con API y PostgreSQL aislados
cubren edición, historial, conflicto, costos incompletos, formalización única,
redondeo recibido y respuestas perdidas tras commit con recarga/reintento.
Axe y capturas complementan el recorrido móvil/escritorio claro/oscuro.
Para E2E se requiere `RRII_E2E_API_BASE`; sin ella la configuración falla
antes de ejecutar casos. Consultar [arquitectura frontend](../architecture/frontend.md) para
comandos de tipos, lint, unitarias, build y Playwright.
