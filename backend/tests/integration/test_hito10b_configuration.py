from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.db.exceptions import PersistenceError
from app.db.session import SessionFactory
from app.modules.assets.schemas import AssetCreate
from app.modules.assets.service import AssetService
from app.modules.options.configuration_models import ProductOption, ProductOptionValue
from app.modules.options.configuration_schemas import (
    ConfigurationResolveInput,
    ProductConfigurationInput,
    ResolvedOptionValue,
    SelectedOptionValue,
)
from app.modules.options.configuration_service import ProductConfigurationService
from app.modules.quotes.models import Quote
from tests.integration import test_hito10b_options as catalog_tests

pytestmark = pytest.mark.integration
client = catalog_tests.client


def product(client: TestClient) -> str:
    result = client.post(
        "/api/v1/products",
        json={
            "name": "Figura",
            "initial_variant": {"name": "PLA", "base_unit": "unit"},
        },
    )
    assert result.status_code == 201, result.text
    return str(result.json()["id"])


def option(client: TestClient, name: str, count: int = 3) -> dict[str, Any]:
    definition_id = catalog_tests.definition(client, name)
    values = []
    for index in range(count):
        response = client.post(
            f"{catalog_tests.ROOT}/{definition_id}/values", json={"name": str(index)}
        )
        assert response.status_code == 201
        values.append({"value_id": response.json()["id"]})
    return {"definition_id": definition_id, "values": values}


def path(product_id: str) -> str:
    return f"/api/v1/products/{product_id}/configuration"


def configure(
    client: TestClient, product_id: str, options: list[dict[str, Any]]
) -> dict[str, Any]:
    response = client.put(path(product_id), json={"options": options})
    assert response.status_code == 200, response.text
    return dict(response.json())


def selections(
    entry: dict[str, Any], count: int, quantity: str = "1"
) -> dict[str, Any]:
    return {
        "definition_id": entry["definition_id"],
        "values": [
            {"value_id": value["value_id"], "quantity": quantity}
            for value in entry["values"][:count]
        ],
    }


@pytest.mark.parametrize(
    "minimum,maximum,counts",
    [
        (0, 1, [0, 1]),
        (1, 1, [1]),
        (0, None, [0, 1, 2, 3]),
        (1, None, [1, 2, 3]),
        (2, 3, [2, 3]),
    ],
)
def test_cardinality_counts_values_and_preserves_quantities(
    client: TestClient, minimum: int, maximum: int | None, counts: list[int]
) -> None:
    product_id = product(client)
    entry = option(client, "Accesorios")
    entry.update(min_selections=minimum, max_selections=maximum)
    configure(client, product_id, [entry])
    for count in range(4):
        result = client.post(
            path(product_id) + "/resolve",
            json={"selections": [selections(entry, count, "2.5")]},
        )
        assert result.status_code == (200 if count in counts else 409), result.text
        if count in counts:
            resolved = result.json()["selections"][0]["values"]
            assert len(resolved) == count
            assert all(
                Decimal(value["quantity"]) == Decimal("2.5") for value in resolved
            )
            assert all(value["asset_id"] is None for value in resolved)


def test_defaults_explicit_empty_clear_and_product_isolation(
    client: TestClient,
) -> None:
    first, second = product(client), product(client)
    entry = option(client, "Sombreros")
    entry["values"][0]["default_quantity"] = "2"
    configure(client, first, [entry])
    assert client.get(path(second)).json()["options"] == []
    result = client.post(path(first) + "/resolve", json={}).json()
    assert result["selections"][0]["values"][0]["quantity"] == "2.000000"
    empty = client.post(
        path(first) + "/resolve", json={"selections": [selections(entry, 0)]}
    )
    assert empty.status_code == 200
    assert empty.json()["selections"][0]["values"] == []
    configure(client, first, [])
    assert client.get(path(first)).json()["options"] == []
    assert client.post(path(first) + "/resolve", json={}).json()["selections"] == []
    with SessionFactory() as session:
        assert session.scalar(select(func.count()).select_from(Quote)) == 0


