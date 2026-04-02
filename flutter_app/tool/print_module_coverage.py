#!/usr/bin/env python3
"""Summarize line coverage for modular (test-friendly) lib areas.

Run after: flutter test --coverage

- "modules": lib/core, app, data, models, utils, services, theme
- "modules_excl_supabase_repos": same but excludes conversation_repository and
  simulation_repository (heavy PostgREST / Supabase; cover via integration or fakes).

Full-app line % stays low while clarify/solve/simulation pages dominate LOC; the
excluded metric matches the 80–90% goal for injectable logic.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
LCOV = REPO_ROOT / "coverage" / "lcov.info"

PREFIXES = (
    "lib/core/",
    "lib/app/",
    "lib/data/",
    "lib/models/",
    "lib/utils/",
    "lib/services/",
    "lib/theme/",
)

EXCLUDE_SERVICE_FILES = frozenset(
    {
        "lib/services/conversation_repository.dart",
        "lib/services/simulation_repository.dart",
    }
)


def parse_lcov(path: Path) -> list[tuple[str, int, int]]:
    rows: list[tuple[str, int, int]] = []
    for rec in path.read_text().split("end_of_record"):
        rec = rec.strip()
        if not rec:
            continue
        sf = None
        lf = lh = 0
        for line in rec.splitlines():
            if line.startswith("SF:"):
                sf = line[3:].strip()
            elif line.startswith("LF:"):
                lf = int(line[3:])
            elif line.startswith("LH:"):
                lh = int(line[3:])
        if sf is not None:
            rows.append((sf, lf, lh))
    return rows


def summarize(name: str, rows: list[tuple[str, int, int]]) -> tuple[int, int, float]:
    lf = sum(r[1] for r in rows)
    lh = sum(r[2] for r in rows)
    pct = 100.0 * lh / lf if lf else 100.0
    print(f"{name}: {pct:.1f}% ({lh}/{lf} lines)")
    return lf, lh, pct


def main() -> int:
    if not LCOV.is_file():
        print(f"Missing {LCOV}; run: flutter test --coverage", file=sys.stderr)
        return 1
    all_rows = parse_lcov(LCOV)
    modules = [(sf, lf, lh) for sf, lf, lh in all_rows if sf.startswith(PREFIXES)]
    modules_excl = [(sf, lf, lh) for sf, lf, lh in modules if sf not in EXCLUDE_SERVICE_FILES]

    summarize("modules (core, app, data, models, utils, services, theme)", modules)
    _, _, pct_excl = summarize("modules excl. Supabase HTTP repos", modules_excl)

    if pct_excl < 80.0:
        print("WARNING: modules excl. Supabase repos below 80%", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
