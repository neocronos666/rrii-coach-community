# Familias, composición y compatibilidad de Assets

## Identidades

`AssetFamily` agrupa adaptaciones del mismo diseño; no es una revisión ni un
producto. Tiene nombre y descripción editables. `Asset.family_id` es opcional:
los recursos existentes permanecen sin familia hasta clasificarlos. Una revisión
no crea otra adaptación/familia. Un diseño diferente se registra como otra familia
y otro Asset, no como una corrección geométrica de un Asset existente.

API: POST/GET `/api/v1/asset-families`, GET/PATCH `/{family_id}`. Crear/actualizar
Asset admite family_id (null permite desvincular); GET `/assets?family_id=...`
filtra miembros. No hay borrado de familias por API.

## Composición reproducible

`AssetCompositionComponent` pertenece a una revisión del padre y fija un
child_asset_id, child_revision_id y cantidad Decimal/NUMERIC(18,6) positiva.
La FK compuesta exige que la revisión pertenezca al hijo indicado. Cada hijo
aparece una sola vez por padre/revisión; la cantidad representa repeticiones.
No hay pasos productivos, ensamblado ni máquinas en la composición.

- GET `/assets/{id}/revisions/{revision_id}/composition`: hijos directos y sus
  revisiones/cantidades fijadas. No expone sus archivos ni historial completo.
- POST `/assets/{id}/composition-revisions`: requiere base_revision_id actual y
  lista completa `components`; crea otra revisión y copia referencias a archivos
  del padre. La lista vacía elimina todos los hijos en la nueva revisión solamente.
- GET `/assets/{id}/revisions/{revision_id}/component-updates`: revisiones fijadas
  frente a actuales de hijos directos, con update_available. No modifica datos.
- Adoptar una revisión hija consiste en publicar explícitamente una nueva lista
  con el UUID elegido mediante composition-revisions. No existe seguimiento
  automático de latest. Se puede conservar una revisión antigua indefinidamente.

Si cambió la revisión base, publicar devuelve 409: el caller debe revisar el nuevo
estado antes de volver a intentarlo. No fusiona selecciones silenciosamente.
Una revisión ordinaria conserva la composición actual. Restaurar copia la
composición histórica y los archivos propios en una nueva revisión actual.
El comportamiento de archivos es: la revisión ordinaria no copia
archivos automáticamente; restauración y publicación de composición sí los copian.

## Ciclos y concurrencia

Se validan dos grafos por identidad de Asset:

1. Relaciones de las revisiones actuales, reemplazando las aristas del padre.
2. Snapshot expandido siguiendo exclusivamente las revisiones hijas fijadas.

Ambos deben ser DAG; tampoco se permite auto-inclusión mediante una revisión
antigua del mismo recurso. Compartir un descendiente entre ramas sí está permitido.
Se usan recorridos iterativos y consultas por niveles, sin recursión Python ni
consulta individual por cada nodo. Las revisiones históricas nunca se alteran.
Restaurar también valida el grafo actual resultante y puede devolver 409 si crearía
un ciclo; la revisión histórica sigue disponible para consulta.

El lock transaccional de composición precede al lock del Asset en toda publicación
u operación que cambia la revisión actual. Esto serializa escrituras de grafo en
Community y evita ciclos entre publicaciones concurrentes de distintos padres.
Las lecturas con lock refrescan la identidad ORM para no usar una revisión actual
obsoleta que estuviera cacheada en la sesión. Los servicios controlan la transacción;
ningún helper de composición hace commit. Una falla revierte revisión, puntero y filas.

## Compatibilidad positiva

Asset↔Asset simétrica, par canónico único y dos recursos distintos. No se deriva
compatibilidad por compartir familia. No hay reglas negativas; ausencia o retirada
significa que no hay declaración positiva, no que los recursos sean incompatibles.

GET `/assets/{id}/compatibilities` devuelve items/total/offset/limit (máximo 100 por
página), con metadata mínima. PUT `/{other_id}` es idempotente incluso invirtiendo
los extremos; DELETE retira la declaración positiva. Se conservan relaciones con
recursos archivados, informando su estado. Índices en ambos extremos permiten
consultar cientos de coincidencias sin cargar toda la lista en la respuesta.

## Límites y uso desde la interfaz

Los avisos se refieren a hijos directos; adoptar una revisión requiere publicar
explícitamente una revisión del padre. La composición no crea producción ni stock.
La [interfaz de estructura](asset_structure_ui_es.md) permite gestionar familias,
compatibilidades y componentes. La resolución de opciones se describe en
[configuración de productos](product_configuration_es.md).
