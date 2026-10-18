# Arquitectura de persistencia

## Alcance

La persistencia de Community utiliza PostgreSQL 17, SQLAlchemy 2.x síncrono,
psycopg 3 y Alembic. Además de la configuración técnica, actualmente persiste
máquinas, insumos, presentaciones, compras, movimientos de stock, cálculos de
costos técnicos y presupuestos. Es un conjunto acotado de capacidades
Community, no un ERP completo ni un dominio de producción implementado.

## Configuración y motor

`DATABASE_URL` es la única fuente de la URL de conexión y debe usar
`postgresql+psycopg://`. Pydantic Settings valida el controlador. El motor
compartido habilita `pool_pre_ping` y no registra SQL por defecto. El registro
puede activarse en desarrollo con `DATABASE_ECHO=true`, teniendo presente que
las sentencias podrían contener datos.

La aplicación nunca ejecuta `metadata.create_all`. Alembic es el único
mecanismo permitido para cambiar el esquema.

## Metadata y modelos

`Base` usa `DeclarativeBase` y una `MetaData` central. No aporta campos
implícitos. Los modelos que Alembic debe descubrir se registran explícitamente
en `app.db.models`.

La convención de nombres es:

| Objeto | Convención |
|---|---|
| Índice | `ix_<tabla>_<columna>` |
| Unicidad | `uq_<tabla>_<columna>` |
| Check | `ck_<tabla>_<nombre>` |
| Clave foránea | `fk_<tabla>_<columna>_<tabla referenciada>` |
| Clave primaria | `pk_<tabla>` |

Los `CheckConstraint` deben recibir un nombre semántico para completar la
convención.

## Identificadores y timestamps

`UUIDPrimaryKeyMixin` define UUIDv4 generado por la aplicación y almacenado con
el tipo UUID nativo de PostgreSQL. UUIDv7 se reconsiderará solo cuando exista
una necesidad y soporte estable que lo justifiquen.

`TimestampMixin` define `created_at` y `updated_at` como
`TIMESTAMP WITH TIME ZONE`. PostgreSQL asigna ambos valores al insertar;
SQLAlchemy actualiza `updated_at` al emitir una modificación ORM. La aplicación
y los contenedores trabajan con semántica UTC.

No se incorporan automáticamente `organization_id`, borrado lógico, usuarios
de auditoría ni versionado optimista.

## Sesiones y transacciones

Existe un único `SessionFactory`. La dependencia `get_db_session` entrega una
sesión por petición y se limita a cerrarla. No confirma transacciones.

- El servicio decide `commit` y `rollback`.
- El repositorio recibe una sesión y puede ejecutar `flush`.
- El repositorio nunca ejecuta `commit`.
- Un error SQLAlchemy se transforma en un error técnico sin exponer la URL ni
  credenciales.

La sesión actúa como frontera transaccional inicial. No se implementa todavía
un patrón `UnitOfWork` adicional ni un repositorio genérico.

## Modelo técnico

`SystemSetting` valida migraciones, UUID, JSONB, timestamps y el patrón de
acceso. Solo admite configuración técnica no sensible. Su `key` es única y su
`value` es JSONB porque el valor técnico puede tener estructura variable.

JSONB no reemplaza el modelado relacional: relaciones y conceptos centrales
del dominio deberán representarse mediante tablas y columnas explícitas.

## Límites

No hay soporte asíncrono, múltiples motores, auditoría de usuario ni soft
delete general. Pedidos, proyectos y producción tienen modelos y servicios
propios. No se agrega infraestructura para conceptos ajenos al alcance vigente.
