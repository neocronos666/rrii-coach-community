# Preparar una prueba del paquete fuera del repositorio

[Instalación](README.md) · [Diseño técnico](distribution_design_es.md) · [Guía para testers](testing_es.md)

Esta página es para quien **prepara** una prueba. El tester recibe un paquete y
sigue el [inicio rápido de usuario](linux_es.md#inicio-rápido). No necesita clonar
el repositorio ni instalar herramientas de programación.

La preparación requiere Python 3.12 o posterior, Docker local, Compose >= 2.20 y
conexión para descargar dependencias la primera vez. Aún no se publicaron las imágenes;
por eso la prueba local usa `--offline` después de construirlas en esa misma PC.

## 1. Generar las imágenes y el paquete

Desde la raíz del repositorio:

```bash
python3 scripts/build-distribution.py --build-images
```

Se construyen localmente las imágenes backend/frontend de la candidata `0.1.0-rc1`
y se descarga la imagen versionada de la base. Este comando no sube nada a un registry.

En `dist/` se generan:

- `rrii-coach-community-0.1.0-rc1-linux-amd64.tar.gz`.
- `rrii-coach-community-0.1.0-rc1-linux-amd64.tar.gz.sha256`.

El paquete contiene doce archivos permitidos; no incluye el checkout, dependencias
de desarrollo ni configuración local. Generar sólo el archivo, si las imágenes ya
están preparadas, es posible con `python3 scripts/build-distribution.py`.

## 2. Copiar, verificar y descomprimir fuera del checkout

La carpeta temporal nueva evita pisar una prueba anterior:

```bash
RRII_TRIAL_DIR="$(mktemp -d "${TMPDIR:-/tmp}/rrii-coach-trial.XXXXXX")"
cp dist/rrii-coach-community-0.1.0-rc1-linux-amd64.tar.gz "$RRII_TRIAL_DIR/"
cp dist/rrii-coach-community-0.1.0-rc1-linux-amd64.tar.gz.sha256 "$RRII_TRIAL_DIR/"
cd "$RRII_TRIAL_DIR"
sha256sum -c rrii-coach-community-0.1.0-rc1-linux-amd64.tar.gz.sha256
tar -xzf rrii-coach-community-0.1.0-rc1-linux-amd64.tar.gz
cd rrii-coach-community
pwd
./install.sh --offline
```

Guardá la ruta que muestra `pwd`. El paquete no monta fuentes del repositorio;
funciona con sus propios archivos y volúmenes. `--offline` sólo evita descargar
imágenes que ya están en el Docker local: no las transfiere a otra PC.
Si la prueba se hace en otra máquina, el responsable debe preparar allí las mismas
imágenes antes de instalar; compartir sólo el tar.gz todavía no alcanza.

Abrí **http://localhost:18080**, o la URL que indique el script si cambiaste el puerto.

## 3. Hacer la prueba humana

1. Creá una máquina de nombre reconocible y un Asset con un archivo de texto.
2. Descargá el archivo, verificá el contenido y guardá las URLs de los registros.
3. Ejecutá `./stop.sh`; los contenedores de esa instalación deben desaparecer.
4. Ejecutá `./start.sh`, abrí las URLs y descargá nuevamente el archivo.
5. Recorré la [prueba funcional](testing_es.md) y ejecutá `./stop.sh` al terminar.
6. Si querés borrar **esa prueba**, ejecutá `./reset.sh`, escribí la frase solicitada
   y volvé con `./start.sh`: la instancia debe quedar vacía.

Informá commit fuente, checksum, sistema, navegador y resultados. No se deduce
aceptación humana de los tests automáticos. Para revisar RAM, verificá que los
contenedores propios terminaron; otros programas y la caché de Linux siguen activos.

La carpeta temporal puede eliminarse al reiniciar. Si querés conservar esta
instalación, mové la carpeta completa a un lugar permanente antes de seguir usándola;
no pierdas su `.env`. Los volúmenes Docker no se borran por mover la carpeta.

## Verificación automatizada del artefacto

Desde la raíz del checkout de preparación:

```bash
python3 scripts/check-distribution.py dist/rrii-coach-community-0.1.0-rc1-linux-amd64.tar.gz
```

El runner crea sus propios datos/volúmenes y los elimina al terminar. Comprueba
instalación, stop/start, reset, puertos y actualización con un esquema histórico
0037. Reutiliza el mismo build etiquetado de nuevo: aún no existe una release binaria
anterior distinta para afirmar compatibilidad entre dos releases publicadas.

## CI y publicación

El workflow manual [prepare-distribution.yml](../../.github/workflows/prepare-distribution.yml)
ordena: tests completos → imágenes locales → paquete → prueba del artefacto → artifact
para revisión. Tiene permisos de lectura y no incluye login, push de imágenes ni
publicación de Release. Preparar o sincronizar este código no publica el paquete.
La publicación de imágenes y releases requiere autorización separada.
