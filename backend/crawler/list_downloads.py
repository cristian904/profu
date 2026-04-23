"""Scan root downloads folder and report counts for crawler runs."""

import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT_DOWNLOADS = SCRIPT_DIR.parents[1] / "downloads"
RUNS = ["var_2009", "heiprofu"]


def _log(msg: str) -> None:
    print(msg, flush=True)


def count_pdfs(directory: Path) -> int:
    """Count PDF files in a directory."""
    if not directory.exists():
        return 0
    return sum(1 for file_path in directory.iterdir() if file_path.is_file() and file_path.suffix.lower() == ".pdf")


def main() -> None:
    """Print download stats for each crawler run folder."""
    _log("Scanning crawler download folders...")
    _log("")
    _log(f"Root: {ROOT_DOWNLOADS}")
    _log("")

    for run_name in RUNS:
        run_dir = ROOT_DOWNLOADS / run_name
        problems_dir = run_dir / "problems"
        solutions_dir = run_dir / "solutions"
        problems_count = count_pdfs(problems_dir)
        solutions_count = count_pdfs(solutions_dir)
        _log(f"  {run_name}/")
        _log(f"    Problems:  {problems_count} PDFs ({problems_dir})")
        _log(f"    Solutions: {solutions_count} PDFs ({solutions_dir})")
        _log(f"    Pair delta (problems-solutions): {problems_count - solutions_count}")
        _log("")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    main()
    sys.exit(0)
