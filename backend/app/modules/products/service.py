from typing import NoReturn
from uuid import UUID

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.exceptions import PersistenceError
from app.modules.products.exceptions import (
    DuplicateVariantSkuError,
    ProductNotFoundError,
)
from app.modules.products.models import Product, ProductVariant
from app.modules.products.repository import ProductRepository
from app.modules.products.schemas import (
    ProductCreate,
    ProductUpdate,
    VariantCreate,
    VariantUpdate,
)


class ProductService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = ProductRepository(session)

    def get_product(self, product_id: UUID, *, lock: bool = False) -> Product:
        product = self.repository.product(product_id, lock=lock)
        if product is None:
            raise ProductNotFoundError("No existe el producto")
        return product

    def get_variant(self, variant_id: UUID, *, lock: bool = False) -> ProductVariant:
        variant = self.repository.variant(variant_id, lock=lock)
        if variant is None:
            raise ProductNotFoundError("No existe la variante")
        return variant

    def create(self, payload: ProductCreate) -> tuple[Product, ProductVariant]:
        try:
            product = Product(**payload.model_dump(exclude={"initial_variant"}))
            self.repository.add(product)
            variant = ProductVariant(
                product_id=product.id, **payload.initial_variant.model_dump()
            )
            self.repository.add(variant)
            self.session.commit()
            return product, variant
        except SQLAlchemyError as error:
            self._persistence_error(error)

    def add_variant(self, product_id: UUID, payload: VariantCreate) -> ProductVariant:
        try:
            self.get_product(product_id, lock=True)
            variant = ProductVariant(product_id=product_id, **payload.model_dump())
            self.repository.add(variant)
            self.session.commit()
            return variant
        except ProductNotFoundError:
            self.session.rollback()
            raise
        except SQLAlchemyError as error:
            self._persistence_error(error)

    def update_product(self, product_id: UUID, payload: ProductUpdate) -> Product:
        try:
            product = self.get_product(product_id, lock=True)
            for field, value in payload.model_dump(exclude_unset=True).items():
                setattr(product, field, value)
            self.session.commit()
            return product
        except ProductNotFoundError:
            self.session.rollback()
            raise
        except SQLAlchemyError as error:
            self._persistence_error(error)

    def update_variant(
        self, variant_id: UUID, payload: VariantUpdate
    ) -> ProductVariant:
        try:
            variant = self.get_variant(variant_id, lock=True)
            for field, value in payload.model_dump(exclude_unset=True).items():
                setattr(variant, field, value)
            self.session.commit()
            return variant
        except ProductNotFoundError:
            self.session.rollback()
            raise
        except SQLAlchemyError as error:
            self._persistence_error(error)

    def _persistence_error(self, error: SQLAlchemyError) -> "NoReturn":
        self.session.rollback()
        if isinstance(error, IntegrityError):
            diagnostic = getattr(error.orig, "diag", None)
            if (
                getattr(diagnostic, "constraint_name", None)
                == "uq_product_variants_sku"
            ):
                raise DuplicateVariantSkuError("El SKU ya está registrado") from error
        raise PersistenceError("No se pudo guardar el catálogo") from error
