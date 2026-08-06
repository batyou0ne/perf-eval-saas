import logging

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.limiter import limiter
from app.core.logging import configure_logging

configure_logging()

settings = get_settings()
logger = logging.getLogger(__name__)

app = FastAPI(title="Performance Eval SaaS API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    logger.warning(
        "Rate limit exceeded", extra={"path": request.url.path, "client_ip": get_remote_address(request)}
    )
    return _rate_limit_exceeded_handler(request, exc)


async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error(
        "Unhandled exception", extra={"path": request.url.path, "method": request.method}, exc_info=exc
    )
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": "Internal server error"})


app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
app.add_exception_handler(Exception, _unhandled_exception_handler)
app.add_middleware(SlowAPIMiddleware)

app.include_router(api_router, prefix="/api/v1")
