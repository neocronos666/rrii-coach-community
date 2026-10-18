# Características, opciones y configuración de productos

## Separación entre selección e implementación física

Sombrero se resuelve contra la Cabeza seleccionada. Cambiar Cabeza cambia las
adaptaciones de Sombrero resolubles. El contexto es una referencia explícita por
característica a un recurso fijo o al resultado de otra selección; no se infiere
compatibilidad con cualquiera o todos los recursos del Product. Esta referencia
limitada no constituye un motor genérico de dependencias condicionales.

## Catálogo global

`OptionDefinition` representa una característica reutilizable, por ejemplo Sombrero.
`OptionValue` pertenece a una definición y representa una opción semántica, por
ejemplo Gaucho. Ambas entidades tienen UUIDv4, nombre, descripción, active y
timestamps UTC. Los nombres se recortan en API y no pueden quedar vacíos. Son únicos
globalmente para definiciones y dentro de la definición para valores; la comparación
es exacta y distingue mayúsculas. El mismo nombre de valor puede usarse en distintas
características.

Un valor puede referenciar `AssetFamily` mediante `family_id` nullable. La familia
identifica el diseño; no elige una adaptación ni revisión. Gaucho Pikachu y Gaucho
Raichu pueden compartir familia y la opción continúa llamándose Gaucho. Un valor
sin familia también es válido como concepto semántico; por sí solo no proporciona
una implementación física. No se aceptan referencias directas a Asset, STL ni
StoredFile en estos contratos.

Las identidades y la pertenencia de un valor a su definición no se cambian mediante
PATCH. Nombre, descripción, active y familia son editables. `family_id: null` retira
el vínculo; omitirlo lo conserva. Desactivar no elimina filas ni modifica el estado
propio de sus valores. Las consultas administrativas permiten ver ambas condiciones;
el uso de elementos inactivos en nuevas configuraciones pertenece a 3b. No existe
DELETE. No se crean características, valores ni familias demo automáticamente.

Las FK usan RESTRICT. La identidad compuesta `(definition_id, id)` permite que 3b
restrinja en base de datos la pertenencia de las opciones. No se modifica
ProductVariant, sus atributos ni la Recipe existente.

## API administrativa

Rutas relativas a `/api/v1`:

| Ruta | Operaciones |
| --- | --- |
| `/option-definitions` | POST crear, GET listar |
| `/option-definitions/{definition_id}` | GET consultar, PATCH editar/desactivar |
| `/option-definitions/{definition_id}/values` | POST crear valor, GET listar |
| `/option-definitions/{definition_id}/values/{value_id}` | GET consultar, PATCH editar/desactivar |

Los listados admiten active opcional, search por nombre con comodines escapados,
offset y limit (50 por defecto, máximo 100). Se ordenan por nombre/UUID. Un valor
consultado con otra definición devuelve 404. Duplicados producen 409; campos
desconocidos o null en name/active producen 422; familia inexistente produce 404.

`OptionService` controla las transacciones. La actualización bloquea y refresca la
fila; las escrituras de valores bloquean primero su definición. Las restricciones
únicas protegen las altas concurrentes. Un fallo de persistencia revierte la
transacción; no quedan valores parcialmente creados.

## Configuración por producto

`ProductOption` declara una característica global dentro de un Product. Sus opciones
permitidas se registran en `ProductOptionValue`; una FK compuesta impide registrar
un OptionValue de otra definición. No se modifica ProductVariant ni su unidad.
Las claves de las asociaciones son los UUID de las entidades relacionadas.

`min_selections` y `max_selections` cuentan valores distintos; max null significa
sin límite adicional a las opciones permitidas. La cantidad de cada valor es
Decimal positivo (18,6), separada de esa cardinalidad. Por ejemplo, Gaucho ×2 y
Cowboy ×1 representan dos selecciones. La cantidad de Product pertenece al caso
de recetas y pricing; este endpoint no la multiplica ni calcula costos.

Un `default_quantity` no nulo marca un valor por defecto. Los defaults pueden
omitirse incluso en una característica obligatoria: el usuario deberá elegir.
Si se especifican defaults, deben formar una selección válida dentro de min/max.
No se deduce una selección obligatoria única silenciosamente en esta capa.

