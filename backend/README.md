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

### POST /clarify/stream
Streaming endpoint for clarifying concepts
- Request body: `{"query": "your question here"}`
- Response: Server-Sent Events (SSE) stream with AI response tokens

## Development

The backend uses:
- FastAPI for the web framework
- LangChain for LLM orchestration
- Google Gemini 1.5 Flash for AI responses
- Server-Sent Events (SSE) for token streaming
