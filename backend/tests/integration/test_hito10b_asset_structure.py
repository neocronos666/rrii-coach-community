from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from app.db.exceptions import PersistenceError
from app.db.session import SessionFactory
from app.modules.assets.exceptions import AssetConflictError
from app.modules.assets.models import Asset, AssetRevision
from app.modules.assets.schemas import AssetCreate, RevisionCreate
from app.modules.assets.service import AssetService
from app.modules.assets.structure_models import (
    AssetCompatibility,
    AssetCompositionComponent,
    AssetFamily,
)
from app.modules.assets.structure_schemas import CompositionRevisionCreate
from app.modules.assets.structure_service import AssetStructureService
from tests.integration import test_hito10b_asset_files as file_tests
from tests.integration import test_hito10b_assets as asset_tests

client = asset_tests.client
storage = file_tests.storage
create = asset_tests.create
pytestmark = pytest.mark.integration


def component(asset: dict[str, object], quantity: str = "1") -> dict[str, object]:
    return {
        "child_asset_id": asset["id"],
        "child_revision_id": asset["current_revision_id"],
        "quantity": quantity,
    }


def publish(
    client: TestClient, parent: dict[str, object], children: list[dict[str, object]]
) -> dict[str, object]:
    response = client.post(
        f"/api/v1/assets/{parent['id']}/composition-revisions",
        json={
            "base_revision_id": parent["current_revision_id"],
            "components": children,
        },
    )
    assert response.status_code == 201, response.text
    return dict(client.get(f"/api/v1/assets/{parent['id']}").json())


def composition(
    client: TestClient, asset: dict[str, object]
) -> list[dict[str, object]]:
    return list(
        client.get(
            f"/api/v1/assets/{asset['id']}/revisions/{asset['current_revision_id']}/composition"
        ).json()
    )


def test_families_separate_adaptation_design_and_revision(client: TestClient) -> None:
    family = client.post("/api/v1/asset-families", json={"name": "Gaucho"}).json()
    first = create(client, name="Gaucho Pikachu", family_id=family["id"])
    second = create(client, name="Gaucho Raichu", family_id=family["id"])
    assert first["id"] != second["id"]
    client.post(f"/api/v1/assets/{first['id']}/revisions", json={})
    current = client.get(f"/api/v1/assets/{first['id']}").json()
    assert current["family_id"] == family["id"] and current["id"] == first["id"]
    other_family = client.post(
        "/api/v1/asset-families", json={"name": "Gaucho ala ancha"}
    ).json()
    third = create(client, family_id=other_family["id"])
    assert third["family_id"] != first["family_id"]
    members = client.get("/api/v1/assets", params={"family_id": family["id"]}).json()
    assert {row["id"] for row in members} == {first["id"], second["id"]}
    assert (
        client.patch(
            "/api/v1/asset-families/" + family["id"],
            json={"description": "Mismo diseño"},
        ).status_code
        == 200
    )
    assert (
        client.get("/api/v1/asset-families/" + family["id"]).json()["name"] == "Gaucho"
    )
    assert (
        client.patch(
            "/api/v1/asset-families/" + family["id"], json={"name": None}
        ).status_code
        == 422
    )
    assert len(client.get("/api/v1/asset-families").json()) == 2
    assert (
        client.post(
            "/api/v1/assets", json={"name": "No crear", "family_id": str(uuid4())}
        ).status_code
        == 404
    )
    assert (
        client.patch(f"/api/v1/assets/{first['id']}", json={"family_id": None}).json()[
            "family_id"
        ]
        is None
    )
    with SessionFactory() as session:
        assert session.scalar(select(func.count()).select_from(Asset)) == 3
        assert session.scalar(select(func.count()).select_from(AssetFamily)) == 2


def test_positive_symmetric_compatibility_without_negative_rules(
    client: TestClient,
) -> None:
    first, second = create(client), create(client)
    path = f"/api/v1/assets/{first['id']}/compatibilities"
    reverse = f"/api/v1/assets/{second['id']}/compatibilities"
    assert client.get(path).json()["items"] == []
    assert client.put(path + "/" + str(second["id"])).status_code == 200
    assert client.put(reverse + "/" + str(first["id"])).status_code == 200
    assert client.get(reverse).json()["total"] == 1
    item = client.get(path).json()["items"][0]
    assert set(item) == {"id", "code", "name", "family_id", "archived"}
    assert "incompatible" not in item
    with SessionFactory() as session:
        assert session.scalar(select(func.count()).select_from(AssetCompatibility)) == 1
    assert client.put(path + "/" + str(first["id"])).status_code == 409
    assert client.put(path + "/" + str(uuid4())).status_code == 404
    assert client.delete(reverse + "/" + str(first["id"])).status_code == 204
    assert client.delete(reverse + "/" + str(first["id"])).status_code == 204
    assert client.get(path).json()["items"] == []


