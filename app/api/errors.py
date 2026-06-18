from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from app.domain.exceptions import (
    DuplicateSlugError,
    FieldValidationError,
    InputResolutionError,
    InvalidTransitionError,
    NodeExecutionError,
    NotFoundError,
    ValidationError,
    WorkflowEngineError,
)


def _error_body(
    *,
    code: str,
    message: str,
    request: Request,
    details: list | None = None,
) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or [],
            "request_id": getattr(request.state, "request_id", None),
        }
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(NotFoundError)
    async def not_found_handler(request: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=_error_body(
                code=exc.code,
                message=exc.message,
                request=request,
                details=exc.details,
            ),
        )

    @app.exception_handler(DuplicateSlugError)
    async def duplicate_slug_handler(request: Request, exc: DuplicateSlugError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_error_body(
                code=exc.code,
                message=exc.message,
                request=request,
                details=exc.details,
            ),
        )

    @app.exception_handler(ValidationError)
    async def validation_handler(request: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_body(
                code=exc.code,
                message=exc.message,
                request=request,
                details=exc.details,
            ),
        )

    @app.exception_handler(InvalidTransitionError)
    async def invalid_transition_handler(
        request: Request, exc: InvalidTransitionError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_error_body(
                code=exc.code,
                message=exc.message,
                request=request,
                details=exc.details,
            ),
        )

    @app.exception_handler(FieldValidationError)
    async def field_validation_handler(
        request: Request, exc: FieldValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=_error_body(
                code=exc.code,
                message=exc.message,
                request=request,
                details=exc.details,
            ),
        )

    @app.exception_handler(InputResolutionError)
    async def input_resolution_handler(
        request: Request, exc: InputResolutionError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=_error_body(
                code=exc.code,
                message=exc.message,
                request=request,
                details=exc.details,
            ),
        )

    @app.exception_handler(NodeExecutionError)
    async def node_execution_handler(
        request: Request, exc: NodeExecutionError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=_error_body(
                code=exc.code,
                message=exc.message,
                request=request,
                details=exc.details,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_body(
                code="VALIDATION_ERROR",
                message="Request validation failed",
                request=request,
                details=exc.errors(),
            ),
        )

    @app.exception_handler(PydanticValidationError)
    async def pydantic_validation_handler(
        request: Request, exc: PydanticValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_body(
                code="VALIDATION_ERROR",
                message="Request validation failed",
                request=request,
                details=exc.errors(),
            ),
        )

    @app.exception_handler(WorkflowEngineError)
    async def workflow_engine_handler(request: Request, exc: WorkflowEngineError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body(
                code=exc.code,
                message=exc.message,
                request=request,
                details=exc.details,
            ),
        )
