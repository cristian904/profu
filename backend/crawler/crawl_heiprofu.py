"""Crawl heiprofu.ro BAC M1 Mate-Info page: download all exam PDFs (Test + Barem).
Scrapes https://heiprofu.ro/examene-matematica/bacalaureat-matematica/subiecte-bac-m1-mate-info/
and downloads every linked PDF (past exams and training tests with their solutions)."""

import sys
import time
from pathlib import Path
from urllib.parse import urljoin, unquote

import httpx
from bs4 import BeautifulSoup

INDEX_URL = "https://heiprofu.ro/examene-matematica/bacalaureat-matematica/subiecte-bac-m1-mate-info/"
DOWNLOAD_DIR = Path(__file__).resolve().parent / "downloads_exams"
DELAY_SECONDS = 1.5

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}


def _log(msg: str) -> None:
    print(msg, flush=True)


def filename_from_url(url: str) -> str:
    """Return the filename as in the URL (last path segment, URL-decoded)."""
    path = url.split("?")[0].rstrip("/")
    name = path.split("/")[-1] if "/" in path else path
    return unquote(name)


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


def extract_pdf_links(html: str, page_url: str) -> list[tuple[str, str]]:
    """Find all PDF links under wp-content/uploads. Returns [(url, filename), ...] (deduplicated by filename)."""
    soup = BeautifulSoup(html, "html.parser")
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href.lower().endswith(".pdf") or "/wp-content/uploads/" not in href:
            continue
        full_url = urljoin(page_url, href)
        name = filename_from_url(full_url)
        if name in seen:
            continue
        seen.add(name)
        out.append((full_url, name))
    return out


def main() -> None:
    _log("Hei Profu crawler starting...")
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    _log(f"Download dir: {DOWNLOAD_DIR}")

    with httpx.Client(headers=HEADERS, follow_redirects=True, timeout=30.0) as client:
        _log(f"Fetching index: {INDEX_URL}")
        resp = client.get(INDEX_URL)
        resp.raise_for_status()
        links = extract_pdf_links(resp.text, INDEX_URL)
        _log(f"Found {len(links)} PDF links (exams + barem)")

        for url, filename in links:
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

    _log("Done.")


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    print("Starting Hei Profu crawler...", flush=True)
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)
