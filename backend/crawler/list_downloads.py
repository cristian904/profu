"""Scan downloads/ and downloads_exams/ and report distinct variante, past exams, and training tests."""

import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DOWNLOADS_VARIANTE = SCRIPT_DIR / "downloads"  # variante-mate.ro: 2009_M1_v{N}_...
DOWNLOADS_EXAMS = SCRIPT_DIR / "downloads_exams"  # heiprofu.ro: past exams + training tests


def _log(msg: str) -> None:
    print(msg, flush=True)


def count_variante(directory: Path) -> tuple[int, int]:
    """Count distinct variante (2009_M1_v{N}_...) and total PDFs. Returns (variante_count, file_count)."""
    if not directory.exists():
        return 0, 0
    pattern = re.compile(r"2009_M1_v(\d+)_", re.IGNORECASE)
    variants: set[int] = set()
    count = 0
    for f in directory.iterdir():
        if f.suffix.lower() != ".pdf":
            continue
        m = pattern.search(f.name)
        if m:
            variants.add(int(m.group(1)))
            count += 1
    return len(variants), count


def count_past_exams_and_training(directory: Path) -> tuple[int, int, int, int]:
    """
    Classify heiprofu PDFs into past exams vs training tests.
    Returns (past_exams_distinct, past_exams_files, training_distinct, training_files).
    """
    if not directory.exists():
        return 0, 0, 0, 0

    # Past exams: ..._YYYY_var_XX_... or ..._YYYY_bar_XX_... (and var_model, var_simulare, etc.)
    # Training: ..._YYYY_Test_NN.pdf or ..._YYYY_Bar_NN.pdf
    var_bar_pattern = re.compile(
        r"(?:^|_)(\d{4})_(?:var|bar)_([a-z0-9_-]+?)(?:_[Ll][Rr][Oo]\d*|\.pdf)",
        re.IGNORECASE,
    )
    # Legacy: varianta_model, barem_model, var_simulare with year elsewhere
    var_bar_legacy = re.compile(
        r"(?:var|bar)(?:em)?_(?:model|simulare)|varianta_model|barem_model",
        re.IGNORECASE,
    )
    year_in_name = re.compile(r"_(\d{4})_")
    test_bar_pattern = re.compile(r"_(\d{4})_(?:Test|Bar)_(\d+)", re.IGNORECASE)

    past_keys: set[tuple[str, str]] = set()  # (year, variant_id)
    past_files = 0
    training_keys: set[tuple[str, int]] = set()  # (year, test_num)
    training_files = 0

    for f in directory.iterdir():
        if f.suffix.lower() != ".pdf":
            continue
        name = f.name

        # Training: _YYYY_Test_NN or _YYYY_Bar_NN
        m = test_bar_pattern.search(name)
        if m:
            training_keys.add((m.group(1), int(m.group(2))))
            training_files += 1
            continue

        # Past exam: var_ / bar_ with year
        m = var_bar_pattern.search(name)
        if m:
            past_keys.add((m.group(1), m.group(2).lower()))
            past_files += 1
            continue

        # Legacy: varianta_model, barem_model, XII ... var_simulare
        if var_bar_legacy.search(name):
            year = year_in_name.search(name)
            y = year.group(1) if year else "unknown"
            if "simulare" in name.lower():
                past_keys.add((y, "simulare"))
            else:
                past_keys.add((y, "model"))
            past_files += 1
            continue

        # Other legacy names (var-mate-info-2013, subiect-bac-olimpici, 9-varianta-oficiala, etc.)
        if "var" in name.lower() or "bar" in name.lower() or "varianta" in name.lower() or "subiect" in name.lower():
            year = year_in_name.search(name) or re.search(r"20\d{2}", name)
            y = (year.group(1) if year and year.lastindex else year.group(0)) if year else "unknown"
            past_keys.add((y, name[:50]))  # use filename as id
            past_files += 1

    return len(past_keys), past_files, len(training_keys), training_files


def main() -> None:
    _log("Scanning crawler download folders...")
    _log("")

    # --- downloads/ (variante-mate.ro) ---
    variante_count, variante_files = count_variante(DOWNLOADS_VARIANTE)
    _log(f"  {DOWNLOADS_VARIANTE.name}/ (variante-mate.ro)")
    _log(f"    Distinct variante: {variante_count}")
    _log(f"    Total PDFs:         {variante_files}")
    if variante_count > 0:
        expected = variante_count * 6
        _log(f"    (expected 6 PDFs per variant -> {expected})")
    _log("")

    # --- downloads_exams/ (heiprofu.ro) ---
    past_distinct, past_files, training_distinct, training_files = count_past_exams_and_training(
        DOWNLOADS_EXAMS
    )
    _log(f"  {DOWNLOADS_EXAMS.name}/ (heiprofu.ro)")
    _log(f"    Past exams (official BAC):  {past_distinct} distinct  |  {past_files} PDFs")
    _log(f"    Training tests:             {training_distinct} distinct  |  {training_files} PDFs")
    _log("")

    total_exams = past_files + training_files
    _log("  Summary")
    _log(f"    Variante (2009 M1):     {variante_count} distinct variante, {variante_files} files")
    _log(f"    Past exams:             {past_distinct} distinct, {past_files} files")
    _log(f"    Training tests:          {training_distinct} distinct, {training_files} files")
    _log(f"    Total PDFs in exams:    {total_exams}")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    main()
    sys.exit(0)
