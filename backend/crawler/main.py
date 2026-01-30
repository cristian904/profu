"""Crawl variante-mate.ro M1 variant pages and download the 6 PDFs per variant.
All logic in one file; other crawlers can be added below or in the same script."""

import sys
import time
from pathlib import Path
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

# --- Direct PDF URLs (BAC-M1-2009 statements, RBAC-M1-2009 solutions) ---
STATEMENT_BASE = "https://variante-mate.ro/bacalaureat/BAC-M1-2009"
SOLUTION_BASE = "https://variante-mate.ro/bacalaureat/RBAC-M1-2009"
STATEMENT_PATHS = [("i", "s1_statement"), ("ii", "s2_statement"), ("iii", "s3_statement")]
SOLUTION_PATHS = [("i", "s1_solution"), ("ii", "s2_solution"), ("iii", "s3_solution")]

DOWNLOAD_DIR = Path(__file__).resolve().parent / "downloads"
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


def links_for_variant(variant: int) -> list[tuple[str, str]]:
    """Build the 6 (url, filename_suffix) pairs for a variant from the direct PDF URL pattern."""
    v = f"{variant:03d}"
    out = []
    for path, suffix in STATEMENT_PATHS:
        out.append((f"{STATEMENT_BASE}/d_mt1_{path}_{v}.pdf", suffix))
    for path, suffix in SOLUTION_PATHS:
        out.append((f"{SOLUTION_BASE}/d_mt1_{path}_{v}.pdf", suffix))
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
    _log("Crawler starting...")
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    _log(f"Download dir: {DOWNLOAD_DIR}")

    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=30.0) as client:
        for variant in range(1, 101):
            _log(f"Variant {variant}: downloading 6 PDFs ...")
            links = links_for_variant(variant)

            for url, suffix in links:
                filename = f"2009_M1_v{variant}_{suffix}.pdf"
                filepath = DOWNLOAD_DIR / filename
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
