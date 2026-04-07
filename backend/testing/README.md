# profu-testing

Local harness for **clarify step-by-step** synthetic scenarios: LLM-generated checklists, multi-turn HTTP runs against the real API, and Langfuse dataset rows for **LLM-as-judge** evaluation in the Langfuse UI.

## Prerequisites

- Running `ai_backend` (e.g. `poe ai` from repo root, default `http://127.0.0.1:8080`).
- Valid **Supabase JWT** for a user allowed to call `/clarify/step-by-step-stream`.
- `GOOGLE_API_KEY` in repo-root `.env` for checklist generation (Gemini).
- Optional: `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_HOST` to register dataset items.

## Configuration

All variables are loaded via **pydantic-settings** in [`profu_testing/config.py`](profu_testing/config.py): repo-root `.env` first (if present), then cwd `.env`, then process environment. See the module docstring for the full list.

| Variable | Purpose |
|----------|---------|
| `EVAL_JWT` or `PROFU_EVAL_BEARER` | Bearer token only (optional `Bearer ` prefix is stripped). |
| `API_BASE_URL` | Default API root (same as Flutter/backend); used when `TESTING_API_BASE_URL` is unset. |
| `TESTING_API_BASE_URL` | Override API root for the harness. |
| `GOOGLE_API_KEY` | Checklist generation. |
| `GEMINI_MODEL` | Shared Gemini model id. |
| `TESTING_GEMINI_MODEL` | Override model for checklists only. |
| `PROFU_LANGFUSE_EVAL_DATASET` | Langfuse dataset name (default `profu_clarify_step_by_step_eval`). |
| `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` / `LANGFUSE_BASE_URL` / `LANGFUSE_HOST` | Dataset registration (host resolution matches `ai_backend`). |

Root `.env` may also define `DATABASE_URL`, `SUPABASE_*`, and `SOLVE_MONTHLY_QUOTA_THRESHOLD`; they are parsed into `ProfuTestingSettings` for parity but are **not** used by the current harness.

## Commands

From repo root (after `uv sync`):

```bash
uv run --project backend/testing profu-test-clarify --list
uv run --project backend/testing profu-test-clarify --scenario derivatives_prerequisites
uv run --project backend/testing profu-test-clarify --all
```

Flags:

- `--skip-checklist` — placeholder checklist only (no Gemini call).
- `--skip-langfuse` — do not create dataset items.

Transcripts are also written under `backend/testing/runs/` for quick inspection.

## Langfuse LLM-as-judge

Each run uses one **32-char hex** `trace_id` for all turns so the backend exports a single trace (`clarify_with_steps`). The harness calls `create_dataset_item` with:

- `input`: scenario id, opening message, scenario goal.
- `expected_output`: JSON checklist (dynamic rubric).
- `metadata.transcript`: full user/assistant log for judges that cannot read nested trace I/O.
- `source_trace_id`: same `trace_id` sent to the API.

Configure a **custom** LLM-as-judge evaluator in Langfuse that compares the checklist (`expected_output`) to the conversation output (trace or transcript). See [LLM-as-a-Judge](https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge).

## Scenarios

YAML files live in `profu_testing/scenarios/clarify_step_by_step/`. Edit or add files, then rerun the CLI.
