from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.exceptions import PersistenceError
from app.db.session import get_db_session
from app.modules.products.exceptions import (
    DuplicateVariantSkuError,
    ProductNotFoundError,
)
from app.modules.products.schemas import (
    ProductCreate,
    ProductCreated,
    ProductRead,
    ProductUpdate,
    VariantCreate,
    VariantRead,
    VariantUpdate,
)
from app.modules.products.service import ProductService

router = APIRouter(tags=["products"])
DatabaseSession = Annotated[Session, Depends(get_db_session)]


def product_service(session: DatabaseSession) -> ProductService:
    return ProductService(session)


Service = Annotated[ProductService, Depends(product_service)]
Offset = Annotated[int, Query(ge=0)]
Limit = Annotated[int, Query(ge=1, le=100)]


@contextmanager
def errors() -> Iterator[None]:
    try:
        yield
    except ProductNotFoundError as error:
        raise HTTPException(404, str(error)) from error
    except DuplicateVariantSkuError as error:
        raise HTTPException(409, str(error)) from error
    except PersistenceError as error:
        raise HTTPException(500, "No se pudo guardar el catálogo") from error


@router.post("/products", response_model=ProductCreated, status_code=201)
def create_product(payload: ProductCreate, service: Service) -> ProductCreated:
    with errors():
        product, variant = service.create(payload)
        return ProductCreated(
            **ProductRead.model_validate(product).model_dump(),
            initial_variant=VariantRead.model_validate(variant),
        )


@router.get("/products", response_model=list[ProductRead])
def list_products(
    service: Service,
    active: bool | None = None,
    search: Annotated[str | None, Query(max_length=255)] = None,
    offset: Offset = 0,
    limit: Limit = 50,
) -> list[ProductRead]:
    return [
        ProductRead.model_validate(item)
        for item in service.repository.products(active, search, offset, limit)
    ]


@router.get("/products/{product_id}", response_model=ProductRead)
def get_product(product_id: UUID, service: Service) -> ProductRead:
    with errors():
        return ProductRead.model_validate(service.get_product(product_id))


@router.patch("/products/{product_id}", response_model=ProductRead)
def update_product(
    product_id: UUID, payload: ProductUpdate, service: Service
) -> ProductRead:
    with errors():
        return ProductRead.model_validate(service.update_product(product_id, payload))


@router.post(
    "/products/{product_id}/variants", response_model=VariantRead, status_code=201
)
def add_variant(
    product_id: UUID, payload: VariantCreate, service: Service
) -> VariantRead:
    with errors():
        return VariantRead.model_validate(service.add_variant(product_id, payload))


@router.get("/products/{product_id}/variants", response_model=list[VariantRead])
def list_variants(
    product_id: UUID,
    service: Service,
    active: bool | None = None,
    offset: Offset = 0,
    limit: Limit = 50,
) -> list[VariantRead]:
    with errors():
        service.get_product(product_id)
        return [
            VariantRead.model_validate(item)
            for item in service.repository.variants(product_id, active, offset, limit)
        ]


@router.get("/product-variants/{variant_id}", response_model=VariantRead)
def get_variant(variant_id: UUID, service: Service) -> VariantRead:
    with errors():
        return VariantRead.model_validate(service.get_variant(variant_id))


@router.patch("/product-variants/{variant_id}", response_model=VariantRead)
def update_variant(
    variant_id: UUID, payload: VariantUpdate, service: Service
) -> VariantRead:
    with errors():
        return VariantRead.model_validate(service.update_variant(variant_id, payload))
