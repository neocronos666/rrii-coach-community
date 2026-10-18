export const productionMessages = {
  title: "Producción",
  new: "Nuevo plan de producción",
  plan: "Plan de producción",
  create: "Crear plan de producción",
  source: "Ver origen comercial",
  sourceQuote: "Ver presupuesto de origen",
  creationHelp:
    "Elegí la variante, receta vigente y cantidad física a producir. La cantidad comercial puede representar una demanda completa: no se copia como cantidad física. Contrastá la configuración con el presupuesto de origen.",
  reserve: "Reservar insumos al crear",
  allocate: "Asignar salida al destino al crear",
  effects:
    "La reserva no consume insumos. La asignación compromete producto al destino, pero no fabrica ni entrega. Los faltantes se informan sin bloquear la creación.",
  confirm: "Confirmo la configuración, cantidad y efectos del nuevo plan.",
  previewHelp:
    "Vista previa del servidor sin crear tareas, reservas ni asignaciones. Crear vuelve a resolver la receta vigente; puede diferir si el catálogo cambió.",
  historical:
    "Receta y configuración guardadas al crear el plan. Los importes comerciales no se recalculan.",
  warnings: "Advertencias de disponibilidad actual",
  tasks: "Tareas",
  empty: "No hay tareas para estos filtros.",
  all: "Todos",
  priority: "Prioridad",
  originRequired:
    "Abrí la planificación desde un pedido o componente de proyecto.",
  cancelledOrigin: "El destino está cancelado; no admite planes nuevos.",
  sourceQuantity:
    "Cantidad comercial guardada (no es una cantidad física inferida)",
  task: "Tarea de producción",
  progress: "Progreso informado por el servidor",
  remaining: "Pendiente",
  excess: "Excedente",
  closeHelp:
    "Indicá resultados y consumos reales. El consumo total incluye desperdicio. El cierre descuenta los consumos e ingresa las unidades buenas de la salida inventariable al stock. No entrega ni cierra el pedido o proyecto.",
  pause: "Pausar tarea",
  resume: "Reanudar tarea",
  cancel: "Cancelar tarea",
  actionConfirm: "Confirmo el cambio de estado de esta tarea.",
  actionHelp:
    "El servidor valida el estado y los intentos abiertos. Cancelar libera reservas de la tarea; no revierte consumos ni libera la asignación comercial del plan.",
  uncertain:
    "No se pudo confirmar la respuesta. Se consultó el estado; verificá el resultado antes de volver a operar.",
  legacy:
    "Esta tarea histórica usa el ciclo legacy. Sus operaciones siguen disponibles por API; no admite intentos desde esta pantalla.",
  manual:
    "Esta tarea no tiene snapshot de receta. Sus ejecuciones y consumos avanzados se gestionan por API.",
  allocation: "Asignación de salida",
  noAllocation: "Sin asignación de salida",
  filter: "Aplicar filtros",
  clear: "Ver toda la producción",
  machine: "Máquina",
  currentUnits:
    "Las unidades de insumos mostradas se consultan en el catálogo actual; los consumos cerrados conservan su unidad histórica.",
  planLink: "Abrir plan",
  taskLink: "Abrir tarea",
  productionLink: "Ver producción",
  planLinkNew: "Planificar producción",
} as const;
export const productionStates = {
  queued: "En cola",
  in_progress: "En curso",
  paused: "Pausada",
  physically_completed: "Finalizada físicamente",
  cancelled: "Cancelada",
} as const;
export const productionPriorities = {
  low: "Baja",
  normal: "Normal",
  high: "Alta",
  urgent: "Urgente",
} as const;
