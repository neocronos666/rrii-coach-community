# Arquitectura del backend

## Stack y estructura real

Python 3.13, FastAPI, SQLAlchemy 2.x, Alembic, Pydantic 2 y PostgreSQL 17.
Dependencias y herramientas: `backend/pyproject.toml` y `backend/uv.lock`.

```text
backend/app/
├── api/           # salud y registro de routers
├── core/          # configuración y validaciones compartidas
├── db/            # sesión, modelos técnicos y persistencia
├── modules/
│   ├── assets/
│   ├── costing/
│   ├── installation/
│   ├── machines/
│   ├── options/
│   ├── orders/
│   ├── production/
│   ├── products/
│   ├── projects/
│   ├── quick_quotes/
│   ├── quotes/
│   ├── recipes/
│   └── supplies/
├── schemas/
└── main.py
```

Los routers traducen HTTP; los schemas validan contratos. Los servicios aplican
reglas y controlan transacciones; los repositorios encapsulan consultas y no
confirman transacciones. Los modelos usan las APIs tipadas de SQLAlchemy 2.x.

La configuración funcional pertenece a `installation`; las claves técnicas de
`SystemSetting` no sustituyen ese contrato. Los archivos se gestionan en
`assets/storage.py`. No se crean módulos vacíos para capacidades no implementadas.

## Validación

pytest, Ruff y mypy comprueban pruebas, estilo, formato y tipos. Las pruebas de
integración requieren PostgreSQL aislado y esquema instalado mediante Alembic.
Los comandos de desarrollo están en el Makefile y las guías de
[calidad](../development/quality_es.md) y [base de datos](../development/database_es.md).
