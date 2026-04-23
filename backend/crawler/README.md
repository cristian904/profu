# Crawler

Python module that downloads bacalaureat M1 PDFs (enunturi + rezolvari) from [variante-mate.ro](https://variante-mate.ro/bacalaureat/variante-m1/v-1).

## URL pattern

- Variant pages: `https://variante-mate.ro/bacalaureat/variante-m1/v-{1..100}`
- Each page has 6 PDFs: 3 statements ("Enunturi" – Subiectul 1/2/3) and 3 solutions ("Rezolvari" – Subiectul 1/2/3).

## Output

- All crawler files are saved under root `downloads/` (gitignored).
- Each crawler writes to its own run folder:
  - `downloads/var_2009/`
  - `downloads/heiprofu/`
- Inside each run folder:
  - `problems/` contains problem statements
  - `solutions/` contains solutions/barems
- Problem and solution pairs share the same filename (for example, `downloads/var_2009/problems/2009_M1_v1_s1.pdf` matches `downloads/var_2009/solutions/2009_M1_v1_s1.pdf`).

## Setup

From the **repo root**:

```bash
uv sync
```

## Run

From the **repo root**:

```bash
# Hei Profu crawler (exam PDFs from heiprofu.ro)
uv run python -m crawler.crawl_heiprofu

# Variant 2009 crawler (variante-mate.ro)
uv run python -m crawler.crawler_var_2009
```

Other scripts: `uv run python -m crawler.list_downloads`, `uv run python -m crawler.match_exam_solutions`, `uv run python -m crawler.move_jsons_to_structured_output` (run from repo root with the same pattern).
