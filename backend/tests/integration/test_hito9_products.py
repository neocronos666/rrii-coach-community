from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select

from app.db.session import SessionFactory
from app.main import app
from app.modules.products.models import Product, ProductVariant

pytestmark = pytest.mark.integration


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as client:
        yield client
    with SessionFactory() as session:
        session.execute(delete(ProductVariant))
        session.execute(delete(Product))
        session.commit()


def create(client: TestClient, sku: str | None = None) -> dict[str, object]:
    response = client.post(
        "/api/v1/products",
        json={
            "name": " Pikachu ",
            "initial_variant": {
                "name": "Rojo / PLA",
                "base_unit": "unit",
                "sku": sku,
                "attributes": {"color": "rojo", "material": "PLA"},
            },
        },
    )
    assert response.status_code == 201, response.text
    return dict(response.json())


def test_catalog_atomic_creation_and_sku_conflict(client: TestClient) -> None:
    first = create(client, " pika-rojo ")
    assert first["name"] == "Pikachu"
    variants = client.get(f"/api/v1/products/{first['id']}/variants").json()
    assert len(variants) == 1
    assert variants[0]["sku"] == "PIKA-ROJO"
    duplicate = client.post(
        "/api/v1/products",
        json={
            "name": "No debe persistir",
            "initial_variant": {
                "name": "Otra",
                "base_unit": "unit",
                "sku": "pika-rojo",
            },
        },
    )
    assert duplicate.status_code == 409
    with SessionFactory() as session:
        assert session.scalar(select(func.count()).select_from(Product)) == 1
        assert session.scalar(select(func.count()).select_from(ProductVariant)) == 1
    create(client)
    create(client)


def test_variants_identity_activation_and_pagination(client: TestClient) -> None:
    product = create(client)
    path = f"/api/v1/products/{product['id']}"
    added = client.post(
        path + "/variants",
        json={
            "name": "Azul / PLA",
            "base_unit": "unit",
            "attributes": {"color": "azul"},
        },
    )
    assert added.status_code == 201
    variant_path = f"/api/v1/product-variants/{added.json()['id']}"
    assert client.patch(path, json={"active": False}).status_code == 200
    assert client.get(variant_path).json()["active"] is True
    assert client.patch(variant_path, json={"active": False}).status_code == 200
    assert client.patch(path, json={"active": True}).status_code == 200
    assert client.get(variant_path).json()["active"] is False
    assert len(client.get(path + "/variants", params={"active": True}).json()) == 1
    assert len(client.get(path + "/variants", params={"limit": 1}).json()) == 1
    assert len(client.get("/api/v1/products", params={"search": "kac"}).json()) == 1
    assert client.get("/api/v1/products", params={"offset": 1}).json() == []
    for field, value in [
        ("base_unit", "g"),
        ("product_id", str(uuid4())),
        ("stock", "4"),
    ]:
        assert client.patch(variant_path, json={field: value}).status_code == 422
    assert client.delete(path).status_code == 405
    assert client.delete(variant_path).status_code == 405


@pytest.mark.parametrize(
    "variant",
    [
        {"name": " ", "base_unit": "unit"},
        {"name": "A", "base_unit": "ton"},
        {"name": "A", "base_unit": "unit", "sku": " "},
        {"name": "A", "base_unit": "unit", "attributes": {"color": {"name": "red"}}},
    ],
)
def test_invalid_variant_rejected(
    client: TestClient, variant: dict[str, object]
) -> None:
    assert (
        client.post(
            "/api/v1/products",
            json={
                "name": "Producto",
                "initial_variant": variant,
            },
        ).status_code
        == 422
    )


def test_not_found_and_null_updates(client: TestClient) -> None:
    missing = str(uuid4())
    assert client.get(f"/api/v1/products/{missing}").status_code == 404
    assert client.get(f"/api/v1/products/{missing}/variants").status_code == 404
    assert client.get(f"/api/v1/product-variants/{missing}").status_code == 404
    product = create(client)
    path = f"/api/v1/products/{product['id']}"
    variant = client.get(path + "/variants").json()[0]
    for field in ["active", "name", "attributes"]:
        assert (
            client.patch(
                f"/api/v1/product-variants/{variant['id']}", json={field: None}
            ).status_code
            == 422
        )
