"""FastAPI application factory."""

import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import AppError
from app.core.logging import generate_request_id, request_id_ctx, setup_logging
from app.core.rate_limit import check_rate_limit
from app.core.redis import close_redis
from app.schemas.common import APIResponse, ErrorDetail, ResponseMeta

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    setup_logging()
    logger.info("Starting SIBER API")
    yield
    await close_redis()
    logger.info("Shutting down SIBER API")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Authorized security analysis platform for web applications and APIs.",
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def request_context_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        request_id = request.headers.get("X-Request-ID") or generate_request_id()
        token = request_id_ctx.set(request_id)
        request.state.request_id = request_id
        start = time.perf_counter()

        try:
            decision = await check_rate_limit(request)
            if decision is not None and not decision.allowed:
                response = JSONResponse(
                    status_code=429,
                    content=APIResponse(
                        success=False,
                        error=ErrorDetail(
                            code="RATE_LIMITED",
                            message="Too many requests. Please try again later.",
                        ),
                        meta=ResponseMeta(request_id=request_id),
                    ).model_dump(),
                    headers={"Retry-After": str(decision.retry_after_seconds)},
                )
            else:
                response = await call_next(request)
        finally:
            request_id_ctx.reset(token)

        duration_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"

        logger.info(
            "%s %s %s %.2fms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        return response

    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=APIResponse(
                success=False,
                error=ErrorDetail(
                    code=exc.code,
                    message=exc.message,
                    details=exc.details,
                ),
                meta=ResponseMeta(
                    request_id=getattr(request.state, "request_id", ""),
                ),
            ).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        details = [
            {
                "location": ".".join(str(part) for part in error.get("loc", ())),
                "message": error.get("msg", "Invalid input."),
                "type": error.get("type", "validation_error"),
            }
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=422,
            content=APIResponse(
                success=False,
                error=ErrorDetail(
                    code="VALIDATION_ERROR",
                    message="Request validation failed.",
                    details=details,
                ),
                meta=ResponseMeta(
                    request_id=getattr(request.state, "request_id", ""),
                ),
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception: %s", exc)
        return JSONResponse(
            status_code=500,
            content=APIResponse(
                success=False,
                error=ErrorDetail(
                    code="INTERNAL_ERROR",
                    message="An unexpected error occurred.",
                ),
                meta=ResponseMeta(
                    request_id=getattr(request.state, "request_id", ""),
                ),
            ).model_dump(),
        )

    app.include_router(api_router, prefix=settings.api_prefix)

    @app.get("/")
    async def root() -> dict[str, str]:
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "docs": f"{settings.api_prefix}/../docs" if settings.is_development else "",
        }

    return app


app = create_app()
