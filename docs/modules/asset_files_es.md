# Archivos de Assets: contrato y almacenamiento

## Modelo y alcance

`StoredFile` identifica bytes inmutables por SHA-256, tamaño y clave física relativa
`sha256/<prefijo>/<hash>`. No tiene dueño comercial ni API de carga independiente.
`AssetRevisionFile` vincula esos bytes con una revisión, un nombre y un rol:
`manufacturing`, `source`, `documentation`, `reference`, `media` y
`thumbnail` ([contrato de miniaturas](asset_thumbnails_es.md)).

El nombre distingue adjuntos de una revisión; no es una ruta ni identifica el
blob. Distintos nombres/revisiones/Assets pueden compartir el mismo StoredFile.
No hay reemplazo ni borrado de adjuntos por API: corregir un archivo requiere una
nueva revisión. Se permite completar una revisión vieja con un nombre faltante.
`attached_at` usa la hora real PostgreSQL (`clock_timestamp`); la fecha original
de la revisión no cambia. Restaurar crea una revisión nueva y copia referencias,
con nuevos identificadores/fechas de adjunción, preservando los originales.

No hay adjuntos de Product, explorador de archivos ni mantenimiento automático
de blobs huérfanos.
Un archivo desconocido o sin STL también puede registrarse dentro de un recurso.

## API

Base: `/api/v1/assets/{asset_id}/revisions/{revision_id}`.

- `POST /files?filename=pieza.stl&role=manufacturing`: body binario,
  `Content-Type: application/octet-stream`. Devuelve la referencia y metadata,
  sin exponer ubicación física. No requiere multipart ni dependencias nuevas.
- `GET /files`: adjuntos ordenados por nombre.
- `GET /files/{attachment_id}/content`: descarga como attachment, `nosniff`;
  valida identidad/revisión y verifica hash/tamaño antes de responder.
- `GET /files-diff/{other_revision_id}`: comparación dentro del mismo Asset;
  altas/bajas por nombre, cambios de contenido por hash, cambios de rol y sin
  cambios. Un cambio simultáneo de rol y contenido figura en ambas listas.
- El `POST /restore` copia también referencias a archivos.

Errores: nombre/rol inválido o archivo vacío 422; destino inexistente 404;
nombre duplicado 409 (salvo reintento idéntico de thumbnail); exceso de bytes 413; transporte incorrecto 415;
almacenamiento ausente/inconsistente 503. Los archivos se sirven como descarga;
el MIME detectado nunca habilita ejecución o visualización inline en ese endpoint.
La ruta thumbnail sirve únicamente el PNG normalizado.

## Almacenamiento y consistencia

`ASSET_STORAGE_PATH` existente es la única raíz persistente. El servidor genera
las rutas y rechaza enlaces simbólicos; no acepta rutas físicas por API.
Debe ser un directorio administrado exclusivamente por la instalación, sin
modificaciones externas concurrentes de blobs o de su estructura.

`ASSET_MAX_UPLOAD_BYTES` limita cada archivo (default 268435456 = 256 MiB).
Se comprueba durante el streaming, incluso sin Content-Length. Se usa temporal
anónimo del sistema para recibir y staging en la raíz para publicación atómica;
no se mantiene el archivo completo en RAM. Puede requerir espacio temporal
adicional al blob final. No es una preferencia local del navegador.

Publicación mediante enlace atómico y fsync; nunca sobrescribe el destino.
Lock transaccional por hash + unicidad SQL serializan la deduplicación, incluso
entre Assets diferentes. Se verifica el contenido existente antes de reutilizarlo.
La actualización de referencias y StoredFile pertenece a una transacción del
servicio. El lock del Asset serializa también restauración y adjunción tardía.

Filesystem y PostgreSQL no comparten transacción. Si falla el commit después de
publicar, puede quedar un blob huérfano; una carga posterior del mismo contenido
lo recupera. Nunca se elimina al hacer rollback un blob que otro recurso pudiera
usar. El archivado conserva referencias y bytes. Cualquier mantenimiento debe considerar referencias históricas antes de
eliminar un blob; no hay recolección automática de huérfanos.
Los temporales se limpian al salir; un fallo de limpieza queda registrado y no
convierte un commit ya exitoso en un error aparente. Una caída abrupta del proceso
puede dejar temporales para mantenimiento, que todavía no se automatiza.

## Detección inicial

STL binario: tamaño coherente con contador de triángulos. STL ASCII: gramática de
facetas completa, con lectura acotada por línea. Devuelve formato y triángulos.
PNG: firma/IHDR, ancho y alto; JPEG/PDF: firmas. Es identificación inicial, no un
validador exhaustivo de geometría, documentos ni imágenes. No calcula parámetros
de slicer. Otros formatos se guardan como `application/octet-stream`; no se fía
de extensión ni MIME declarado. El rol thumbnail tiene decodificación validada y
normalización propias antes de entrar al almacenamiento genérico.

## Verificación

Las pruebas están en `backend/tests/test_asset_storage.py` y los tests de integración
de Assets y archivos. Usar PostgreSQL y almacenamiento aislados; comprobar Alembic
current y check antes de atribuir un fallo al contrato. Ver
[calidad](../development/quality_es.md) y [biblioteca](asset_library_ui_es.md).
