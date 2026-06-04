"""Custom exception hierarchy + global handler payload."""
from __future__ import annotations

from typing import Any


class AppException(Exception):
    status_code: int = 500
    code: str = "internal_error"
    message: str = "Internal server error"

    def __init__(self, message: str | None = None, *, details: dict[str, Any] | None = None) -> None:
        super().__init__(message or self.message)
        if message:
            self.message = message
        self.details = details or {}


class NotFoundError(AppException):
    status_code = 404
    code = "not_found"
    message = "Resource not found"


class ValidationFailedError(AppException):
    status_code = 422
    code = "validation_failed"
    message = "Validation failed"


class UnauthorizedError(AppException):
    status_code = 401
    code = "unauthorized"
    message = "Authentication required"


class ForbiddenError(AppException):
    status_code = 403
    code = "forbidden"
    message = "Insufficient permissions"


class ConflictError(AppException):
    status_code = 409
    code = "conflict"
    message = "Resource conflict"


class RateLimitedError(AppException):
    status_code = 429
    code = "rate_limited"
    message = "Too many requests"


class CrawlError(AppException):
    status_code = 502
    code = "crawl_failed"
    message = "Crawl operation failed"


class ExternalServiceError(AppException):
    status_code = 502
    code = "external_service"
    message = "Upstream service error"


class PromptInjectionError(AppException):
    status_code = 400
    code = "prompt_injection"
    message = "Query rejected by safety filter"
