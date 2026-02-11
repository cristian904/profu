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

## Scoring scale (solutions) parsing

Scoring-scale (barem/rezolvare) PDFs can be parsed into structured JSON with solution steps and scores. Each PDF may contain one subject (Subiectul I, II, or III) or all three. The pipeline is:

1. **Vision**: Gemini 2.0 Vision extracts text from the PDF and outputs markdown with structure and LaTeX/markdown formulas (`$...$`, `$$...$$`).
2. **Structure**: A second Gemini call turns that markdown into JSON with keys `s1`, `s2`, `s3` (only subjects present in the document). For each exercise: `number`, optional `item` (a/b/c/d for s2/s3), and `solution_steps` — either an array of `{"step": "...", "score": <number>}` when the solution is in a table, or a single string when it is plain text.

Run from `backend/exam_parser`:

```bash
# Single PDF or directory of PDFs; outputs are saved in the same folder as the PDF(s)
poetry run python run_solutions.py path/to/solution.pdf
poetry run python run_solutions.py path/to/downloads
poetry run python run_solutions.py path/to/downloads --output-dir path/to/base --skip-existing

# Re-run only PDFs whose JSON has null or empty step fields (fixes bad markdown parsing)
poetry run python run_solutions.py path/to/downloads --rerun-null-steps
```

- **Output location**: By default, outputs are under the folder containing the PDF(s). Two subfolders are created:
  - **vision_outputs_solutions/** — intermediate markdown from Gemini Vision (one `.md` per PDF, same stem).
  - **structured_output_solutions/** — final JSON (one `.json` per PDF, same stem).
- Use `--output-dir` / `-o` to use a different base directory for both subfolders.
- **`--skip-existing`**: Skip PDFs that already have a corresponding `.json` in `structured_output_solutions/`.
- **`--rerun-null-steps`**: Scan `structured_output_solutions/` for JSONs with null or empty step fields and re-run vision + structured extraction for the corresponding PDFs in the same folder.