def test_compatibility_hundreds_paginated(client: TestClient) -> None:
    base = create(client)
    with SessionFactory() as session:
        assets, structure = AssetService(session), AssetStructureService(session)
        for index in range(201):
            child = assets.create(AssetCreate(name=f"Adaptación {index:03}"))
            structure.put_compatibility(UUID(str(base["id"])), child.id)
    path = f"/api/v1/assets/{base['id']}/compatibilities"
    pages = [
        client.get(path, params={"offset": offset, "limit": 100}).json()
        for offset in (0, 100, 200)
    ]
    assert all(page["total"] == 201 for page in pages)
    assert [len(page["items"]) for page in pages] == [100, 100, 1]
    assert len({row["id"] for page in pages for row in page["items"]}) == 201
    assert client.get(path, params={"limit": 101}).status_code == 422


def test_nested_composition_quantities_and_shared_descendant(
    client: TestClient,
) -> None:
    leaf, left, right, parent = [create(client) for _ in range(4)]
    left = publish(client, left, [component(leaf, "2.5")])
    right = publish(client, right, [component(leaf, "3")])
    parent = publish(client, parent, [component(left, "1"), component(right, "2")])
    assert len(composition(client, parent)) == 2
    assert Decimal(str(composition(client, left)[0]["quantity"])) == Decimal("2.5")
    assert set(composition(client, parent)[0]) == {
        "id",
        "parent_revision_id",
        "child_asset_id",
        "child_revision_id",
        "quantity",
    }


def test_pin_update_adoption_restore_and_parent_files(client: TestClient) -> None:
    child, parent = create(client), create(client)
    parent_path = f"/api/v1/assets/{parent['id']}/revisions"
    attachment = file_tests.upload(
        client,
        parent_path + "/" + str(parent["current_revision_id"]),
        b"%PDF-1.7\nmanual",
        "manual.pdf",
        "documentation",
    )
    parent = publish(client, parent, [component(child, "2")])
    old_composition = composition(client, parent)
    old_revision = client.get(
        parent_path + "/" + str(parent["current_revision_id"])
    ).json()
    updated = client.post(
        f"/api/v1/assets/{child['id']}/revisions", json={"note": "Corrección"}
    ).json()
    assert composition(client, parent) == old_composition
    updates = client.get(
        parent_path + "/" + str(parent["current_revision_id"]) + "/component-updates"
    ).json()
    assert updates[0]["update_available"] is True
    assert updates[0]["pinned_revision_id"] == child["current_revision_id"]
    assert updates[0]["current_revision_id"] == updated["id"]
    assert set(updates[0]).isdisjoint({"files", "revisions", "source_url"})
    child = dict(client.get(f"/api/v1/assets/{child['id']}").json())
    adopted = publish(client, parent, [component(child, "2")])
    assert adopted["current_revision_id"] != parent["current_revision_id"]
    assert composition(client, adopted)[0]["child_revision_id"] == updated["id"]
    restored = client.post(
        parent_path + "/" + str(parent["current_revision_id"]) + "/restore", json={}
    ).json()
    restored_composition = client.get(
        parent_path + "/" + restored["id"] + "/composition"
    ).json()
    assert (
        restored_composition[0]["child_revision_id"]
        == old_composition[0]["child_revision_id"]
    )
    assert restored_composition[0]["id"] != old_composition[0]["id"]
    assert (
        client.get(parent_path + "/" + restored["id"] + "/files").json()[0][
            "stored_file_id"
        ]
        == attachment["stored_file_id"]
    )
    assert (
        client.get(parent_path + "/" + str(parent["current_revision_id"])).json()
        == old_revision
    )
    ordinary = client.post(parent_path, json={}).json()
    assert (
        client.get(parent_path + "/" + ordinary["id"] + "/composition").json()[0][
            "child_revision_id"
        ]
        == old_composition[0]["child_revision_id"]
    )


def test_direct_indirect_and_historical_cycles_rejected(client: TestClient) -> None:
    first, second = create(client), create(client)

    def rejected(parent: dict[str, object], child: dict[str, object]) -> None:
        response = client.post(
            f"/api/v1/assets/{parent['id']}/composition-revisions",
            json={
                "base_revision_id": parent["current_revision_id"],
                "components": [component(child)],
            },
        )
        assert response.status_code == 409, response.text
        assert (
            client.get(f"/api/v1/assets/{parent['id']}").json()["current_revision_id"]
            == parent["current_revision_id"]
        )

    rejected(first, first)
    second_with_first = publish(client, second, [component(first)])
    rejected(first, second_with_first)
    # El grafo actual ya no tiene aristas desde segundo; su historia todavía sí.
    publish(client, second_with_first, [])
    rejected(first, second_with_first)


