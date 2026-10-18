# Desarrollo con PostgreSQL y Alembic

Todos los comandos se ejecutan dentro de contenedores. El host no necesita
Python, psycopg, SQLAlchemy ni Alembic.

## Configuración

La aplicación obtiene la conexión exclusivamente desde `DATABASE_URL`.
Compose la construye con `POSTGRES_DB`, `POSTGRES_USER` y
`POSTGRES_PASSWORD`. La contraseña real queda en `.env`, que Git ignora.

`DATABASE_ECHO=false` evita registrar sentencias SQL. No activarlo con datos
privados.

## Migraciones de desarrollo

Aplicar hasta la última revisión:

```bash
make db-upgrade
```

Consultar revisión e historial:

```bash
make db-current
make db-history
```

Crear una revisión requiere un mensaje explícito:

```bash
make db-revision MESSAGE="crear tabla técnica"
```

Revisar siempre el archivo generado. La autogeneración no sustituye la revisión
humana.

Revertir una revisión puede destruir datos y requiere confirmación:

```bash
make db-downgrade CONFIRM=DOWNGRADE
```

No editar `alembic_version` ni usar `metadata.create_all`.

El backend no aplica migraciones al arrancar. Su endpoint `/ready` compara las
revisiones actuales con el head y devuelve `503` si faltan migraciones; la
corrección es ejecutar `make db-upgrade`, no usar `stamp` para ocultar una
diferencia de esquema.

## Pruebas aisladas

La integración usa el servicio `db_test` del perfil `test`. Es PostgreSQL 17,
no publica puertos y guarda sus datos en `tmpfs`; no comparte volumen ni
credenciales con desarrollo.

```bash
make test-integration
```

El comando inicia la base aislada, aplica migraciones, ejecuta solo las pruebas
marcadas `integration`, revierte el esquema y detiene el servicio.

Para validar explícitamente el ciclo completo:

```bash
make db-check
```

Ejecuta:

```text
upgrade head → downgrade base → upgrade head → alembic check
```

La última subida queda únicamente en la base efímera de prueba.

## Diagnóstico

Si PostgreSQL de desarrollo no está saludable:

```bash
docker compose ps
docker compose logs db
```

Si Alembic informa diferencias luego de aplicar `head`, revisar que el modelo
esté importado por `app.db.models` y que la migración reproduzca la metadata.
No incluir URLs completas de conexión al compartir logs.

## Migraciones funcionales

`20260814_0002` crea exclusivamente la tabla `machines`. La configuración de
instalación reutiliza `system_settings`, por lo que no necesita otra tabla.
Nunca modificar `20260728_0001` ni una migración ya aplicada: todo cambio nuevo
requiere una revisión posterior.

`20260815_0003` crea `supplies`, `supply_presentations`, `supply_purchases` y
`supply_stock_movements`. Cantidades normalizadas usan `NUMERIC(18,6)` y dinero
usa `NUMERIC(18,4)`. Los constraints garantizan cantidades positivas donde
corresponde, costos no negativos, SKU único y movimientos no nulos.

`20260815_0004` crea `cost_calculations` y `cost_calculation_lines`. Los
snapshots guardan costos unitarios como `NUMERIC(24,8)`, subtotales como
`NUMERIC(18,4)`, monedas, fuentes y referencias. No deben actualizarse ni
eliminarse mediante la API.

`20260815_0005` crea `quotes`, `quote_items`, `quote_adjustments` y la secuencia
global `quote_code_sequence`. La secuencia evita códigos basados en conteos y
produce `Q-AAAA-NNNNNN`; el contador continúa entre años. Los importes
comerciales son snapshots `NUMERIC(18,4)`.

`20260901_0006` crea `orders`, `projects`, `project_components` y
`quote_conversions`, además de secuencias independientes para códigos de pedido
y proyecto. La unicidad de `quote_conversions.quote_id` y las referencias de
origen protegen una sola conversión operativa por presupuesto.


La revisión 20260901_0007 crea production_tasks y la secuencia production_task_code_seq. El origen queda protegido como Order XOR ProjectComponent; las cantidades planificadas son decimales positivas y los parámetros técnicos abiertos usan JSONB.

La revisión 20260901_0008 agrega el índice parcial único que permite una sola ProductionTask in_progress por Machine.

La revisión `20260901_0009` crea `production_task_dependencies`. Su clave
primaria compuesta evita duplicados, dos FKs `RESTRICT` conservan la integridad
de tareas y un CHECK impide auto-dependencias. La aciclicidad y la pertenencia
al mismo trabajo se validan en el servicio.
