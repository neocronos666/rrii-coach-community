# Configuración de instalación

Acceso: menú Más → Configuración de instalación, ruta `/settings`.
El botón de configuración de la barra superior conserva apariencia y preferencias
locales del navegador; esta pantalla modifica valores compartidos del backend.

Campos: negocio, moneda, país, región, zona horaria IANA, idioma, política/tipo/
valor de seña, electricidad por kWh, tarifas por hora de diseño, preproducción,
posproducción, ensamblado, soporte, capacitación y pretransporte, markup.
El idioma persistido no agrega traducciones: la interfaz sigue en castellano.

GET carga la configuración completa. Si falla la carga inicial no aparece el
formulario ni se permite guardar defaults inventados. Datos guardados permite
revisar la respuesta actual sin sobrescribir el borrador. Cargar valores guardados
requiere confirmación y descarta cambios locales; navegar con cambios también avisa.

PUT reemplaza todos los campos. Cantidades monetarias se envían como texto y
los opcionales vacíos como null. Cero permanece explícito. El servidor valida
seña, moneda, zona y valores; frontend no calcula costos, señas ni conversiones.
Cambiar moneda no convierte tarifas ni precios históricos. La confirmación cubre
el reemplazo completo y los efectos sobre operaciones futuras; los snapshots
históricos no se recalculan desde esta pantalla.

Antes de enviar PUT se consulta la configuración y se compara con el snapshot
que originó el formulario. Si cambió, se impide esa escritura y se solicita
revisar/cargar los valores actuales antes de editar nuevamente. La API no ofrece
ETag/versionado: aún existe una carrera entre consulta y escritura, y no se
promete exclusión mutua entre sesiones.

Una respuesta incierta conserva un aviso por pestaña y bloquea nuevas escrituras.
No se reenvía PUT automáticamente. Consultar, revisar y reconocer el aviso permite
recuperar el formulario; cargar valores guardados incorpora lo confirmado por API.
Se reutiliza el guard de inventario con scope installation-settings. Al bloquearse
sessionStorage se informa que el aviso sólo se mantiene en memoria.

No se cambia backend, esquema, contratos ni dependencias. No hay autenticación,
conversor de monedas ni nuevas políticas de edición Community.