def test_restore_checks_current_graph_without_mutating_history(
    client: TestClient,
) -> None:
    first, second = create(client), create(client)
    composite = publish(client, first, [component(second)])
    empty = publish(client, composite, [])
    publish(client, second, [component(first)])
    response = client.post(
        f"/api/v1/assets/{first['id']}/revisions/{composite['current_revision_id']}/restore",
        json={},
    )
    assert response.status_code == 409
    assert (
        client.get(f"/api/v1/assets/{first['id']}").json()["current_revision_id"]
        == empty["current_revision_id"]
    )
    assert len(composition(client, composite)) == 1


@pytest.mark.parametrize(
    "quantity", ["0", "-1", "0.0000001", "NaN", "1000000000000", None]
)
def test_invalid_quantity(client: TestClient, quantity: object) -> None:
    parent, child = create(client), create(client)
    entry = component(child)
    entry["quantity"] = quantity
    response = client.post(
        f"/api/v1/assets/{parent['id']}/composition-revisions",
        json={"base_revision_id": parent["current_revision_id"], "components": [entry]},
    )
    assert response.status_code == 422


def test_duplicate_wrong_revision_and_stale_base(client: TestClient) -> None:
    parent, child, other = create(client), create(client), create(client)
    path = f"/api/v1/assets/{parent['id']}/composition-revisions"
    payload = {
        "base_revision_id": parent["current_revision_id"],
        "components": [component(child), component(child)],
    }
    assert client.post(path, json=payload).status_code == 422
    payload["components"] = [
        {**component(child), "child_revision_id": other["current_revision_id"]}
    ]
    assert client.post(path, json=payload).status_code == 404
    publish(client, parent, [component(child)])
    assert (
        client.post(
            path,
            json={"base_revision_id": parent["current_revision_id"], "components": []},
        ).status_code
        == 409
    )
    with SessionFactory() as session:
        assert (
            session.scalar(select(func.count()).select_from(AssetCompositionComponent))
            == 1
        )


def test_concurrent_cross_publications_cannot_create_cycle(client: TestClient) -> None:
    first, second = create(client), create(client)
    barrier = Barrier(2)

    def publish_one(index: int) -> bool:
        parent, child = (first, second) if index == 0 else (second, first)
        with SessionFactory() as session:
            barrier.wait(timeout=10)
            try:
                AssetStructureService(session).publish_composition(
                    UUID(str(parent["id"])),
                    CompositionRevisionCreate.model_validate(
                        {
                            "base_revision_id": parent["current_revision_id"],
                            "components": [component(child)],
                        }
                    ),
                )
                return True
            except AssetConflictError:
                return False

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(publish_one, range(2))) == [False, True]


def test_failed_commit_preserves_current_and_composition(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    parent, child = create(client), create(client)
    with SessionFactory() as session:

        def fail() -> None:
            raise SQLAlchemyError("Fallo simulado")

        monkeypatch.setattr(session, "commit", fail)
        with pytest.raises(PersistenceError):
            AssetStructureService(session).publish_composition(
                UUID(str(parent["id"])),
                CompositionRevisionCreate.model_validate(
                    {
                        "base_revision_id": parent["current_revision_id"],
                        "components": [component(child)],
                    }
                ),
            )
        assert (
            session.scalar(select(func.count()).select_from(AssetCompositionComponent))
            == 0
        )
        assert session.scalar(select(func.count()).select_from(AssetRevision)) == 2
    assert (
        client.get(f"/api/v1/assets/{parent['id']}").json()["current_revision_id"]
        == parent["current_revision_id"]
    )
    publish(client, parent, [component(child)])


def test_locked_asset_refreshes_cached_state_before_new_revision(
    client: TestClient,
) -> None:
    parent, child = create(client), create(client)
    parent_id = UUID(str(parent["id"]))
    with SessionFactory() as session:
        cached = session.get(Asset, parent_id)
        assert cached is not None
        published = publish(client, parent, [component(child)])
        assert cached.current_revision_id == UUID(str(parent["current_revision_id"]))
        with pytest.raises(AssetConflictError):
            AssetStructureService(session).publish_composition(
                parent_id,
                CompositionRevisionCreate.model_validate(
                    {
                        "base_revision_id": parent["current_revision_id"],
                        "components": [],
                    }
                ),
            )
        revision = AssetService(session).create_revision(parent_id, RevisionCreate())
        rows = AssetStructureService(session).composition(parent_id, revision.id)
        assert rows[0].child_asset_id == UUID(str(child["id"]))
        assert revision.id != UUID(str(published["current_revision_id"]))
