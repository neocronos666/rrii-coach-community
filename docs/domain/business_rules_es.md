# Reglas de negocio Community

Estas reglas resumen comportamiento implementado. Los contratos detallados están
en OpenAPI y [módulos](../modules/); esta guía no agrega capacidades.

## Instalación y máquinas

1. Una instalación local tiene una configuración funcional tipada, sin login.
2. El backend limita a dos máquinas activas, independientemente del tipo.
3. Una máquina se desactiva; la API no permite borrarla.
4. Potencia nominal y vida útil son estimaciones, no mediciones de dispositivos.

## Archivos y catálogo

5. Producto, variante, Asset, revisión y archivo son conceptos distintos.
6. Las revisiones históricas se conservan; restaurar crea una revisión nueva.
7. El backend valida formatos, tamaños y nombres de archivos. Los bytes quedan
   en filesystem local y los metadatos en PostgreSQL, con SHA-256.
8. Las recetas describen pasos, dependencias, recursos e inputs. Los snapshots
   operativos no se reescriben cuando cambia el catálogo.

## Costos y presupuestos

9. Dinero y cantidades usan aritmética decimal, nunca `float`.
10. Calcular costos no consume ni reserva stock.
11. Fuentes faltantes producen líneas incompletas, no costo cero.
12. Los snapshots de costos son inmutables; no se recalculan al consultarlos.
13. No se convierten monedas sin un contrato explícito; un presupuesto exige
    cálculos completos de una única moneda.
14. Costo técnico, precio sugerido y precio final son valores distintos.
15. El precio sugerido usa markup. Los ajustes porcentuales se aplican al
    subtotal posterior al markup; luego se agregan los ajustes fijos.
16. Condiciones de seña y precio se conservan en el presupuesto. No se presenta
    un registro de cobros como capacidad del módulo de presupuestos.
17. Sólo un presupuesto `draft` admite edición; la aprobación no crea destinos
    operativos ni consume stock. La conversión posterior es explícita y única:
    un ítem produce Order; varios, Project con componentes.
18. Guardar o consultar un Quick Quote no formaliza un Quote. Las revisiones
    conservan entrada y resultado; recalcular y formalizar son acciones explícitas.

## Ejecución

19. ProductionTask pertenece exactamente a Order o ProjectComponent.
20. Las dependencias forman un DAG dentro del mismo pedido o proyecto.
21. Los estados cambian mediante servicios, no mediante PATCH directo de status.
22. Task representa el objetivo y Run un intento. Un Run abierto ocupa su máquina;
    las tareas legacy conservan su exclusividad histórica.
23. Una tarea paused no admite nuevos Runs. Pausar o cancelar exige cerrar el Run
    abierto. Finalizar un prerrequisito no inicia automáticamente dependientes.
24. Cerrar un Run registra resultados y consumos transaccionalmente; un reintento
    idéntico no duplica movimientos. El fin físico no cierra Order o Project.
25. Test Print prueba una receta completa sin crear destinos comerciales.
    Su promoción a stock requiere una acción explícita.

## Inventario

26. Las existencias físicas se derivan de movimientos, no de un saldo editable.
27. La unidad base de un insumo no cambia después de su primer movimiento.
28. Reservas, consumos y asignaciones son hechos diferentes. Los faltantes al
    registrar consumos físicos se informan según las reglas de ejecución, sin
    ocultar el hecho ocurrido ni presentarlo como stock suficiente.
29. Los movimientos, consumos, snapshots y revisiones preservan historia. No se
    promete auditoría por usuario, trazabilidad serial ni un bus general de eventos.
