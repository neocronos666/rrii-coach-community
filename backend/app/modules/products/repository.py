from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.products.models import Product, ProductVariant


class ProductRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def product(self, product_id: UUID, *, lock: bool = False) -> Product | None:
        statement = select(Product).where(Product.id == product_id)
        if lock:
            statement = statement.with_for_update()
        return self.session.scalar(statement)

    def variant(self, variant_id: UUID, *, lock: bool = False) -> ProductVariant | None:
        statement = select(ProductVariant).where(ProductVariant.id == variant_id)
        if lock:
            statement = statement.with_for_update()
        return self.session.scalar(statement)

    def products(
        self, active: bool | None, search: str | None, offset: int, limit: int
    ) -> list[Product]:
        statement = select(Product)
        if active is not None:
            statement = statement.where(Product.active == active)
        if search:
            statement = statement.where(Product.name.icontains(search, autoescape=True))
        return list(
            self.session.scalars(
                statement.order_by(Product.name, Product.id).offset(offset).limit(limit)
            )
        )

    def variants(
        self, product_id: UUID, active: bool | None, offset: int, limit: int
    ) -> list[ProductVariant]:
        statement = select(ProductVariant).where(
            ProductVariant.product_id == product_id
        )
        if active is not None:
            statement = statement.where(ProductVariant.active == active)
        return list(
            self.session.scalars(
                statement.order_by(ProductVariant.name, ProductVariant.id)
                .offset(offset)
                .limit(limit)
            )
        )

    def add(self, entity: Product | ProductVariant) -> None:
        self.session.add(entity)
        self.session.flush()
