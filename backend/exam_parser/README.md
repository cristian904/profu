# Exam Parser (Bacalaureat)

Parse bacalaureat exam PDFs to markdown with LaTeX math using **Gemini 2.0 Vision**. One PDF in, one `.md` out (structure, headings, and math preserved as `$...$` and `$$...$$`).

No endpoints or frontend; runs locally with `GOOGLE_API_KEY` for the Gemini API.

## Setup

```bash
cd backend/exam_parser
poetry install
```

- **Python**: 3.11–3.13.
- **API key**: Set `GOOGLE_API_KEY` in the environment (e.g. copy `.env.example` to `.env` and fill it).

## Usage

Run from `backend/exam_parser`:

```bash
# Single PDF — output: same dir as PDF, <stem>.md (or use -o FILE)
poetry run python run.py path/to/exam.pdf
poetry run python run.py path/to/exam.pdf --output path/to/out.md

# Batch — all PDFs in a folder; outputs to <dir>/vision_outputs/<stem>.md (skips existing)
poetry run python run.py --batch path/to/downloads
```

## Output

- **Single file**: Default path is `{pdf_dir}/{stem}.md`. Use `-o` or `--output` to set a custom path.
- **Batch**: Outputs go to `{dir}/vision_outputs/{stem}.md`. Files that already exist are skipped.

Output is markdown with inline math `$...$` and display math `$$...$$` for use in the app or further processing.
