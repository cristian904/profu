# Backend Setup

## Prerequisites

- Python 3.13+
- Poetry (for dependency management)

## Installation

1. Install dependencies:
```bash
cd backend
poetry install
```

2. Create a `.env` file in the `backend` directory:
```bash
cp .env.example .env
```

3. Add your Google API Key to the `.env` file:
```
GOOGLE_API_KEY=your_actual_gemini_api_key_here
```

To get a Google API key:
- Go to https://makersuite.google.com/app/apikey
- Create a new API key
- Copy and paste it into your `.env` file

## Running the Server

```bash
poetry run uvicorn profu_backend.main:app --reload
```

The API will be available at `http://localhost:8000`

## API Endpoints

### GET /
Health check endpoint

### GET /index
Returns application description

### POST /clarify/once-stream
**"Clarify Once" Mode** - Direct answer endpoint where AI answers questions immediately with full knowledge.
- Request body: 
  ```json
  {
    "query": "your question here",
    "history": [
      {"role": "user", "content": "previous question"},
      {"role": "assistant", "content": "previous answer"}
    ]
  }
  ```
- Response: Server-Sent Events (SSE) stream with AI response tokens
- The `history` field is optional and allows for contextual follow-up questions

### POST /clarify/step-by-step-stream
**"Clarify Step-by-Step" Mode** - Guided step-by-step learning endpoint using LangGraph.
- The AI identifies prerequisite concepts and guides the student through them before explaining the main topic
- Uses Socratic questioning method for interactive learning
- Request/Response format same as `/clarify/stream`
- First query triggers prerequisite generation, follow-ups continue the conversation

## Configuration

### Prompts
AI prompts are configured in `profu_backend/prompts.yaml`. You can customize:
- System prompts for different chat types
- Instructions for formatting (Markdown, LaTeX, graphs)
- Educational tone and approach
- Response structure

Edit `prompts.yaml` to modify the AI's behavior without changing code.

## Project Structure

```
backend/
├── profu_backend/
│   ├── main.py              # FastAPI application entry point
│   ├── prompts.yaml         # AI prompt configurations
│   └── routers/             # API route modules (organized by feature)
│       ├── __init__.py
│       ├── common.py               # Shared utilities (LLM, models, prompts)
│       ├── clarify_once.py         # Direct answer mode endpoint
│       └── clarify_step_by_step.py # Step-by-step learning endpoint
├── tests/                          # Unit and integration tests
│   ├── __init__.py
│   ├── test_main.py
│   ├── test_clarify.py             # Tests for both clarify modes
│   └── test_integration.py
├── pyproject.toml           # Poetry dependencies
├── .env                     # Environment variables (not in git)
└── .env.example            # Environment variables template
```

### Adding New Features

To add a new feature router:
1. Create a new file in `profu_backend/routers/` (e.g., `hints.py`)
2. Import shared utilities from `common.py` if needed:
   ```python
   from .common import get_llm, QueryRequest, PROMPTS
   ```
3. Define an `APIRouter` with appropriate prefix and tags
4. Implement your endpoints in the router
5. Import and include the router in `main.py`:
   ```python
   from .routers import clarify_once, clarify_step_by_step, hints
   app.include_router(hints.router)
   ```

## Development

The backend uses:
- **FastAPI** for the web framework
- **LangChain** for LLM orchestration
- **LangGraph** for guided learning state machine (step-by-step mode)
- **Google Gemini 2.0 Flash** for AI responses
- **Server-Sent Events (SSE)** for token streaming
- **PyYAML** for prompt configuration management

### Architecture

The clarify feature is split into two modes:
- **Clarify Once** (`clarify_once.py`): Direct question-answering mode
- **Clarify Step-by-Step** (`clarify_step_by_step.py`): Interactive step-by-step learning with prerequisite checking

Both modes share common utilities from `common.py` including:
- LLM initialization (`get_llm()`)
- Pydantic models (`Message`, `QueryRequest`)
- Prompt configurations (`PROMPTS`)

### Running Tests

The backend includes comprehensive unit and integration tests.

Install test dependencies:
```bash
poetry install --with dev
```

Run all tests:
```bash
poetry run pytest
```Run tests with coverage:
```bash
poetry run pytest --cov=profu_backend --cov-report=html
```

Run specific test file:
```bash
poetry run pytest tests/test_main.py
```

Run tests by marker:
```bash
poetry run pytest -m unit
poetry run pytest -m integration
```

### Test Structure

```
tests/
├── __init__.py
├── test_main.py          # Core app endpoint tests
├── test_clarify.py       # Tests for clarify_once and clarify_step_by_step routers
└── test_integration.py   # Integration and streaming tests
```

Tests cover:
- ✅ API endpoint responses (both clarify modes)
- ✅ Pydantic model validation
- ✅ CORS configuration
- ✅ LLM initialization
- ✅ Streaming functionality (SSE format)
- ✅ Error handling
- ✅ Conversation history management
- ✅ Prompt configuration loading
