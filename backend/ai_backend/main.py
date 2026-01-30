from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import logging

from routers import clarify_once, clarify_with_steps, solve_problem

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

# Load environment variables
load_dotenv()

app = FastAPI(
    title="Profu API",
    version="1.0.0",
    description="AI-Powered Bacalaureat Preparation Assistant"
)

# Add exception handler for validation errors
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    print(f"[VALIDATION ERROR] Path: {request.url.path}")
    print(f"[VALIDATION ERROR] Method: {request.method}")
    print(f"[VALIDATION ERROR] Errors: {exc.errors()}")
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
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
