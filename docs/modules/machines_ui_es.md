# Interfaz de máquinas

- `/machines`: catálogo, filtros de actividad y tipo aplicados por API. Acceso
  desde Máquinas en el menú Más del shell.
- `/machines/new`: alta, confirmación del estado y catálogo de registros actuales
  para revisar un resultado incierto.
- `/machines/{id}`: datos guardados, edición parcial y activación/desactivación.
  Enlace a `/production?machine={id}` con filtro inicial aplicado al servidor.

Community admite dos máquinas activas. El backend valida altas/reactivaciones;
la UI conserva entradas cuando recibe el conflicto y permite corregirlas.
No hay eliminación ni modificación del límite. Inactividad no equivale a cancelar
producción o cerrar intentos: esas transiciones se realizan desde producción.

Importes, potencia y vida útil son texto, sin conversiones numéricas en navegador.
Datos desconocidos se envían como null y se muestran como desconocidos; no se
inventan costos ni se recalculan snapshots. Fecha de compra es una fecha civil,
sin conversión UTC. En alta, moneda vacía utiliza configuración de instalación;
en edición es obligatoria y se conserva la moneda histórica.

PATCH envía sólo diferencias respecto a los datos cargados/guardados. Consultar
registros no sobrescribe el formulario en edición. Tras un guardado confirmado
se actualiza la base de comparación, incluyendo cambios que vuelvan a un valor
anterior. No existe ETag en el contrato; no se garantiza resolver simultaneidad.

Se reutiliza el guard de escrituras inciertas de inventario con scope machine.
POST y PATCH no se reenvían automáticamente: un aviso persiste por pestaña y
bloquea nuevas escrituras hasta consulta y reconocimiento explícito. El resumen
no permite deduplicar operaciones entre pestañas. Si sessionStorage falla, se
informa que el aviso sólo se conserva en memoria.

Esta pantalla no contiene costos por hora calculados, mantenimiento, sensores,
reservas de agenda ni estadísticas de uso. Configuración global es otro incremento.
No cambia backend, esquema, contratos ni dependencias.
