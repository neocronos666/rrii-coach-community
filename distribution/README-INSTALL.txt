RRII-Coach Community — empezar en Linux

1. Descomprimí el paquete y abrí una terminal en esa carpeta.
2. Ejecutá: ./install.sh
3. Abrí la dirección mostrada (normalmente http://localhost:18080).
4. Al terminar: ./stop.sh       Para volver: ./start.sh

Todavía no hay imágenes ni Release candidata publicadas. Si recibiste una
prueba preparada localmente, el responsable te indicará ./install.sh --offline.
Ese modo usa imágenes ya cargadas: no descarga ni compila nada.

Necesitás Docker y Compose; no necesitás Python, Node ni una base de datos.
Si falta Docker, el script da una guía y no modifica el sistema:
Debian: https://docs.docker.com/engine/install/debian/
Ubuntu: https://docs.docker.com/engine/install/ubuntu/
Mint requiere revisar su base Ubuntu. El paquete se probó en Mint 22.2 amd64;
Debian/Ubuntu siguen pendientes de validación propia. ARM no está incluido.

Conservá esta carpeta y su .env: identifica tus datos y contiene una contraseña.
Si el puerto está ocupado, cambiá sólo RRII_PORT en .env y repetí el comando.
stop.sh conserva datos. reset.sh LOS BORRA y pide confirmación explícita.

Para consultar versión y estado: ./status.sh
Para actualizar con un paquete nuevo: conservar .env y archivos de estado,
copiar los archivos nuevos sobre esta carpeta y ejecutar ./update.sh.
Pide confirmación y guarda respaldo. No hay rollback automático del esquema.

Ayuda: https://github.com/neocronos666/rrii-coach-community/tree/main/docs/installation
Reportes: https://github.com/neocronos666/rrii-coach-community/issues
No adjuntes .env, contraseñas, backups ni datos privados a los reportes.
Los datos demo siguen pendientes. Condiciones de evaluación: LICENSE.
