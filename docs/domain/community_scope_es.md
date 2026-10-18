# Alcance de RRII-Coach Community

Community organiza el trabajo local de un taller maker para una persona.
No tiene login ni administración de usuarios. Admite hasta dos máquinas activas;
la API aplica el límite al crear o reactivar una máquina.

## Capacidades implementadas

- Biblioteca de Assets: categorías, familias, compatibilidades, composición,
  atribución, archivos, miniaturas y revisiones históricas.
- Productos y variantes, opciones configurables, servicios y recetas.
- Cálculos técnicos, preview de recetas, Quick Quotes con revisiones y
  formalización explícita, presupuestos con markup y condiciones comerciales.
- Conversión única y explícita de presupuesto a pedido o proyecto.
- Planificación, dependencias, cola, intentos de producción y consumos reales.
- Test Print de receta completa y promoción explícita a stock.
- Insumos, presentaciones, compras, movimientos, reservas, stock de productos,
  asignaciones y entregas.
- Configuración de instalación y preferencias de interfaz; dashboard de registros.

## Límites vigentes

La persistencia usa PostgreSQL y archivos locales. No se controlan máquinas ni
se realiza slicing. No hay emisión fiscal, gestión de organizaciones, conectores
externos, dispositivos o procesos de sincronización. La aplicación no proporciona
un sistema general de auditoría de identidad del operador.

Los estados y reglas se describen en los documentos de módulos y en OpenAPI.
El alcance funcional está congelado; la etapa actual se concentra en estabilidad,
instalación, pruebas, documentación y preparación de release.
