import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.exceptions import PersistenceError
from app.modules.orders.models import Order
from app.modules.orders.repository import OrderRepository
from app.modules.orders.types import OrderStatus
from app.modules.projects.models import Project, ProjectComponent
from app.modules.projects.repository import ProjectRepository
from app.modules.projects.types import ProjectStatus
from app.modules.quotes.conversion_models import QuoteConversion
from app.modules.quotes.conversion_repository import QuoteConversionRepository
from app.modules.quotes.conversion_schemas import (
    ConversionTargetType,
    QuoteConversionRead,
)
from app.modules.quotes.exceptions import (
    QuoteNotConvertibleError,
    QuoteNotFoundError,
)
from app.modules.quotes.models import Quote
from app.modules.quotes.repository import QuoteRepository
from app.modules.quotes.types import QuoteStatus

logger = logging.getLogger(__name__)


def target_type_for_item_count(item_count: int) -> ConversionTargetType:
    if item_count == 1:
        return ConversionTargetType.ORDER
    if item_count >= 2:
        return ConversionTargetType.PROJECT
    raise QuoteNotConvertibleError("Un presupuesto sin items no puede convertirse")


class QuoteConversionService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._quotes = QuoteRepository(session)
        self._orders = OrderRepository(session)
        self._projects = ProjectRepository(session)
        self._conversions = QuoteConversionRepository(session)

    def convert(self, quote_id: UUID) -> tuple[QuoteConversionRead, bool]:
        try:
            quote = self._quotes.get_for_update(quote_id)
            if quote is None:
                raise QuoteNotFoundError("No existe el presupuesto solicitado")
            if quote.status != QuoteStatus.APPROVED.value:
                raise QuoteNotConvertibleError(
                    "Solo un presupuesto approved puede convertirse"
                )

            existing = self._conversions.get_by_quote(quote.id)
            if existing is not None:
                result = self._to_read(existing)
                self._session.commit()
                return result, False

            target_type = target_type_for_item_count(len(quote.items))
            conversion = self._create_conversion(quote, target_type)
            self._conversions.add(conversion)
            result = self._to_read(conversion)
            self._session.commit()
            logger.info(
                "quote_converted quote_id=%s target_type=%s target_id=%s",
                quote.id,
                result.target_type.value,
                result.target_id,
            )
            return result, True
        except (QuoteNotFoundError, QuoteNotConvertibleError):
            self._session.rollback()
            raise
        except IntegrityError as error:
            self._session.rollback()
            existing = self._conversions.get_by_quote(quote_id)
            if existing is not None:
                result = self._to_read(existing)
                self._session.commit()
                return result, False
            raise PersistenceError("No se pudo convertir el presupuesto") from error
        except SQLAlchemyError as error:
            self._session.rollback()
            raise PersistenceError("No se pudo convertir el presupuesto") from error

    def _create_conversion(
        self, quote: Quote, target_type: ConversionTargetType
    ) -> QuoteConversion:
        if target_type is ConversionTargetType.ORDER:
            item = quote.items[0]
            order = self._orders.add(
                Order(
                    code=self._orders.next_code(datetime.now(UTC).year),
                    source_quote_id=quote.id,
                    source_quote_item_id=item.id,
                    title=quote.title,
                    description=item.description,
                    status=OrderStatus.PENDING.value,
                    quantity=item.quantity,
                    currency=quote.currency,
                    technical_unit_cost=item.technical_unit_cost,
                    technical_total_cost=item.technical_total_cost,
                    quoted_suggested_price=quote.suggested_price,
                    quoted_final_price=quote.final_price,
                    notes=item.notes if item.notes is not None else quote.notes,
                )
            )
            logger.info("order_created order_id=%s code=%s", order.id, order.code)
            return QuoteConversion(
                quote_id=quote.id,
                target_type=target_type.value,
                order_id=order.id,
                order=order,
            )

        project = self._projects.add(
            Project(
                code=self._projects.next_code(datetime.now(UTC).year),
                source_quote_id=quote.id,
                title=quote.title,
                description=quote.description,
                status=ProjectStatus.PENDING.value,
                currency=quote.currency,
                quoted_technical_cost=quote.technical_cost_total,
                quoted_suggested_price=quote.suggested_price,
                quoted_final_price=quote.final_price,
                notes=quote.notes,
                components=[
                    ProjectComponent(
                        source_quote_item_id=item.id,
                        description=item.description,
                        quantity=item.quantity,
                        technical_unit_cost=item.technical_unit_cost,
                        technical_total_cost=item.technical_total_cost,
                        position=item.position,
                        notes=item.notes,
                    )
                    for item in quote.items
                ],
            )
        )
        logger.info("project_created project_id=%s code=%s", project.id, project.code)
        return QuoteConversion(
            quote_id=quote.id,
            target_type=target_type.value,
            project_id=project.id,
            project=project,
        )

    @staticmethod
    def _to_read(conversion: QuoteConversion) -> QuoteConversionRead:
        if conversion.target_type == ConversionTargetType.ORDER.value:
            if conversion.order is None:
                raise RuntimeError("La conversión a pedido no posee destino")
            return QuoteConversionRead(
                target_type=ConversionTargetType.ORDER,
                target_id=conversion.order.id,
                code=conversion.order.code,
            )
        if conversion.project is None:
            raise RuntimeError("La conversión a proyecto no posee destino")
        return QuoteConversionRead(
            target_type=ConversionTargetType.PROJECT,
            target_id=conversion.project.id,
            code=conversion.project.code,
        )
