# Módulo de máquinas

## Entidad

`Machine` representa un equipo maker individual y genérico. No presupone que
sea una impresora ni que dos unidades del mismo modelo tengan igual historial.

Campos iniciales: UUID, nombre, tipo, fabricante, modelo, fecha y precio de
compra, moneda histórica, potencia nominal, vida útil estimada, estado activo,
notas y timestamps UTC.

Los importes usan `Decimal` y `NUMERIC(18, 4)`. Potencia y horas estimadas usan
`NUMERIC(12, 2)`. `purchase_date` utiliza `DATE`.

El motor técnico puede derivar una depreciación básica por hora a partir de
precio de compra y vida útil, y estimar energía mediante potencia nominal. No
son depreciación contable ni consumo medido; datos faltantes producen líneas
incompletas.

## Tipos

Los valores estables son `fdm_printer`, `sla_printer`, `cnc`, `laser`,
`scanner`, `washer`, `curing_station` y `other`. Se almacenan como `VARCHAR` y
se validan con enums Python/Pydantic. No se crea un enum PostgreSQL para evitar
migraciones innecesarias al ampliar la lista.

## Reglas Community

Community admite como máximo dos máquinas activas, sin distinguir tipo. La
regla reside en `MachineService` y se aplica al crear activa o reactivar. No
bloquea consultas, ediciones ni desactivaciones. El valor no es configurable
ni un feature flag.

No existe DELETE. `active=false` retira una máquina de servicio preservando su
identidad para trazabilidad futura.

## API

- `GET /api/v1/machines`, con filtros opcionales `active` y `machine_type`.
- `POST /api/v1/machines` (`201`; `409` al superar el límite).
- `GET /api/v1/machines/{machine_id}` (`404` si no existe).
- `PATCH /api/v1/machines/{machine_id}` para actualización parcial.

## Extensiones futuras

Ubicaciones, dispositivos, mantenimiento, consumos y estadísticas de vida útil
se modelarán como entidades relacionadas. No se agregan columnas específicas
para cámaras, sensores, materiales o consumos.
