# Recetas y resolución configurable

## Identidad y contrato

`Recipe` es la única entidad de receta. Existe como máximo una receta base por
Product; las recetas heredadas pueden estar ligadas a una ProductVariant concreta.
Editar una receta no altera los snapshots de planes, tareas o pruebas anteriores.

Rutas relativas a `/api/v1`:

| Ruta | Operaciones |
| --- | --- |
| `/products/{product_id}/recipe` | POST crear base, GET consultar |
| `/product-variants/{variant_id}/recipes` | POST crear receta ligada, GET listar |
| `/recipes/{recipe_id}` | GET consultar, PUT editar metadata |
| `/recipes/{recipe_id}/plan` | GET consultar pasos, PUT reemplazar plan completo |
| `/products/{product_id}/recipe/resolve` | POST resolver base sin persistir producción |

La identidad y ámbito de Recipe no se cambian mediante edición. Para una base,
resolver o planificar exige elegir una variante de su producto, aunque exista
una sola. Una receta ligada conserva su variante y no admite selecciones nuevas.

## Pasos, cantidades y dependencias

Cada paso tiene clave local estable, título, tipo de tarea, unidad,
`quantity_per_output`, `batch_yield`, instrucciones e inputs. Las dependencias
forman un DAG. Los lotes se redondean hacia arriba al planificar; las unidades
continuas conservan Decimal y la unidad `unit` requiere cantidades enteras.

`kind` distingue `operation`, `print`, `service` y `wait`. Print exige FDM/SLA;
service referencia una definición reutilizable y admite operación manual,
ensamblaje o posprocesado. Wait usa defaults técnicos manual/unit/1/1: no son
minutos ni implementa temporización. No tiene máquina, salida o consumos.
Los recursos pueden identificar también el objeto de un servicio o espera.

Un paso de receta base puede indicar `is_final_output=true`, con cantidad por
salida igual a uno y sin variante fija. La resolución enlaza esa salida con la
variante elegida sin modificar la plantilla. Guardar una base incompleta es
posible; planificar exige exactamente una salida final válida.

Los inputs de producto pueden referenciar un paso productor prerrequisito de la
misma receta o stock. No se expande automáticamente otra receta.

## Opciones, omisiones y escala

La [configuración del producto](product_configuration_es.md) define valores
permitidos, cardinalidad, cantidades y defaults. Omitir una característica aplica
sus defaults; enviar una selección vacía es una decisión explícita.

`when_selected` expresa una condición positiva por paso. Si se omite un paso, sus
sucesores conservan los prerrequisitos activos anteriores de cada rama. Si un paso
activo consume un producto que debía generar un paso omitido, se devuelve conflicto;
no se inventan piezas ni se sustituye ese origen por stock.

`scale_by_selection` multiplica la demanda del paso por la cantidad seleccionada
de su condición. No multiplica `batch_yield` ni insumos o recursos por lote.
Por ejemplo, diez productos con dos accesorios por producto requieren veinte
accesorios; el material por lote conserva su cantidad. No se permite escala sin
condición ni sobre la salida final. Un servicio sin escala mantiene su demanda
por producto aunque use la misma condición de presencia.

## Recursos fijos y seleccionados

Cada recurso tiene clave única en el paso, etiqueta opcional y cantidad por lote.
Su origen es exclusivo: una `asset_revision_id` fija o
`from_selection: {definition_id, value_id}`. Este último sólo se admite en receta
base y debe corresponder a un valor permitido del producto.

Resolver un paso activo exige una implementación física inequívoca para cada
recurso seleccionado. Ausencia o ambigüedad producen conflicto; un paso omitido
no exige sus recursos. El resultado fija Asset y revisión en la instantánea.
No se expanden composiciones a pasos ni se crea stock por referenciar un Asset.
Ver [estructura de Assets](asset_structure_es.md).

## Materiales seleccionados

`OptionValue.supply_id` identifica un insumo concreto. Un paso puede declarar
`selected_supply_inputs` con característica, unidad y cantidad por lote.
Resolver exige exactamente un valor seleccionado con insumo activo y unidad base
idéntica. No se infieren marcas, sustituciones, conversiones ni cantidades por stock.
Si entradas fijas y seleccionadas resuelven el mismo insumo del paso, se rechaza;
no se suman silenciosamente. La cantidad seleccionada no vuelve a multiplicar
el material por lote. Un paso omitido no exige material.

## Servicios y contexto automático

La plantilla admite únicamente `{piece}`, `{design}`, `{product}` y `{quantity}`.
No admite scripting, acceso a atributos, conversiones o especificadores de formato.
Los valores sustituidos son texto y no vuelven a interpretarse como plantilla.

En una receta base, la resolución completa valores ausentes:

| Valor | Fuente |
| --- | --- |
| `product` | Nombre del producto |
| `quantity` | Demanda calculada del paso, expresada como texto Decimal |
| `piece` | Etiqueta del único recurso, o nombre del Asset |
| `design` | Nombre del Asset de ese único recurso |

El contexto explícito tiene precedencia. Varios recursos o ausencia del recurso
necesario exigen texto explícito; no se elige uno por orden. GET/PUT conserva
`action_context` tal como se guardó y puede devolver `service_action=null` si falta
la resolución automática. Resolver, previsualizar y crear planes conservan la frase
y contexto efectivos. Las recetas ligadas mantienen su contrato de contexto explícito.
No se agregan costos ni duraciones por registrar un servicio.

## Planificación e historia

Resolver devuelve configuración, pasos activos, omitidos y cantidades en una
instantánea PostgreSQL REPEATABLE READ; no crea Quote, plan, tareas o stock.
Las rutas de producción consumen esa resolución. `machine_assignments` es una
asignación explícita por clave de paso, no una sugerencia guardada en RecipeStep.
Service/wait no admiten máquina y asignar un paso omitido produce error.

Crear un plan conserva snapshots de configuración, recursos, materiales, frases
y dependencias. El reintento con la misma petición recupera el snapshot original;
un cambio de petición con el mismo identificador genera conflicto. No se relee
el catálogo para reescribir historia. La planificación puede reservar insumos,
pero no los consume. Ver [planes](production_plans_es.md),
[Test Print](test_prints_es.md) y [pricing preview](pricing_preview_es.md).

## Verificación

Los tests de integración cubren base de producto, configuración, recursos,
condiciones, escala, materiales, contexto de servicios e idempotencia en
`backend/tests/integration`. Los resultados se atribuyen a cada ejecución,
no a este documento. Ver [calidad](../development/quality_es.md).
