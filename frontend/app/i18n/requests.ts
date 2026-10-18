export const requestMessages = {
  pending:
    "Hay una solicitud pendiente de respuesta. Reintentá la misma solicitud antes de realizar cambios.",
  retryPending: "Reintentar solicitud pendiente",
  storageUnavailable:
    "El navegador no pudo conservar el reintento. Mantené esta pestaña abierta hasta obtener respuesta.",
  invalidPending:
    "No se pudo leer la solicitud pendiente guardada. Revisá el estado guardado de la operación antes de iniciar otra.",
  clearPending: "Ya revisé el estado: descartar registro ilegible",
} as const;
