from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import logging
import traceback
import uuid

from ai_backend.config import settings  # noqa: F401 - load .env via pydantic-settings
from profu_logging.log_utils import ColoredJsonFormatter
from profu_logging.feature_logger import get_feature_logger
from ai_backend.routers import clarify_once, clarify_with_steps, solve_problem, simulari
from ai_backend.common.auth import ensure_jwks_prefetch, get_user_id_from_request

# Feature-scoped loggers (preserve `source` values)
LOG_VALIDATION = get_feature_logger(source="validation")
LOG_EXCEPTION = get_feature_logger(source="exception")

# Configure JSON logging: level prefix + JSON message (colored when TTY)
_json_logger = logging.getLogger("ai_backend.json")
_json_logger.setLevel(logging.INFO)
_json_logger.propagate = False
_handler = logging.StreamHandler()
_handler.setFormatter(ColoredJsonFormatter("%(levelname)s:    %(message)s"))
_json_logger.addHandler(_handler)


# Suppress uvicorn's duplicate "Exception in ASGI application" + traceback; we log errors as JSON above
class _SuppressUvicornExceptionLog(logging.Filter):
    """Filter out uvicorn's default exception log so only our JSON log is shown."""

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return "Exception in ASGI application" not in msg


_uvicorn_error_logger = logging.getLogger("uvicorn.error")
_uvicorn_error_logger.addFilter(_SuppressUvicornExceptionLog())


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Prefetch JWKS at startup so first RS256/ES256 request doesn't pay fetch cost
    ensure_jwks_prefetch()
    yield


app = FastAPI(
    title="Profu API",
    version="1.0.0",
    description="AI-Powered Bacalaureat Preparation Assistant",
    lifespan=lifespan,
)

# Add exception handler for validation errors (422 = Unprocessable Entity, standard for body validation)
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    LOG_VALIDATION.warning(
        f"Path: {request.url.path}, Method: {request.method}, Errors: {exc.errors()}",
        user_id=None,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "message": "Validation error - check server logs for details"},
    )


# Log unhandled exceptions as JSON (same format as other logs) then return 500
@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    error_id = uuid.uuid4()
    user_id = None
    try:
        user_id = get_user_id_from_request(request)
    except Exception:
        pass
    LOG_EXCEPTION.error(
        f"[error_id={error_id}] {exc!s}",
        user_id=user_id,
        traceback=traceback.format_exc(),
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "error_id": str(error_id),
        },
    )


# CORS: set CORS_ALLOW_ORIGINS in .env (comma-separated) for production; empty = any origin, no credentials
_cors_raw = (settings.cors_allow_origins or "").strip()
if _cors_raw:
    _cors_origins = [o.strip() for o in _cors_raw.split(",") if o.strip()]
    _cors_credentials = True
else:
    _cors_origins = ["*"]
    _cors_credentials = False

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=_cors_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(clarify_once.router)
app.include_router(clarify_with_steps.router)
app.include_router(solve_problem.router)
app.include_router(simulari.router)

@app.get("/")
async def root():
    return {"message": "Profu API is running"}


@app.get("/index")
async def index():
    """
    Returns a text response describing the Profu application.
    """
    return {
        "message": "Profu - Your AI-Powered Bacalaureat Preparation Assistant\n\n"
                   "Profu is an innovative educational platform designed to help Romanian high school "
                   "seniors prepare for the Bacalaureat exam. Our AI-driven application provides:\n\n"
                   "• Progressive Hints System: Upload math problems and receive step-by-step guidance\n"
                   "• Theory Bot: Ask questions and get curriculum-aligned answers\n"
                   "• 24/7 Access: Study anytime, anywhere at a fraction of the cost of private tutoring\n\n"
                   "Built with FastAPI backend and Flutter frontend."
    }
