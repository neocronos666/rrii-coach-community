# Familias, compatibilidades y composición de Assets

Acceso: Más → Familias de diseño (`/families`, `/families/new`, `/families/{id}`).
Desde una revisión en Biblioteca, «Familia, compatibilidades y composición» abre
`/asset-structure/{asset_id}?revision={revision_id}`. La URL sin revision fija
la revisión actual al cargar; no avanza silenciosamente durante consultas.

## Familias y relaciones actuales

Familias admiten alta/edición de nombre y descripción. No existen borrado ni
actividad en su contrato. Se recorren todas las páginas. Alta/edición inciertas
conservan aviso por pestaña, sin reenvío automático, con consulta para revisión.

La familia del Asset y las compatibilidades son metadata actual; no pertenecen
a la revisión histórica consultada. La familia guardada se muestra aparte del
selector en edición. Sin familia envía null explícito. Cambiar la familia no
modifica opciones ni declara compatibilidad.

Compatibilidad es positiva y simétrica. Registrar o retirar requiere confirmación;
retirar no elimina Assets ni declara incompatibilidad. La lista incluye todas
las páginas. Seleccionar el propio Asset se somete al rechazo del backend.
No hay inferencia de relaciones desde familia, categoría o composición.

## Composición por revisión

Se muestran hijos fijados, revisión fijada/actual y disponibilidad de actualización.
Assets archivados se cargan explícitamente y se identifican; no desaparecen las
referencias históricas. Cada componente elige Asset, revisión concreta y cantidad
textual. El servidor valida pertenencia, duplicados, cantidades y DAG sin ciclos.
No se resuelve ni ordena un DAG en el navegador.

Publicar envía lista completa y revisión base; crea otra revisión del padre y
copia sus archivos. Una lista vacía retira hijos sólo en la nueva revisión.
Adoptar una revisión hija actual modifica el borrador, nunca el histórico, y
requiere publicar explícitamente. Cambiar el Asset hijo vacía su selector de
revisión para evitar enviar una revisión de otro Asset.

Una revisión antigua permite consulta con campos deshabilitados. Si la revisión
actual cambia después de abrir, el backend rechaza la base obsoleta; la UI conserva
borrador y ofrece abrir la vigente. Consultar no pisa cambios. Navegar a otra
revisión con cambios solicita confirmación. Tras éxito se abre la revisión creada.

Publicación incierta bloquea nuevos envíos, también al abrir otra revisión del
mismo Asset: el aviso tiene scope del Asset. Consultar, revisar y reconocer permite
continuar sin duplicar automáticamente revisiones. No se deduce éxito comparando
componentes ni se inventa request_id. El aviso persiste por pestaña; si falla
sessionStorage, sólo queda en memoria y se informa. Las relaciones usan un scope
separado; no bloquean consultas históricas. No existe garantía entre pestañas.

## Límites

No se agregan reglas de negocio, migraciones ni endpoints. La [administración de metadata y categorías](asset_details_ui_es.md) se ofrece
en pantallas separadas; se mantienen los recorridos de Biblioteca existentes. No se deduce costo,
producción ni stock de una composición. Sin cambios de dependencias ni despliegue.
