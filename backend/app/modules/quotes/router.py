from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.db.exceptions import PersistenceError
from app.db.session import get_db_session
from app.modules.quotes.conversion_schemas import QuoteConversionRead
from app.modules.quotes.conversion_service import QuoteConversionService
from app.modules.quotes.exceptions import (
    IncompleteCostCalculationError,
    InvalidDepositError,
    InvalidQuoteAdjustmentError,
    InvalidQuoteTransitionError,
    MultiCurrencyQuoteUnsupportedError,
    QuoteNotConvertibleError,
    QuoteNotEditableError,
    QuoteNotFoundError,
)
from app.modules.quotes.schemas import QuoteCreate, QuoteRead, QuoteReject, QuoteUpdate
from app.modules.quotes.service import QuoteService
from app.modules.quotes.types import QuoteStatus

router = APIRouter(prefix="/quotes", tags=["quotes"])
DatabaseSession = Annotated[Session, Depends(get_db_session)]


def _translate(error: Exception) -> HTTPException:
    if isinstance(error, QuoteNotFoundError):
        return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error))
    if isinstance(error, QuoteNotEditableError | InvalidQuoteTransitionError):
        return HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error))
    if isinstance(
        error,
        IncompleteCostCalculationError
        | MultiCurrencyQuoteUnsupportedError
        | InvalidDepositError
        | InvalidQuoteAdjustmentError,
    ):
        return HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        )
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="No se pudo procesar el presupuesto",
    )


@router.post(
    "",
    response_model=QuoteRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear presupuesto",
    description="Crea un snapshot comercial desde cálculos técnicos existentes.",
    responses={
        404: {"description": "Cálculo inexistente"},
        422: {"description": "Economía inválida"},
    },
)
def create_quote(payload: QuoteCreate, session: DatabaseSession) -> QuoteRead:
    try:
        return QuoteService(session).create(payload)
    except (
        QuoteNotFoundError,
        IncompleteCostCalculationError,
        MultiCurrencyQuoteUnsupportedError,
        InvalidDepositError,
        InvalidQuoteAdjustmentError,
        PersistenceError,
    ) as error:
        raise _translate(error) from error


@router.get("", response_model=list[QuoteRead], summary="Listar presupuestos")
def list_quotes(
    session: DatabaseSession,
    quote_status: Annotated[QuoteStatus | None, Query(alias="status")] = None,
    year: Annotated[int | None, Query(ge=2000, le=9999)] = None,
) -> list[QuoteRead]:
    return QuoteService(session).list_quotes(status=quote_status, year=year)


@router.get(
    "/{quote_id}",
    response_model=QuoteRead,
    summary="Consultar presupuesto histórico",
    responses={404: {"description": "Presupuesto inexistente"}},
)
def get_quote(quote_id: UUID, session: DatabaseSession) -> QuoteRead:
    try:
        return QuoteService(session).get(quote_id)
    except QuoteNotFoundError as error:
        raise _translate(error) from error


@router.patch(
    "/{quote_id}",
    response_model=QuoteRead,
    summary="Actualizar presupuesto draft",
    responses={
        404: {"description": "Presupuesto inexistente"},
        409: {"description": "Presupuesto no editable"},
        422: {"description": "Economía inválida"},
    },
)
def update_quote(
    quote_id: UUID, payload: QuoteUpdate, session: DatabaseSession
) -> QuoteRead:
    try:
        return QuoteService(session).update(quote_id, payload)
    except (
        QuoteNotFoundError,
        QuoteNotEditableError,
        IncompleteCostCalculationError,
        MultiCurrencyQuoteUnsupportedError,
        InvalidDepositError,
        InvalidQuoteAdjustmentError,
        PersistenceError,
    ) as error:
        raise _translate(error) from error


@router.post(
    "/{quote_id}/approve",
    response_model=QuoteRead,
    summary="Aprobar presupuesto",
    responses={
        404: {"description": "Presupuesto inexistente"},
        409: {"description": "Transición inválida"},
    },
)
def approve_quote(quote_id: UUID, session: DatabaseSession) -> QuoteRead:
    try:
        return QuoteService(session).approve(quote_id)
    except (QuoteNotFoundError, InvalidQuoteTransitionError) as error:
        raise _translate(error) from error


@router.post(
    "/{quote_id}/reject",
    response_model=QuoteRead,
    summary="Rechazar presupuesto",
    responses={
        404: {"description": "Presupuesto inexistente"},
        409: {"description": "Transición inválida"},
    },
)
def reject_quote(
    quote_id: UUID, payload: QuoteReject, session: DatabaseSession
) -> QuoteRead:
    try:
        return QuoteService(session).reject(quote_id, payload.reason)
    except (QuoteNotFoundError, InvalidQuoteTransitionError) as error:
        raise _translate(error) from error


@router.post(
    "/{quote_id}/convert",
    response_model=QuoteConversionRead,
    summary="Convertir presupuesto aprobado",
    description="Un item crea un pedido; dos o más crean un proyecto.",
    responses={
        201: {"description": "Conversión creada"},
        404: {"description": "Presupuesto inexistente"},
        409: {"description": "Presupuesto no convertible"},
    },
)
def convert_quote(
    quote_id: UUID, response: Response, session: DatabaseSession
) -> QuoteConversionRead:
    try:
        result, created = QuoteConversionService(session).convert(quote_id)
        response.status_code = (
            status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )
        return result
    except QuoteNotFoundError as error:
        raise _translate(error) from error
    except QuoteNotConvertibleError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(error)
        ) from error
    except PersistenceError as error:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No se pudo convertir el presupuesto",
        ) from error
