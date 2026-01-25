from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Profu API", version="1.0.0")

# Enable CORS for Flutter app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific Flutter app origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

@app.get("/")
async def root():
    return {"message": "Profu API is running"}
