# Contratos y límites externos

La interfaz pública implementada es la API HTTP de FastAPI, documentada mediante
OpenAPI. El frontend consume ese contrato y no accede directamente a PostgreSQL.

No hay conectores ERP, sincronización fiscal, importación desde slicers ni
control físico de máquinas o dispositivos. Tampoco hay un modelo persistente de
referencias externas o un proceso de sincronización que deba instalarse.

Los parámetros técnicos de producción se registran manualmente. Los archivos
se incorporan mediante la API de Assets y se conservan en almacenamiento local.

Las dependencias del núcleo se mantienen explícitas: una integración externa no
debe introducir reglas de negocio en el frontend ni exigir columnas propias de
un proveedor en las entidades. Esta regla no autoriza implementar adaptadores
nuevos durante la estabilización.
