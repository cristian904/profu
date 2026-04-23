"""Crawl variante-mate.ro M1 variant pages and download 6 PDFs per variant.

Files are stored under root downloads in separate problems/solutions folders,
while keeping the same filename for each problem-solution pair.
"""

import sys
import time
from pathlib import Path
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

# --- Direct PDF URLs (BAC-M1-2009 statements, RBAC-M1-2009 solutions) ---
STATEMENT_BASE = "https://variante-mate.ro/bacalaureat/BAC-M1-2009"
SOLUTION_BASE = "https://variante-mate.ro/bacalaureat/RBAC-M1-2009"
STATEMENT_PATHS = [("i", 1), ("ii", 2), ("iii", 3)]
SOLUTION_PATHS = [("i", 1), ("ii", 2), ("iii", 3)]

ROOT_DOWNLOAD_DIR = Path(__file__).resolve().parents[2] / "downloads"
RUN_FOLDER = "var_2009"
PROBLEMS_DIR = ROOT_DOWNLOAD_DIR / RUN_FOLDER / "problems"
SOLUTIONS_DIR = ROOT_DOWNLOAD_DIR / RUN_FOLDER / "solutions"
DELAY_SECONDS = 1.5

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def _log(msg: str) -> None:
    print(msg, flush=True)


def resolve_and_download(client: httpx.Client, url: str) -> bytes | None:
    """GET the URL. If response is application/pdf, return its bytes. Returns None if no PDF."""
    try:
        resp = client.get(url, follow_redirects=True, headers=HEADERS, timeout=30.0)
        resp.raise_for_status()
        content_type = (resp.headers.get("content-type") or "").split(";")[0].strip().lower()
        if content_type == "application/pdf":
            return resp.content
        return None
    except Exception:
        return None


def links_for_variant(variant: int) -> list[tuple[str, str, int]]:
    """Build the 6 direct links for a variant.

    Returns tuples of (url, document_kind, subject_number), where document_kind is
    "problem" or "solution".
    """
    v = f"{variant:03d}"
    out: list[tuple[str, str, int]] = []
    for path, subject in STATEMENT_PATHS:
        out.append((f"{STATEMENT_BASE}/d_mt1_{path}_{v}.pdf", "problem", subject))
    for path, subject in SOLUTION_PATHS:
        out.append((f"{SOLUTION_BASE}/d_mt1_{path}_{v}.pdf", "solution", subject))
    return out


# --- Parser (for HTML-based variant pages if needed by other crawlers) ---
def _links_after_heading(heading, page_url: str) -> list[str]:
    """Find the next 3 links labeled 'Subiectul 1', 'Subiectul 2', 'Subiectul 3' after a heading."""
    found: dict[int, str] = {}
    siblings = list(heading.find_next_siblings())
    for sibling in siblings:
        link_candidates: list[tuple[str, str]] = []
        if sibling.name == "a" and sibling.get("href"):
            link_candidates.append(((sibling.get_text() or "").strip(), sibling["href"]))
        for a in sibling.find_all("a", href=True):
            link_candidates.append(((a.get_text() or "").strip(), a["href"]))
        for link_text, href in link_candidates:
            if link_text == "Subiectul 1":
                found[1] = urljoin(page_url, href)
            elif link_text == "Subiectul 2":
                found[2] = urljoin(page_url, href)
            elif link_text == "Subiectul 3":
                found[3] = urljoin(page_url, href)
        if len(found) >= 3:
            break
    return [found[i] for i in (1, 2, 3) if i in found]


def extract_pdf_links(html: str, page_url: str) -> list[tuple[str, str]]:
    """Extract the 6 PDF links from a variant page. Returns [(url, filename_suffix), ...]."""
    soup = BeautifulSoup(html, "html.parser")
    statements: list[str] = []
    solutions: list[str] = []
    for heading in soup.find_all(["h2", "h3"]):
        text = (heading.get_text() or "").strip()
        if text == "Enunturi":
            statements = _links_after_heading(heading, page_url)
        elif text == "Rezolvari":
            solutions = _links_after_heading(heading, page_url)
    if len(statements) != 3 or len(solutions) != 3:
        return []
    suffixes = ["s1_statement", "s2_statement", "s3_statement", "s1_solution", "s2_solution", "s3_solution"]
    return list(zip(statements + solutions, suffixes))


def main() -> None:
    """Run crawler and save paired files in problems/solutions folders."""
    _log("Crawler starting...")
    ROOT_DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    PROBLEMS_DIR.mkdir(parents=True, exist_ok=True)
    SOLUTIONS_DIR.mkdir(parents=True, exist_ok=True)
    _log(f"Root download dir: {ROOT_DOWNLOAD_DIR}")
    _log(f"Run folder: {ROOT_DOWNLOAD_DIR / RUN_FOLDER}")
    _log(f"Problems dir: {PROBLEMS_DIR}")
    _log(f"Solutions dir: {SOLUTIONS_DIR}")

    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=30.0) as client:
        for variant in range(1, 101):
            _log(f"Variant {variant}: downloading 6 PDFs ...")
            links = links_for_variant(variant)

            for url, document_kind, subject in links:
                filename = f"2009_M1_v{variant}_s{subject}.pdf"
                target_dir = PROBLEMS_DIR if document_kind == "problem" else SOLUTIONS_DIR
                filepath = target_dir / filename
                if filepath.exists():
                    _log(f"  Skip (exists): {filename}")
                    continue
                pdf_bytes = resolve_and_download(client, url)
                if pdf_bytes:
                    filepath.write_bytes(pdf_bytes)
                    _log(f"  Saved: {filename}")
                else:
                    _log(f"  No PDF: {filename} <- {url}")
                time.sleep(DELAY_SECONDS)

            time.sleep(DELAY_SECONDS)

    _log("Done.")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    print("Starting crawler script...", flush=True)
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)