@pytest.mark.parametrize(
    "changes",
    [
        {"min_selections": -1},
        {"min_selections": 2, "max_selections": 1},
        {"min_selections": 4, "max_selections": None},
        {"max_selections": True},
        {"context_asset_id": str(uuid4()), "context_definition_id": str(uuid4())},
    ],
)
def test_invalid_configuration_is_not_persisted(
    client: TestClient, changes: dict[str, Any]
) -> None:
    product_id = product(client)
    entry = option(client, "A")
    before = configure(client, product_id, [entry])
    assert (
        client.put(
            path(product_id), json={"options": [{**entry, **changes}]}
        ).status_code
        == 422
    )
    assert client.get(path(product_id)).json() == before


def test_defaults_duplicates_and_invalid_values(client: TestClient) -> None:
    product_id = product(client)
    entry, other = option(client, "A"), option(client, "B")
    duplicate = {**entry, "values": [entry["values"][0], entry["values"][0]]}
    assert (
        client.put(path(product_id), json={"options": [duplicate]}).status_code == 422
    )
    assert (
        client.put(path(product_id), json={"options": [entry, entry]}).status_code
        == 422
    )
    bad_defaults = {
        **entry,
        "values": [{**v, "default_quantity": "1"} for v in entry["values"]],
    }
    assert (
        client.put(path(product_id), json={"options": [bad_defaults]}).status_code
        == 422
    )
    wrong_value = {**entry, "values": other["values"]}
    assert (
        client.put(path(product_id), json={"options": [wrong_value]}).status_code == 404
    )
    configure(client, product_id, [entry])
    for selection in (
        selections(other, 1),
        {"definition_id": entry["definition_id"], "values": other["values"][:1]},
    ):
        assert (
            client.post(
                path(product_id) + "/resolve", json={"selections": [selection]}
            ).status_code
            == 409
        )
    chosen = selections(entry, 1)
    for selection_list in (
        [chosen, chosen],
        [{**chosen, "values": chosen["values"] * 2}],
    ):
        assert (
            client.post(
                path(product_id) + "/resolve", json={"selections": selection_list}
            ).status_code
            == 422
        )
    for quantity in ("0", "-1", "NaN", "1.0000001", "1000000000000"):
        assert (
            client.post(
                path(product_id) + "/resolve",
                json={"selections": [selections(entry, 1, quantity)]},
            ).status_code
            == 422
        )


def physical_value(
    client: TestClient, entry: dict[str, Any], index: int, label: str
) -> dict[str, Any]:
    family = client.post("/api/v1/asset-families", json={"name": label}).json()["id"]
    value_id = entry["values"][index]["value_id"]
    assert (
        client.patch(
            f"{catalog_tests.ROOT}/{entry['definition_id']}/values/{value_id}",
            json={"family_id": family},
        ).status_code
        == 200
    )
    response = client.post("/api/v1/assets", json={"name": label, "family_id": family})
    assert response.status_code == 201
    return dict(response.json())


def test_head_selection_changes_hat_adaptation_and_revision(client: TestClient) -> None:
    product_id = product(client)
    head, hat = option(client, "Cabeza", 2), option(client, "Sombrero", 1)
    pikachu = physical_value(client, head, 0, "Cabeza Pikachu")
    raichu = physical_value(client, head, 1, "Cabeza Raichu")
    gaucho_p = physical_value(client, hat, 0, "Gaucho")
    gaucho_r = client.post(
        "/api/v1/assets",
        json={"name": "Gaucho Raichu", "family_id": gaucho_p["family_id"]},
    ).json()
    for child, target in ((gaucho_p, pikachu), (gaucho_r, raichu)):
        assert (
            client.put(
                f"/api/v1/assets/{child['id']}/compatibilities/{target['id']}"
            ).status_code
            == 200
        )
    head["min_selections"] = 1
    hat.update(min_selections=1, context_definition_id=head["definition_id"])
    configure(client, product_id, [hat, head])
    previous = None
    for head_index, expected in ((0, gaucho_p), (1, gaucho_r)):
        request = {
            "selections": [
                selections(hat, 1),
                {
                    "definition_id": head["definition_id"],
                    "values": [head["values"][head_index]],
                },
            ]
        }
        response = client.post(path(product_id) + "/resolve", json=request)
        assert response.status_code == 200, response.text
        result = response.json()["selections"]
        assert result[0]["definition_id"] == head["definition_id"]
        assert result[1]["values"][0]["asset_id"] == expected["id"]
        assert result[1]["values"][0]["revision_id"] == expected["current_revision_id"]
        assert (
            client.post(path(product_id) + "/resolve", json=request).json()
            == response.json()
        )
        previous = result[1]["values"][0]["revision_id"]
    updated = client.post(
        f"/api/v1/assets/{gaucho_r['id']}/revisions", json={"note": "Corrección"}
    ).json()
    current = client.post(path(product_id) + "/resolve", json=request).json()
    assert current["selections"][1]["values"][0]["revision_id"] == updated["id"]
    assert previous != updated["id"]
    before_clear = client.get(path(product_id)).json()
    assert len(before_clear["options"]) == 2
    configure(client, product_id, [])


