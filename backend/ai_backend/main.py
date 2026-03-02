from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
import logging

from ai_backend.config import settings  # noqa: F401 - load .env via pydantic-settings
from ai_backend.routers import clarify_once, clarify_with_steps, solve_problem
from ai_backend.routers.common import ensure_jwks_prefetch

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)


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
    print(f"[VALIDATION ERROR] Path: {request.url.path}")
    print(f"[VALIDATION ERROR] Method: {request.method}")
    print(f"[VALIDATION ERROR] Errors: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors(), "message": "Validation error - check server logs for details"},
    )

# Enable CORS for Flutter app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific Flutter app origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(clarify_once.router)
app.include_router(clarify_with_steps.router)
app.include_router(solve_problem.router)

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
