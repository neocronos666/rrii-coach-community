"""Validación del DAG actual y de snapshots fijados; sin commits propios."""

from collections import defaultdict, deque
from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.modules.assets.exceptions import AssetConflictError, AssetNotFoundError
from app.modules.assets.models import Asset, AssetRevision
from app.modules.assets.structure_models import AssetCompositionComponent
from app.modules.assets.structure_schemas import ComponentInput


def lock_composition(session: Session) -> None:
    # Espacio de locks de dos enteros, separado del hash de blobs (un bigint).
    session.execute(text("SELECT pg_advisory_xact_lock(1380534595, 1095976786)"))


def components(session: Session, revision_id: UUID) -> list[ComponentInput]:
    return [
        ComponentInput.model_validate(row)
        for row in session.scalars(
            select(AssetCompositionComponent)
            .where(AssetCompositionComponent.parent_revision_id == revision_id)
            .order_by(AssetCompositionComponent.child_asset_id)
        )
    ]


def store_components(
    session: Session, revision_id: UUID, entries: list[ComponentInput]
) -> None:
    for entry in entries:
        session.add(
            AssetCompositionComponent(
                parent_revision_id=revision_id, **entry.model_dump()
            )
        )


def assert_dag(edges: dict[UUID, set[UUID]]) -> None:
    indegree: dict[UUID, int] = defaultdict(int)
    for parent, children in edges.items():
        indegree.setdefault(parent, 0)
        for child in children:
            indegree[child] += 1
    ready = deque(node for node, degree in indegree.items() if degree == 0)
    seen = 0
    while ready:
        node = ready.popleft()
        seen += 1
        for child in edges.get(node, set()):
            indegree[child] -= 1
            if indegree[child] == 0:
                ready.append(child)
    if seen != len(indegree):
        raise AssetConflictError("La composición debe formar un DAG sin ciclos")


def validate_composition(
    session: Session, asset_id: UUID, entries: list[ComponentInput]
) -> None:
    revision_assets = dict(
        session.execute(
            select(AssetRevision.id, AssetRevision.asset_id).where(
                AssetRevision.id.in_([entry.child_revision_id for entry in entries])
            )
        )
        .tuples()
        .all()
    )
    for entry in entries:
        if revision_assets.get(entry.child_revision_id) != entry.child_asset_id:
            raise AssetNotFoundError("No existe la revisión indicada para el hijo")

    # DAG de referencias actuales, reemplazando sólo las aristas del padre.
    current: dict[UUID, set[UUID]] = defaultdict(set)
    for parent, child in session.execute(
        select(Asset.id, AssetCompositionComponent.child_asset_id).join(
            AssetCompositionComponent,
            AssetCompositionComponent.parent_revision_id == Asset.current_revision_id,
        )
    ):
        current[parent].add(child)
    current[asset_id] = {entry.child_asset_id for entry in entries}
    assert_dag(current)

    # Expandir únicamente revisiones fijadas, por niveles, sin seguir current.
    snapshot: dict[UUID, set[UUID]] = defaultdict(set)
    snapshot[asset_id] = {entry.child_asset_id for entry in entries}
    frontier = set(revision_assets)
    visited: set[UUID] = set()
    while frontier:
        rows = session.scalars(
            select(AssetCompositionComponent).where(
                AssetCompositionComponent.parent_revision_id.in_(frontier)
            )
        ).all()
        visited.update(frontier)
        frontier = set()
        for row in rows:
            snapshot[revision_assets[row.parent_revision_id]].add(row.child_asset_id)
            revision_assets[row.child_revision_id] = row.child_asset_id
            if row.child_revision_id not in visited:
                frontier.add(row.child_revision_id)
    assert_dag(snapshot)
