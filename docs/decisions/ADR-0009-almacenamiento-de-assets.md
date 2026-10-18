# ADR-0009: Almacenamiento local de Assets

- Estado: implementada; alcance revisado el 2026-10-17.
- Fecha original: 2026-07-28.

## Decisión

PostgreSQL conserva metadatos y relaciones; los bytes se almacenan en filesystem
local mediante `assets/storage.py`. Los archivos registran SHA-256 y tamaño.
Las claves de almacenamiento se derivan del contenido, no de rutas del cliente.
No hay almacenamiento de objetos remoto implementado.

## Consecuencias

Los respaldos deben incluir PostgreSQL y el volumen de assets. Detener el entorno
normalmente conserva ambos. La carga valida límites y formatos en el backend;
las revisiones preservan las referencias necesarias para consultar la historia.
