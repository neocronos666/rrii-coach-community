# Dataset demo: propuesta pendiente de aprobación

No se implementa un wizard ni un nuevo flujo de negocio. `install.sh --demo`
actualmente devuelve un mensaje explícito de opción no disponible, sin crear datos.

## Lo que existe

Los E2E crean datos por API, sin dumps ni acceso al dominio desde el frontend:

- `frontend/tests/e2e/products.spec.ts`: familia, Asset, insumo y producto.
- `frontend/tests/e2e/quick-quotes.spec.ts`, función seed: producto, variante y receta
  con salida final, utilizadas por preview, historial y formalización.
- `frontend/tests/e2e/test-prints.spec.ts`, función seed: producto final/componente,
  insumo, máquina, servicio, opciones Mate/Brillo y receta con dependencias.

Estos seeds sirven de referencia técnica, pero son distintos y hoy usan nombres
con timestamps. No existe un fixture único que ya cubra todo el recorrido y pueda
copiarse como si fuese un dataset demo terminado.

## Propuesta

Crear una carpeta/instalación demo independiente, con su propio .env, proyecto,
puerto y volúmenes. Cargar un conjunto sintético por las APIs ya existentes,
únicamente si esa instalación está vacía. Registrar IDs y versión del dataset para
no repetir parcialmente una carga. Nunca cargarlo sobre una instalación real.

Conjunto propuesto: una pieza de muestra con Asset propio, dos acabados, una receta,
un material con stock y precios ficticios, un servicio y una máquina. Dejar que el
tester realice Quick Quote → formalización de Quote y Test Print por separado en
la UI; cargar catálogos no debe simular aprobaciones, promociones ni consumos.

Extraer las estructuras compartidas de los E2E sólo después de definir el dataset.
No reutilizar literalmente nombres aleatorios ni convertir sus helpers en lógica
funcional de la aplicación. El runner de seed puede vivir dentro de la imagen o
como comando del paquete; el usuario no necesita instalar Python o Node.

## Decisiones a confirmar antes de implementar

- Si se acepta una instalación demo independiente, sin conversión a datos reales.
- Qué pieza/receta y valores ficticios permiten una cotización completa y un Test
  Print comprensible, sin enseñar costos incompletos como si fueran cero.
- Si se precargan sólo catálogos (propuesto) o también documentos históricos.

Esta preparación deja el demo pendiente y no altera el dominio ni los tests actuales.
