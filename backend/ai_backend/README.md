# Backend Setup

## Prerequisites

- Python 3.13+
- Poetry (for dependency management)

## Installation

1. From the repo root, go to this directory and install dependencies:
```bash
cd backend/ai_backend
poetry install
```

2. Create a `.env` file in this directory (`backend/ai_backend`):
```bash
cp .env.example .env
```

3. Add your Google API Key and (optional) database URL to the `.env` file:
```
GOOGLE_API_KEY=your_actual_gemini_api_key_here
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/profu
```

To get a Google API key:
- Go to https://makersuite.google.com/app/apikey
- Create a new API key
- Copy and paste it into your `.env` file

## Running the Server

```bash
poetry run uvicorn ai_backend.main:app --reload
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
AI prompts are configured in `ai_backend/prompts.yaml`. You can customize:
- System prompts for different chat types
- Instructions for formatting (Markdown, LaTeX, graphs)
- Educational tone and approach
- Response structure

Edit `prompts.yaml` to modify the AI's behavior without changing code.

## Database (PostgreSQL)

1. Create a PostgreSQL database (e.g. `profu`).
2. Run the initial schema script:
   ```bash
   psql -U postgres -d profu -f sql/init.sql
   ```
   Or use the Supabase SQL Editor and paste the contents of `sql/init.sql`. See `sql/README.md` for details.
3. Set `DATABASE_URL` in `.env` to a `postgresql+asyncpg://...` URL.

The backend uses SQLAlchemy 2.0 async (asyncpg) for all DB operations. Models live in `ai_backend/models/`, Pydantic schemas in `ai_backend/schemas/`. CRUD routers can be added under `ai_backend/routers/` and wired in `main.py`.

## Project Structure

```
backend/
├── ai_backend/
│   ├── main.py              # FastAPI application entry point
│   ├── database.py          # Async engine, session, get_db dependency
│   ├── prompts.yaml         # AI prompt configurations
│   ├── models/              # SQLAlchemy ORM models
│   │   ├── user.py
│   │   ├── exam_problem.py
│   │   ├── conversation.py
│   │   ├── exam_simulation.py
│   │   ├── exam_grade.py
│   │   └── scoring_scale.py
│   ├── schemas/             # Pydantic request/response schemas
│   │   ├── user.py
│   │   ├── exam_problem.py
│   │   └── ...
│   └── routers/             # API route modules (organized by feature)
│       ├── __init__.py
│       ├── common.py               # Shared utilities (LLM, models, prompts)
│       ├── clarify_once.py        # Direct answer mode endpoint
│       └── clarify_with_steps.py  # Step-by-step learning endpoint
│   ├── pyproject.toml       # Poetry dependencies (project root)
│   ├── poetry.lock
│   ├── .env                 # Environment variables (not in git)
│   ├── .env.example         # Environment variables template
│   └── tests/               # Unit and integration tests
│       ├── __init__.py
│       ├── test_main.py
│       ├── test_clarify.py   # Tests for both clarify modes
│       └── test_integration.py
├── sql/
│   ├── init.sql             # Initial PostgreSQL schema (run this yourself)
│   └── README.md            # How to run init.sql
└── pytest.ini               # Pytest config (run tests from backend/)
```

### Adding New Features

To add a new feature router:
1. Create a new file in `ai_backend/routers/` (e.g., `hints.py`)
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

The backend includes comprehensive unit and integration tests. Tests live in `backend/ai_backend/tests/`; `pytest.ini` is in `backend/`. Run them from the **backend** directory using the venv created by Poetry in `ai_backend`:

From repo root:
```bash
cd backend
ai_backend/.venv/bin/python -m pytest
```
(On Windows: `ai_backend\.venv\Scripts\python.exe -m pytest`)

Run with coverage:
```bash
ai_backend/.venv/bin/python -m pytest --cov=ai_backend --cov-report=html
```

Run a specific test file:
```bash
ai_backend/.venv/bin/python -m pytest ai_backend/tests/test_main.py
```

Run by marker:
```bash
ai_backend/.venv/bin/python -m pytest -m unit
ai_backend/.venv/bin/python -m pytest -m integration
```

### Test Structure

Tests live in `ai_backend/tests/` (when running from `backend/`):

```
ai_backend/tests/
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
