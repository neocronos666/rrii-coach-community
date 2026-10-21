RRII-Coach Community — prueba local en Linux de 64 bits

1. Descomprimí el paquete y abrí una terminal en esa carpeta.
2. Ejecutá: ./install.sh
3. Abrí la dirección que aparece (normalmente http://localhost:18080).
4. Al terminar: ./stop.sh
5. Para volver: ./start.sh

Necesitás Docker y Docker Compose. Si faltan, install.sh indica la guía;
no instala paquetes ni modifica el sistema. Pedí ayuda a un administrador.
Debian: https://docs.docker.com/engine/install/debian/
Ubuntu: https://docs.docker.com/engine/install/ubuntu/
Mint 22 usa base Ubuntu 24.04; Docker no declara soporte oficial para Mint.
El paquete se está validando en Mint 22.2 amd64. Otras distribuciones aún
requieren su propia validación antes de anunciar soporte de la RC.

No necesitás instalar Python, Node ni una base de datos.
Conservá esta carpeta: .env identifica tu instalación y contiene una contraseña.
Para cambiar de puerto, editá sólo RRII_PORT en .env y repetí el arranque.
No cambies el nombre de instalación ni la contraseña después de crear datos.

Actualizar: descargá el nuevo paquete, copiá sus archivos sobre esta carpeta
(sin borrar .env ni archivos ocultos), y ejecutá ./update.sh.
También podés indicar la versión que te dio el responsable: ./update.sh 0.1.0-rc2
Pide confirmación, guarda respaldo y migra. No hay rollback automático.
No compartas .env, backups ni los logs sin revisarlos antes.

Diagnóstico: ./status.sh
BORRAR TODOS TUS DATOS: ./reset.sh (pide confirmación explícita).
stop.sh nunca borra datos. reset.sh no borra imágenes ni otros proyectos.

Esta candidata todavía no se publicó. En una prueba preparada localmente,
el responsable puede pedirte ./install.sh --offline: usa imágenes ya cargadas.
Datos demo aún no disponibles. El README y las condiciones de evaluación
se incluyen en LICENSE; esta preparación no cambia las condiciones vigentes.