def test_missing_ambiguous_and_archived_implementations(client: TestClient) -> None:
    product_id = product(client)
    entry = option(client, "Sombrero", 1)
    first = physical_value(client, entry, 0, "Gaucho")
    target = client.post("/api/v1/assets", json={"name": "Cabeza"}).json()
    entry["context_asset_id"] = target["id"]
    configure(client, product_id, [entry])
    request = {"selections": [selections(entry, 1)]}
    missing = client.post(path(product_id) + "/resolve", json=request)
    assert missing.status_code == 409
    assert "No hay implementación declarada" in missing.json()["detail"]
    assert (
        client.put(
            f"/api/v1/assets/{target['id']}/compatibilities/{first['id']}"
        ).status_code
        == 200
    )
    assert client.post(path(product_id) + "/resolve", json=request).status_code == 200
    second = client.post(
        "/api/v1/assets", json={"name": "Otro válido", "family_id": first["family_id"]}
    ).json()
    client.put(f"/api/v1/assets/{second['id']}/compatibilities/{target['id']}")
    ambiguous = client.post(path(product_id) + "/resolve", json=request)
    assert ambiguous.status_code == 409
    assert "ambigua" in ambiguous.json()["detail"]
    client.delete(f"/api/v1/assets/{second['id']}")
    assert client.post(path(product_id) + "/resolve", json=request).status_code == 200
    client.delete(f"/api/v1/assets/{target['id']}")
    assert client.post(path(product_id) + "/resolve", json=request).status_code == 409


def test_context_graph_and_unresolved_context(client: TestClient) -> None:
    product_id = product(client)
    first, second, third = option(client, "A"), option(client, "B"), option(client, "C")
    before = configure(client, product_id, [first])
    first["context_definition_id"] = second["definition_id"]
    assert client.put(path(product_id), json={"options": [first]}).status_code == 409
    second["context_definition_id"] = third["definition_id"]
    third["context_definition_id"] = first["definition_id"]
    assert (
        client.put(
            path(product_id), json={"options": [third, first, second]}
        ).status_code
        == 409
    )
    assert client.get(path(product_id)).json() == before
    second["context_definition_id"] = None
    configure(client, product_id, [first, second])
    # Un contexto omitido o un valor sin familia no identifica un recurso.
    for chosen in (
        [selections(first, 1)],
        [selections(first, 1), selections(second, 1)],
    ):
        assert (
            client.post(
                path(product_id) + "/resolve", json={"selections": chosen}
            ).status_code
            == 409
        )
    assert client.post(path(product_id) + "/resolve", json={}).status_code == 200


def test_inactive_catalog_and_unknown_resources(client: TestClient) -> None:
    product_id = product(client)
    entry = option(client, "A", 1)
    definition_path = f"{catalog_tests.ROOT}/{entry['definition_id']}"
    value_path = definition_path + f"/values/{entry['values'][0]['value_id']}"
    configure(client, product_id, [entry])
    for inactive_path in (
        value_path,
        definition_path,
        f"/api/v1/products/{product_id}",
    ):
        client.patch(inactive_path, json={"active": False})
        assert (
            client.post(
                path(product_id) + "/resolve",
                json={"selections": [selections(entry, 1)]},
            ).status_code
            == 409
        )
        assert client.get(path(product_id)).status_code == 200
        client.patch(inactive_path, json={"active": True})
    for method in ("get", "put", "post"):
        response = (
            client.get(path(str(uuid4())))
            if method == "get"
            else client.put(path(str(uuid4())), json={"options": []})
            if method == "put"
            else client.post(path(str(uuid4())) + "/resolve", json={})
        )
        assert response.status_code == 404
    entry["context_asset_id"] = str(uuid4())
    assert client.put(path(product_id), json={"options": [entry]}).status_code == 404


