# Miniaturas de revisiones de Assets

10B.9: una miniatura opcional por revisión, mediante el rol explícito `thumbnail`
de AssetRevisionFile. No hay selección implícita entre adjuntos media ni render de
STL. Se conserva la deduplicación de StoredFile y el almacenamiento local por hash.

## Carga, lectura e historia

Todas las rutas usan el prefijo `/api/v1`.

`POST /assets/{asset_id}/revisions/{revision_id}/files?filename=preview.png&role=thumbnail`
recibe los bytes como `application/octet-stream`, igual que los adjuntos existentes.
Acepta PNG/JPEG estáticos, independientemente del nombre. El nombre es lógico;
se recomienda terminarlo en `.png` porque el contenido guardado siempre es PNG.
El original no se conserva mediante este rol; para conservarlo debe adjuntarse
aparte como media/source. El hash y tamaño de la respuesta identifican el derivado.

Límites: el menor entre ASSET_MAX_UPLOAD_BYTES y 10 MiB de entrada; hasta 16 millones
de píxeles. El PNG resultante conserva proporción, no agranda imágenes pequeñas,
normaliza orientación EXIF y cabe en 512 × 512. Conserva transparencia; elimina
metadatos EXIF, perfiles y textos. No interpreta SVG ni imágenes animadas.
El límite general de almacenamiento también se aplica al derivado.

`GET /assets/{asset_id}/revisions/{revision_id}/thumbnail` sirve exclusivamente el
PNG normalizado como `image/png`, inline y con nosniff. Si no hay miniatura devuelve
404. Listado, comparación y descarga convencional de archivos incluyen el nuevo
rol; el endpoint de descarga sigue siendo attachment, incluso para thumbnails.

Una revisión admite una sola miniatura. Mismo nombre y mismos bytes normalizados
son un reintento y devuelven la referencia original; diferente nombre o contenido
produce 409. Un archivo existente de otro rol con ese nombre también produce 409.
Para cambiar la miniatura se crea otra revisión y se carga allí. Crear una revisión
normal comienza sin archivos; restaurar copia los adjuntos y la referencia a la
miniatura histórica. El archivado no elimina archivos.

## Consistencia y migración

0038 amplía el CHECK de roles e introduce un índice único parcial por revisión
para thumbnail. No modifica migraciones aplicadas ni transforma adjuntos antiguos.
Downgrade rechaza mientras existan referencias thumbnail, para no perder historia.

Normalización previa al lock; publicación y referencia dentro de la transacción
del servicio, con lock de Asset y de hash existentes. Si falla el commit no se
elimina un blob que pueda estar compartido. Los temporales de storage se limpian;
un blob publicado sin referencia puede recuperarse al reintentar. GC sigue diferido.
Una lectura verifica hash/tamaño y responde 503 ante contenido ausente o corrupto.

Pillow 12.3.0 queda fijado en uv.lock. Se usan sus APIs de [apertura y thumbnail](https://pillow.readthedocs.io/en/stable/reference/Image.html)
y normalización EXIF; no se desactiva su protección contra imágenes excesivas.
La decodificación y el límite propio de píxeles preceden al guardado del derivado.
La interfaz de Biblioteca queda para el siguiente incremento; este contrato no
implica que ya exista una pantalla de carga.
