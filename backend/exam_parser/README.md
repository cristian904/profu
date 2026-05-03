# Exam Parser (Bacalaureat)

Offline ingestion pipeline: **local PDF → Nougat** (`facebook/nougat-base` on **GPU/CPU**) **→ markdown → Ollama** (JSON) **→ merge → Supabase → vector index**. Model weights load from the Hugging Face Hub on first run (no cloud jobs).

## Setup

From the **repo root**:

```bash
uv sync
```

Use the repo root `.env` (see `.env.example`): `GOOGLE_API_KEY` (embeddings), Supabase keys, Ollama URL/model. For Nougat on GPU, install a **CUDA** (or Apple **MPS**) PyTorch build; `NOUGAT_DEVICE=auto` picks CUDA, then MPS, then CPU.

## Usage

**CLI** (from repo root):

```bash
uv run python -m exam_parser.pipeline.cli --run-name MY_RUN \
  --problems-dir path/to/problems_pdfs \
  --solutions-dir path/to/solutions_pdfs
```

**Streamlit UI**:

```bash
uv run poe exam_parser_ui
# or: uv run streamlit run backend/exam_parser/pipeline/ui.py
```

Run outputs live under `backend/exam_parser/runs/<run_name>/` (`01_problems_parsed/`, `02_solutions_parsed/`, `03_merged/`). The `load_to_db` step reads merged JSON from `03_merged/` and inserts into Supabase `exam_problems`.
