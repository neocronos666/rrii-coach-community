from collections.abc import Iterator
from contextlib import contextmanager
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.exceptions import PersistenceError
from app.db.session import get_db_session
from app.modules.machines.exceptions import MachineNotFoundError
from app.modules.options.exceptions import OptionConflictError, OptionNotFoundError
from app.modules.products.exceptions import ProductNotFoundError
from app.modules.quick_quotes.exceptions import (
    QuickQuoteConflictError,
    QuickQuoteNotFoundError,
)
from app.modules.quick_quotes.formalization_schemas import (
    QuickQuoteFormalizationRead,
    QuickQuoteFormalize,
)
from app.modules.quick_quotes.formalization_service import (
    QuickQuoteFormalizationService,
)
from app.modules.quick_quotes.schemas import (
    QuickQuoteCreate,
    QuickQuoteRead,
    QuickQuoteRecalculate,
    QuickQuoteReplace,
)
from app.modules.quick_quotes.service import QuickQuoteService
from app.modules.quotes.exceptions import (
    IncompleteCostCalculationError,
    InvalidDepositError,
    InvalidQuoteAdjustmentError,
    MultiCurrencyQuoteUnsupportedError,
)
from app.modules.recipes.exceptions import InvalidRecipeError, RecipeNotFoundError
from app.modules.supplies.exceptions import SupplyNotFoundError

router = APIRouter(prefix="/quick-quotes", tags=["quick-quotes"])
DatabaseSession = Annotated[Session, Depends(get_db_session)]
PageLimit = Annotated[int, Query(ge=1, le=100)]
PageOffset = Annotated[int, Query(ge=0)]


@contextmanager
def errors() -> Iterator[None]:
    try:
        yield
    except (
        QuickQuoteNotFoundError,
        RecipeNotFoundError,
        ProductNotFoundError,
        OptionNotFoundError,
        SupplyNotFoundError,
        MachineNotFoundError,
    ) as error:
        raise HTTPException(404, str(error)) from error
    except (QuickQuoteConflictError, InvalidRecipeError, OptionConflictError) as error:
        raise HTTPException(409, str(error)) from error
    except (
        IncompleteCostCalculationError,
        InvalidDepositError,
        InvalidQuoteAdjustmentError,
        MultiCurrencyQuoteUnsupportedError,
    ) as error:
        raise HTTPException(422, str(error)) from error
    except PersistenceError as error:
        raise HTTPException(500, "No se pudo guardar el borrador") from error


@router.post("", response_model=QuickQuoteRead, status_code=201)
def create(payload: QuickQuoteCreate, session: DatabaseSession) -> QuickQuoteRead:
    with errors():
        return QuickQuoteService(session).create(payload)


@router.get("", response_model=list[QuickQuoteRead])
def list_quick_quotes(
    session: DatabaseSession, limit: PageLimit = 50, offset: PageOffset = 0
) -> list[QuickQuoteRead]:
    with errors():
        return QuickQuoteService(session).list_quotes(limit, offset)


@router.get("/{quote_id}", response_model=QuickQuoteRead)
def get(quote_id: UUID, session: DatabaseSession) -> QuickQuoteRead:
    with errors():
        return QuickQuoteService(session).get(quote_id)


@router.put("/{quote_id}", response_model=QuickQuoteRead)
def replace(
    quote_id: UUID, payload: QuickQuoteReplace, session: DatabaseSession
) -> QuickQuoteRead:
    with errors():
        return QuickQuoteService(session).replace(quote_id, payload)


@router.post("/{quote_id}/recalculate", response_model=QuickQuoteRead)
def recalculate(
    quote_id: UUID, payload: QuickQuoteRecalculate, session: DatabaseSession
) -> QuickQuoteRead:
    with errors():
        return QuickQuoteService(session).recalculate(quote_id, payload)


@router.get("/{quote_id}/revisions", response_model=list[QuickQuoteRead])
def history(
    quote_id: UUID,
    session: DatabaseSession,
    limit: PageLimit = 50,
    offset: PageOffset = 0,
) -> list[QuickQuoteRead]:
    with errors():
        return QuickQuoteService(session).history(quote_id, limit, offset)


@router.get("/{quote_id}/revisions/{revision}", response_model=QuickQuoteRead)
def get_revision(
    quote_id: UUID, revision: int, session: DatabaseSession
) -> QuickQuoteRead:
    with errors():
        return QuickQuoteService(session).get(quote_id, revision)


@router.post(
    "/{quote_id}/formalize", response_model=QuickQuoteFormalizationRead, status_code=201
)
def formalize(
    quote_id: UUID, payload: QuickQuoteFormalize, session: DatabaseSession
) -> QuickQuoteFormalizationRead:
    with errors():
        return QuickQuoteFormalizationService(session).formalize(quote_id, payload)


@router.get("/{quote_id}/formalization", response_model=QuickQuoteFormalizationRead)
def formalization(
    quote_id: UUID, session: DatabaseSession
) -> QuickQuoteFormalizationRead:
    with errors():
        return QuickQuoteFormalizationService(session).get(quote_id)
