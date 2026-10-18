# ADR-0003: Núcleo independiente

- Estado: aceptada; alcance revisado el 2026-10-17.
- Fecha original: 2026-07-28.

## Decisión

Los flujos Community se ejecutan mediante servicios propios y la API HTTP.
No requieren un ERP, emisión fiscal ni un proceso externo de sincronización.
El dominio no incorpora columnas específicas de proveedores externos.

## Consecuencias

La documentación describe los contratos implementados. No se promete un registro
de facturación externa ni conectores que no existen en el código. La revisión
documental no introduce cambios en el dominio ni en el esquema.
