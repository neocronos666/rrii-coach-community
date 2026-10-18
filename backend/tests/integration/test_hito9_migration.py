import os
import subprocess
import sys
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import MetaData, Table, create_engine, text

from app.db.engine import engine

pytestmark = pytest.mark.integration


def test_existing_tasks_keep_lifecycle_without_fabricated_runs() -> None:
    assert engine.url.database == "rrii_coach_test"
    database = "rrii_coach_migration_" + uuid4().hex
    migration_url = engine.url.set(database=database)
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as admin:
        admin.exec_driver_sql(f'CREATE DATABASE "{database}"')
    isolated = create_engine(migration_url)
    environment = {
        **os.environ,
        "DATABASE_URL": migration_url.render_as_string(hide_password=False),
    }

    def migrate(revision: str, direction: str = "upgrade") -> None:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", direction, revision],
            env=environment,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr

    try:
        migrate("20260908_0012")
        # Sembrar el contrato histórico reflejado, no modelos/API de otra revisión.
        with isolated.begin() as connection:
            metadata = MetaData()
            tables = {
                name: Table(name, metadata, autoload_with=connection)
                for name in (
                    "cost_calculations",
                    "cost_calculation_lines",
                    "quotes",
                    "quote_items",
                    "orders",
                    "quote_conversions",
                )
            }
            calculation_id, quote_id, item_id, order_id = (uuid4() for _ in range(4))
            tables_values = {
                "cost_calculations": dict(
                    id=calculation_id,
                    calculation_type="technical",
                    complete=True,
                    multi_currency=False,
                    warnings=[],
                    calculated_at=datetime.now(UTC),
                ),
                "cost_calculation_lines": dict(
                    id=uuid4(),
                    calculation_id=calculation_id,
                    position=0,
                    category="extra",
                    description="Histórico",
                    quantity=Decimal(1),
                    unit="item",
                    unit_cost=Decimal(100),
                    currency="ARS",
                    subtotal=Decimal(100),
                    source="manual",
                    complete=True,
                ),
                "quotes": dict(
                    id=quote_id,
                    code="Q-HIST",
                    title="Histórico",
                    status="approved",
                    currency="ARS",
                    technical_cost_total=Decimal(100),
                    markup_percentage=Decimal(0),
                    markup_amount=Decimal(0),
                    subtotal_after_markup=Decimal(100),
                    suggested_price=Decimal(100),
                    final_price=Decimal(100),
                    final_price_overridden=False,
                    deposit_policy="none",
                    approved_at=datetime.now(UTC),
                ),
                "quote_items": dict(
                    id=item_id,
                    quote_id=quote_id,
                    description="Histórico",
                    quantity=Decimal(1),
                    cost_calculation_id=calculation_id,
                    technical_unit_cost=Decimal(100),
                    technical_total_cost=Decimal(100),
                    currency="ARS",
                    position=0,
                ),
                "orders": dict(
                    id=order_id,
                    code="O-HIST",
                    source_quote_id=quote_id,
                    source_quote_item_id=item_id,
                    title="Histórico",
                    description="Histórico",
                    status="pending",
                    quantity=Decimal(1),
                    currency="ARS",
                    technical_unit_cost=Decimal(100),
                    technical_total_cost=Decimal(100),
                    quoted_suggested_price=Decimal(100),
                    quoted_final_price=Decimal(100),
                ),
                "quote_conversions": dict(
                    id=uuid4(),
                    quote_id=quote_id,
                    target_type="order",
                    order_id=order_id,
                ),
            }
            for name, values in tables_values.items():
                connection.execute(tables[name].insert().values(**values))
            for state in ("queued", "in_progress", "physically_completed"):
                connection.execute(
                    text(
                        "INSERT INTO production_tasks "
                        "(id, code, order_id, task_type, title, planned_quantity, "
                        "queue_position, status) VALUES "
                        "(:id, :code, :order_id, 'manual', 'Histórica', 10, 1, :status)"
                    ),
                    {
                        "id": uuid4(),
                        "code": state,
                        "order_id": order_id,
                        "status": state,
                    },
                )
        migrate("head")
        with isolated.connect() as connection:
            states = connection.execute(
                text("SELECT code, status, execution_mode FROM production_tasks")
            ).all()
            assert len(states) == 3
            assert connection.execute(
                text("SELECT demand_quantity, demand_unit FROM cost_calculations")
            ).one() == (None, None)
            assert connection.scalar(
                text("SELECT technical_total_cost FROM orders")
            ) == Decimal(100)
            assert all(
                code == status and mode == "legacy" for code, status, mode in states
            )
            assert connection.scalar(text("SELECT count(*) FROM production_runs")) == 0
            assert (
                connection.scalar(
                    text(
                        "SELECT column_default FROM information_schema.columns "
                        "WHERE table_name='production_tasks' "
                        "AND column_name='execution_mode'"
                    )
                )
                == "'runs'::character varying"
            )
        # Base anterior al ledger: una salida real debe migrar una sola vez.
        migrate("20260909_0015", "downgrade")
        product_id, variant_id, task_id, run_id = (uuid4() for _ in range(4))
        with isolated.begin() as connection:
            connection.execute(
                text("INSERT INTO products (id,name) VALUES (:id,'Físico')"),
                {"id": product_id},
            )
            connection.execute(
                text(
                    "INSERT INTO product_variants (id,product_id,name,base_unit) "
                    "VALUES (:id,:product,'Única','unit')"
                ),
                {"id": variant_id, "product": product_id},
            )
            connection.execute(
                text(
                    "INSERT INTO production_tasks "
                    "(id,code,order_id,task_type,title,planned_quantity,planned_unit,"
                    "queue_position,status,output_variant_id) VALUES "
                    "(:id,'REAL',:order,'manual','Fabricada',10,'unit',1,"
                    "'physically_completed',:variant)"
                ),
                {"id": task_id, "order": order_id, "variant": variant_id},
            )
            connection.execute(
                text(
                    "INSERT INTO production_runs "
                    "(id,task_id,request_id,request_payload,"
                    "parameters,output_variant_id,unit,status,started_at,ended_at,"
                    "good_quantity,failed_quantity) VALUES "
                    "(:id,:task,:request,'{}','{}',:variant,'unit','closed',"
                    "now()-interval '1 minute',now(),12,1)"
                ),
                {
                    "id": run_id,
                    "task": task_id,
                    "request": uuid4(),
                    "variant": variant_id,
                },
            )
        migrate("head")
        migrate("head")
        with isolated.connect() as connection:
            rows = connection.execute(
                text("SELECT variant_id, quantity, run_id FROM product_stock_movements")
            ).all()
            assert [tuple(row) for row in rows] == [(variant_id, 12, run_id)]
            assert (
                connection.scalar(
                    text(
                        "SELECT count(*) FROM production_tasks "
                        "WHERE execution_mode='legacy'"
                    )
                )
                == 3
            )
    finally:
        isolated.dispose()
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as admin:
            admin.exec_driver_sql(f'DROP DATABASE "{database}"')
