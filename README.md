# Profu

[![CI](https://github.com/cristian904/profu/actions/workflows/ci.yml/badge.svg)](https://github.com/cristian904/profu/actions/workflows/ci.yml)

**Profu** is an AI-powered assistant for Romanian **Bacalaureat** preparation: a **Flutter** client and a **FastAPI** backend (`ai_backend`), with optional **Supabase** and an offline **exam parser** pipeline. The stack uses **Google Gemini** for LLM features.

Roadmap, requirements, and product status live under [docs/](docs/); this file is the **onboarding** entry point for the monorepo.

## Repository layout

| Path | Role |
|------|------|
| [backend/ai_backend](backend/ai_backend) | FastAPI AI API (routers, services, tests) |
| [backend/exam_parser](backend/exam_parser) | Offline exam ingestion pipeline (CLI / UI) |
| [backend/crawler](backend/crawler) | Crawl/download tooling and per-variant data trees |
| [backend/logging](backend/logging) | Shared `profu_logging` package |
| [flutter_app](flutter_app) | Flutter/Dart application |
| [supabase](supabase) | Supabase snippets and local config hints |
| [landing](landing) | Static landing assets |
| [docs](docs) | Product and planning documentation |
| [plans](plans) | Design and implementation plans |

Python packages are wired as a **uv workspace** from the repo root ([pyproject.toml](pyproject.toml)).

## Prerequisites

- **Python 3.13+** and [uv](https://docs.astral.sh/uv/getting-started/installation/)
- **Flutter** SDK (for the mobile/web app)
- **Node.js** / `npx` (optional, for [Supabase CLI](https://supabase.com/docs/guides/cli) local stack)

## Quick start

### 1. Install Python dependencies

From the **repository root**:

```bash
uv sync
```

### 2. Environment

Copy the root template and add secrets:

```bash
cp .env.example .env
```

Edit `.env`: at minimum set `GOOGLE_API_KEY` (Gemini). Optional: `DATABASE_URL`, `SUPABASE_*`, `API_BASE_URL`. See [.env.example](.env.example) for comments.

### 3. Run the AI backend

**Option A — default Uvicorn** (typical local URL `http://127.0.0.1:8000`):

```bash
uv run uvicorn ai_backend.main:app --reload
```

**Option B — Poe task `ai`** (listens on **all interfaces**, port **8080**, reload limited to `backend/ai_backend` — matches root `.env.example` `API_BASE_URL`):

```bash
uv run poe ai
```

API details and endpoints: [backend/ai_backend/README.md](backend/ai_backend/README.md).

### 4. Run the Flutter app

```bash
cd flutter_app
flutter pub get
flutter run
```

To align env with the root `.env` (copies to `flutter_app/.env` then opens Chrome), from the repo root:

```bash
uv run poe ui
```

Point the app at the same host/port as your running API (see `API_BASE_URL` in `.env`).

### 5. Local Supabase (optional)

See [docs/SUPABASE_GOOGLE_LOCAL.md](docs/SUPABASE_GOOGLE_LOCAL.md). From the repo root you can use:

```bash
uv run poe supabase
```

## Testing

**Backend** (from repo root):

```bash
uv run poe test_ai
```

Equivalent: `uv run pytest backend/ai_backend/tests -v`

**Flutter**:

```bash
cd flutter_app && flutter test
```

Or: `uv run poe test_ui` / `uv run poe test` (backend + Flutter).

## Continuous integration

[.github/workflows/ci.yml](.github/workflows/ci.yml) runs **backend** tests on push/PR to `main` and `develop`. There is **no** Flutter job in CI yet. More detail: [.github/CI_CD.md](.github/CI_CD.md).

## Documentation

| Document | Description |
|----------|-------------|
| [docs/IMPLEMENTED_FEATURES.md](docs/IMPLEMENTED_FEATURES.md) | What is implemented (product-level) |
| [docs/REQUIREMENTS.md](docs/REQUIREMENTS.md) | Requirements |
| [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md) | Plan, phases, timeline |
| [docs/RISK_REGISTER.md](docs/RISK_REGISTER.md) | Risks and mitigations |
| [docs/SUPABASE_GOOGLE_LOCAL.md](docs/SUPABASE_GOOGLE_LOCAL.md) | Local Supabase and related setup |
| [backend/ai_backend/README.md](backend/ai_backend/README.md) | Backend setup and API overview |
| [backend/exam_parser/README.md](backend/exam_parser/README.md) | Exam parser pipeline |
| [backend/crawler/README.md](backend/crawler/README.md) | Crawler |
| [flutter_app/README.md](flutter_app/README.md) | Flutter app |

## Contributing

Use feature branches, keep docs in [docs/](docs/) or [plans/](plans/) when changing scope, and run the test commands above before opening a PR.

## License

This repository is maintained for the Profu project; refer to team policy for distribution and licensing.