def test_configuration_replacement_rolls_back_and_fk_scopes_values(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    product_id = product(client)
    entry, other = option(client, "A"), option(client, "B")
    before = configure(client, product_id, [entry])
    with SessionFactory() as session:

        def fail_commit() -> None:
            session.flush()
            raise SQLAlchemyError("Fallo simulado")

        monkeypatch.setattr(session, "commit", fail_commit)
        with pytest.raises(PersistenceError):
            ProductConfigurationService(session).replace(
                UUID(product_id), ProductConfigurationInput(options=[])
            )
    assert client.get(path(product_id)).json() == before
    with SessionFactory() as session:
        session.add(
            ProductOptionValue(
                product_id=UUID(product_id),
                definition_id=UUID(entry["definition_id"]),
                value_id=UUID(other["values"][0]["value_id"]),
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()
        row = session.get(
            ProductOption, (UUID(product_id), UUID(entry["definition_id"]))
        )
        assert row is not None
        row.context_definition_id = UUID(other["definition_id"])
        with pytest.raises(IntegrityError):
            session.flush()
        session.rollback()


def test_multiple_context_selections_are_not_chosen_silently(
    client: TestClient,
) -> None:
    product_id = product(client)
    head, hat = option(client, "Cabezas", 2), option(client, "Sombrero", 1)
    physical_value(client, head, 0, "Cabeza A")
    physical_value(client, head, 1, "Cabeza B")
    physical_value(client, hat, 0, "Sombrero")
    head["max_selections"] = None
    hat["context_definition_id"] = head["definition_id"]
    configure(client, product_id, [head, hat])
    response = client.post(
        path(product_id) + "/resolve",
        json={"selections": [selections(head, 2), selections(hat, 1)]},
    )
    assert response.status_code == 409
    assert "único recurso" in response.json()["detail"]


def test_concurrent_replacements_do_not_mix_configuration(client: TestClient) -> None:
    product_id = product(client)
    first, second = option(client, "A"), option(client, "B")
    first["max_selections"] = None
    second["max_selections"] = None
    for entry in (first, second):
        for value in entry["values"]:
            value["default_quantity"] = "2"

    def replace(entry: dict[str, Any]) -> str:
        with SessionFactory() as session:
            result = ProductConfigurationService(session).replace(
                UUID(product_id),
                ProductConfigurationInput.model_validate({"options": [entry]}),
            )
            return str(result.options[0].definition_id)

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert set(executor.map(replace, (first, second))) == {
            first["definition_id"],
            second["definition_id"],
        }
    result = client.get(path(product_id)).json()["options"]
    assert len(result) == 1
    expected = first if result[0]["definition_id"] == first["definition_id"] else second
    assert {value["value_id"] for value in result[0]["values"]} == {
        value["value_id"] for value in expected["values"]
    }
    assert client.post(path(product_id) + "/resolve", json={}).status_code == 200


def test_resolution_uses_one_database_snapshot(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    product_id = product(client)
    entry = option(client, "A", 1)
    asset = physical_value(client, entry, 0, "Único")
    configure(client, product_id, [entry])
    with SessionFactory() as session:
        service = ProductConfigurationService(session)
        original = service._resolve_value

        def concurrent_change(
            definition_id: UUID, chosen: SelectedOptionValue, context_id: UUID | None
        ) -> ResolvedOptionValue:
            with SessionFactory() as writer:
                AssetService(writer).create(
                    AssetCreate(
                        name="Ahora ambiguo", family_id=UUID(asset["family_id"])
                    )
                )
            return original(definition_id, chosen, context_id)

        monkeypatch.setattr(service, "_resolve_value", concurrent_change)
        result = service.resolve(
            UUID(product_id),
            ConfigurationResolveInput.model_validate(
                {"selections": [selections(entry, 1)]}
            ),
        )
        assert str(result.selections[0].values[0].asset_id) == asset["id"]
    assert (
        client.post(
            path(product_id) + "/resolve", json={"selections": [selections(entry, 1)]}
        ).status_code
        == 409
    )
