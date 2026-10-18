# Flujos implementados

## Cotización y destino operativo

```text
Producto / variante + receta
→ preview
→ Quick Quote y revisiones guardadas
→ formalización explícita de una revisión
→ Quote draft
→ aprobación
→ conversión explícita
→ Order (un ítem) o Project (varios ítems)
```

También se puede crear un Quote independiente desde cálculos técnicos completos.
La aprobación no convierte automáticamente ni inicia producción o reserva stock.
Los términos de seña del presupuesto no equivalen a registrar un cobro.

## Producción comercial

```text
Order / ProjectComponent
→ plan de receta o tarea manual
→ tareas y dependencias
→ intentos (Runs)
→ cierre con resultados y consumos
→ salida de stock según configuración explícita
```

El operador usa máquinas y slicers por fuera de la aplicación. La finalización
física de una tarea no cierra automáticamente su pedido o proyecto.
Asignaciones y entregas de productos se registran desde inventario.

## Prueba de receta

```text
Producto / variante + receta
→ Test Print con snapshot de todos los pasos aplicables
→ intentos y resultados
→ completar
→ promoción explícita a stock
```

## Assets e inventario

La biblioteca conserva revisiones y archivos; restaurar una revisión crea otra.
Los productos, recetas y snapshots se vinculan con los recursos que corresponden.
Compras y ajustes generan movimientos de insumos. Las reservas no sustituyen
consumos, y las asignaciones de productos no equivalen por sí solas a entregas.

Consultar [módulos](../modules/) para precondiciones, efectos y errores.
