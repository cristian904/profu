#!/usr/bin/env python3
"""Move all .json files from crawler/downloads_exams into downloads_exams/structured_output."""
from pathlib import Path

DOWNLOADS_EXAMS = Path(__file__).resolve().parent / "downloads_exams"
OUT_SUBDIR = "structured_output"


def main() -> None:
    if not DOWNLOADS_EXAMS.is_dir():
        raise SystemExit(f"Directory not found: {DOWNLOADS_EXAMS}")
    out_dir = DOWNLOADS_EXAMS / OUT_SUBDIR
    out_dir.mkdir(parents=True, exist_ok=True)
    json_files = [p for p in DOWNLOADS_EXAMS.iterdir() if p.is_file() and p.suffix.lower() == ".json"]
    moved = 0
    for p in json_files:
        dest = out_dir / p.name
        p.rename(dest)
        moved += 1
        print(p.name, "->", dest)
    print(f"Done. Moved {moved} .json files to {out_dir}")


if __name__ == "__main__":
    main()