- GET `/products/{product_id}/configuration`: declaraciones y opciones permitidas.
- PUT en esa ruta: reemplaza la lista completa de forma atómica; una lista vacía
  retira todas las declaraciones. Bloquea Product y luego definiciones ordenadas.
  La relación pertenece a la configuración actual, no a un snapshot comercial.
- POST `/products/{product_id}/configuration/resolve`: resuelve una selección sin
  persistir resultado, crear Quote ni consumir stock.

Ejemplo de entrada al resolver:

```json
{
  "selections": [
    {
      "definition_id": "<UUID de Sombrero>",
      "values": [{"value_id": "<UUID de Gaucho>", "quantity": "2"}]
    }
  ]
}
```

Omitir una característica aplica sus defaults. Incluir `values: []` no los aplica;
se valida contra el mínimo. No se aceptan definiciones ajenas al Product, valores
no permitidos, duplicados, cantidades no positivas o datos de recursos calculados
por el cliente. Las configuraciones administrativas pueden consultarse aunque se
hayan desactivado elementos; una selección inactiva o un Product inactivo no se
resuelven. Guardar nuevas declaraciones exige definiciones y valores activos.

## Contexto y resolución física

Cada declaración admite como máximo uno de estos contextos:

- `context_asset_id`: un recurso explícito fijo.
- `context_definition_id`: la selección de otra característica del mismo Product.

La FK compuesta restringe el segundo contexto al Product. El servicio valida el
DAG y ordena de forma topológica estable antes de insertar o resolver. No depende
del orden enviado por el cliente. Sombrero puede resolver después de Cabeza incluso
si el cliente envía Sombrero primero.

Un contexto tomado de otra selección debe producir exactamente un valor con un
recurso físico. Ninguna selección, varias selecciones o una opción semántica sin
recurso producen un error explícito si el dependiente está seleccionado. La cantidad
del contexto no multiplica la del dependiente; no se asignan sombreros entre varias
cabezas ni se infiere compatibilidad con todas o alguna. Una característica sin
selección no exige resolver su contexto.

Para un valor con familia se buscan Assets activos de esa familia con revisión
actual. Si existe contexto, se exige una relación positiva Asset↔Asset explícita.
Cero candidatos produce «No hay implementación declarada»; más de uno produce
«Implementación ambigua». Esto no declara incompatibilidad negativa. La consulta
limita a dos candidatos porque basta para detectar ambigüedad, sin cargar cientos
de coincidencias. No se expande composición ni se aplica transitividad implícita.

Sin contexto, una familia con una sola adaptación activa puede resolverse; si tiene
varias se exige corregir la configuración. Sin familia y sin contexto, el valor es
semántico y devuelve asset_id/revision_id null. Una opción que declara contexto
físico necesita familia. Una opción semántica puede condicionar pasos de receta
sin representar un archivo o recurso físico.

El resultado identifica Product, características, cantidades, contexto resuelto,
familia, Asset y revisión concreta. El orden es estable por dependencias y UUID.
No es un snapshot persistido: otra solicitud puede adoptar la revisión actual que
exista entonces; el resultado anterior no se reescribe.

Las entradas de lectura del servicio usan una transacción PostgreSQL REPEATABLE
READ y requieren sesión sin consultas previas. Se evita combinar configuración,
compatibilidades y revisiones de momentos distintos dentro de una respuesta. El
servicio controla commit/rollback; no realiza escrituras durante la resolución.
Los consumidores conservan los UUID resueltos en sus snapshots y no deben
recalcularlos silenciosamente.

## Vínculo de material

OptionValue admite supply_id opcional además de family_id. El nombre de la opción
continúa siendo semántico (PLA/PETG); supply_id identifica el insumo concreto que
se utilizará cuando un paso solicite material desde esa característica. Crear o
cambiar el vínculo exige un Supply existente y activo; null lo retira y omitir el
campo lo conserva. La FK usa RESTRICT. No hay elección automática por categoría,
marca, disponibilidad de stock ni equivalencia de nombres.

La configuración resuelta incorpora supply_id y supply_unit; ambos son null si
la opción no tiene insumo. Una opción seleccionada con insumo inactivo produce
409. Estos datos se leen en la misma instantánea que la configuración y los Assets.
Las declaraciones de material del paso requieren exactamente un valor seleccionado;
no restringen la cardinalidad global de la característica en otros usos. La cantidad
seleccionada no multiplica la cantidad por lote. Detalles y límites en
[recetas](recipes_es.md), sección de materiales seleccionados.
