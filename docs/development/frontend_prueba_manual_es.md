# Recorrido manual del frontend Community terminado

Iniciar el [entorno local de prueba humana](human_test_environment_es.md) y abrir
`http://localhost:13000`. Las rutas siguientes son relativas a esa aplicación;
la API del entorno se publica en `http://localhost:18000/api/v1` y admite ese
origen mediante CORS. Este recorrido es prueba humana, no un resultado de tests.

| Pantalla | Ruta y recorrido |
| --- | --- |
| Inicio real | `/`: bloques operativos, actualizar, personalizar, links a registros |
| Biblioteca | `/assets`: alta, revisión, archivos, thumbnail y comparación |
| Datos del Asset | Desde detalle → Editar datos; `/asset-details/{id}` |
| Estructura | Desde revisión → estructura; `/asset-structure/{id}?revision={n}` |
| Familias / categorías | `/families`, `/asset-categories` |
| Productos / variantes | `/products`: detalle, opciones/configuración, receta y prueba |
| Opciones y servicios | `/options`, `/services` |
| Quick Quote | `/quick-quotes/new`: preview y guardar; `/quick-quotes` para retomar historial y formalizar |
| Presupuestos | `/quotes`: condiciones comerciales, aprobar/rechazar y convertir explícitamente |
| Composición independiente | `/quotes/new`, cálculo en `/calculations/new`, consulta `/calculations/{id}` |
| Ítems de borrador ordinario | Detalle → Editar ítems técnicos; `/quote-items/{id}` |
| Pedidos / proyectos | `/orders`, `/projects`: planificar receta o crear tarea manual desde el origen |
| Producción | `/production`: filtros, tarea, intentos, consumos y progreso |
| Edición operativa | Tarea → Editar planificación; `/task-edit/{id}` |
| Test Print | Producto/variante → Probar receta; `/test-prints` para retomar y promover explícitamente a stock |
| Inventario | `/inventory`: insumos, presentaciones, compras, ajustes y stock; reservas desde tarea, asignaciones/entregas desde origen |
| Máquinas | `/machines` |
| Configuración de instalación | `/settings`; se distingue de apariencia/dispositivo del navegador |

Prueba sugerida: crear producto y receta → Quick Quote → guardar/formalizar →
aprobar → convertir → planificar → iniciar/cerrar ejecuciones con cantidades reales
→ consultar stock y entregas. La aprobación, conversión, producción y entrega son
acciones separadas. Para Test Print, ejecutar la receta completa y luego promover
la cantidad autorizada; cerrar intentos por sí solo no promociona la prueba.

Para tareas manuales: abrir un pedido → crear tarea → elegir salida opcional y su
unidad base → editar planificación → agregar prerrequisitos del mismo origen →
iniciar intento → registrar buenas/fallidas y consumos → comprobar progreso/stock.
Una tarea cerrada es inmutable; las dependencias/cantidades de recetas no se editan.

Cálculos técnicos independientes se eligen por ID porque la API no ofrece listado.
Los snapshots no se recalculan al consultarlos. No hay suma de monedas en navegador.
El dashboard de actividad muestra últimas actualizaciones, no una auditoría.
