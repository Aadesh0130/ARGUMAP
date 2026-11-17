"""Standard Error Envelopes and Custom Exception Handlers."""

from typing import Any, List, Optional
from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel


class ErrorDetail(BaseModel):
    field: Optional[str] = None
    issue: str


class ErrorEnvelope(BaseModel):
    code: str
    message: str
    details: List[ErrorDetail] = []


class AppException(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[List[ErrorDetail]] = None
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or []
        super().__init__(message)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": [d.model_dump() for d in exc.details]
            }
        }
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = []
    for err in exc.errors():
        field_path = " -> ".join([str(loc) for loc in err.get("loc", []) if loc != "body"])
        details.append(ErrorDetail(field=field_path or "body", issue=err.get("msg", "Invalid value")))

    return JSONResponse(
        status_code=getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422),
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed.",
                "details": [d.model_dump() for d in details]
            }
        }
    )
