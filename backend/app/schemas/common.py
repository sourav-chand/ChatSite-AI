"""Common API envelope schemas."""
from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorPayload(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class Envelope(BaseModel, Generic[T]):
    data: T | None = None
    meta: dict[str, Any] = Field(default_factory=dict)
    error: ErrorPayload | None = None


class PageMeta(BaseModel):
    page: int = 1
    page_size: int = 20
    total: int = 0


class PaginatedEnvelope(BaseModel, Generic[T]):
    data: list[T] = Field(default_factory=list)
    meta: PageMeta
    error: ErrorPayload | None = None
