# Instrucciones para agentes

Estas instrucciones aplican a todo el repositorio.

- Community está funcionalmente congelado. Sólo se permiten bugs, cierre de
  flujos existentes, estabilidad, UX menor sin ampliar alcance, refactors
  necesarios, instalación, testing, documentación, empaquetado, seguridad y
  CI/CD. Una nueva decisión funcional requiere checkpoint y consulta antes de
  implementarla y registrar los resultados de validación de cada cambio.

- La estabilización y las validaciones deben ejecutarse localmente. No depender
  de servidores remotos.

- Escribir en castellano la documentación y los mensajes destinados al
  desarrollador.
- Utilizar inglés en código, módulos, clases, variables y contratos técnicos
  cuando sea la convención adecuada.
- Mantener una arquitectura API First y modular por dominio.
- Mantener exclusivamente el alcance Community, sin capacidades ocultas ni
  flags de distribución.
- No agregar autenticación a Community sin una decisión posterior explícita.
- No implementar conectores ERP ni crear carpetas de integración previstas.
- No agregar Redis, Celery ni workers externos en esta etapa.
- No introducir lógica de negocio en el frontend.
- Ejecutar pruebas, lint y verificación de tipos después de cada cambio.
- No ejecutar operaciones destructivas sobre datos o volúmenes sin
  autorización.
- Trabajar en las fases de análisis, preimplementación, implementación, pruebas
  y cierre.
- Preservar cambios ajenos a la tarea y justificar cualquier eliminación.
- Usar las APIs modernas y tipadas de SQLAlchemy 2.x.
- No usar `metadata.create_all`; todo cambio de esquema debe pasar por Alembic.
- No sustituir PostgreSQL por SQLite en pruebas de integración.
- Los repositorios no confirman transacciones; los servicios controlan
  `commit` y `rollback`.
- No crear repositorios genéricos ni unidades de trabajo prematuramente.
- Almacenar timestamps persistentes con zona horaria y semántica UTC.
- No guardar secretos en JSONB ni en configuraciones técnicas.
- Nunca utilizar `float` para dinero; usar `Decimal` y `NUMERIC`.
- Aplicar los límites Community en el backend, sin flags de distribución.
- No agregar sensores, cámaras ni consumos como columnas de `Machine`.
- No modificar migraciones que ya hayan sido aplicadas.
- Preferir `VARCHAR` y enums Python frente a enums PostgreSQL cuando facilite
  la evolución del dominio.
- Derivar el stock de movimientos; nunca modificar una existencia acumulada.
- Utilizar `Decimal` también para cantidades persistentes.
- No cambiar la unidad base de un insumo después de su primer movimiento.
- No convertir unidades de dimensiones incompatibles sin información explícita.
- No borrar insumos que posean historia.
- Distinguir siempre costo técnico de precio de venta.
- Un cálculo de costos nunca consume ni reserva stock.
- Tratar `CostCalculation` como snapshot inmutable; nunca recalcularlo en silencio.
- No sumar ni convertir monedas distintas sin un provider explícito.
- Representar fuentes faltantes como líneas incompletas, nunca como costo cero.
- `CostCalculation` nunca se modifica desde el módulo de presupuestos.
- Un presupuesto histórico nunca recalcula sus costos y, aprobado, es inmutable.
- Distinguir costo técnico, precio sugerido y precio final.
- Community aplica markup, no margen empresarial.
- Aprobar un presupuesto no crea pedidos, proyectos ni producción.
- Presupuestar no reserva ni consume stock.
- Aprobar un presupuesto no crea Order ni Project automáticamente.
- La conversión Quote a Order o Project es explícita y ocurre una sola vez.
- Un Quote con un item se convierte en Order; con dos o más, en Project.
- Order y Project preservan snapshots del Quote y nunca recalculan históricos.
- La conversión no consume o reserva stock ni crea producción.
- Order y Project no se crean directamente por API en Community.
- ProductionTask es genérica y no equivale a impresión 3D.
- ProductionTask pertenece exactamente a Order XOR ProjectComponent.
- ProductionTask representa objetivos; Runs representan ejecuciones. Las reservas
  y los consumos se gestionan mediante sus servicios de dominio.
- ProductionTask no recalcula costos históricos.
- Una Machine puede tener como máximo un Run abierto o una tarea legacy in_progress.
- Una tarea runs paused no ocupa Machine; no se pausa con Run abierto. Legacy conserva la validación al reanudar.
- physically_completed significa fin físico, no cierre final.
- Los estados de ProductionTask cambian únicamente mediante reglas del servicio.
- Crear ProductionTask sólo desde rutas parent-scoped de Order o ProjectComponent.
- No modificar status de ProductionTask mediante PATCH.
- `finish` sólo opera sobre tareas legacy. Las tareas runs se completan por buenas acumuladas al cerrar Runs.
- No exponer DELETE para ProductionTask.
- Las dependencias de ProductionTask forman un DAG.
- Una dependencia sólo une tareas del mismo Order o del mismo Project.
- Tareas de distintos ProjectComponents del mismo Project pueden depender entre sí.
- ProductionTask.start exige prerrequisitos physically_completed.
- ProductionTask.resume no revalida dependencias.
- Finalizar un prerrequisito no inicia automáticamente tareas dependientes.
