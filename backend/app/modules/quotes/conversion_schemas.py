from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel


class ConversionTargetType(StrEnum):
    ORDER = "order"
    PROJECT = "project"


class QuoteConversionRead(BaseModel):
    target_type: ConversionTargetType
    target_id: UUID
    code: str
