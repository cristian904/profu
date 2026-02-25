#!/usr/bin/env python3
"""
Index exam_problems from Postgres into the documents vector table.

Reads all exam_problems, embeds each row's statement using Gemini (gemini-embedding-001,
1024 dimensions, RETRIEVAL_DOCUMENT), and inserts into documents with metadata containing
all other exam_problems fields including id.

Usage (from repo root):
  uv run python -m exam_parser.index_exam_problems_to_documents [--dry-run] [--batch-size N] [--limit N]

Requires repo root .env: GOOGLE_API_KEY, SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_ANON_KEY).

Before first run, apply the migration that sets documents.embedding to vector(1024):
  supabase/migrations/20260213130000_documents_embedding_1024.sql
"""
import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()  # .env at repo root (run from repo root)

# Metadata keys from exam_problems (all except statement, which becomes content)
METADATA_KEYS = (
    "id",
    "subject_number",
    "problem_number",
    "choices",
    "items",
    "topic",
    "school_subject",
    "difficulty",
    "source",
    "year",
    "solution",
    "created_at",
)

EMBED_DIM = 1024
EMBED_BATCH_SIZE = 50  # Gemini allows multiple texts; stay under token limits
INSERT_BATCH_SIZE = 50


def _to_serializable(obj):
    """Make value JSON-serializable for metadata (e.g. datetime -> ISO string)."""
    if obj is None:
        return None
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    if isinstance(obj, (dict, list)):
        return json.loads(json.dumps(obj, default=lambda x: x.isoformat() if hasattr(x, "isoformat") else str(x)))
    return obj


def build_metadata(row: dict) -> dict:
    """Build documents.metadata from an exam_problems row (all fields including id)."""
    return {k: _to_serializable(row.get(k)) for k in METADATA_KEYS if k in row}


def normalize_embedding(values: list[float]) -> list[float]:
    """Normalize embedding to unit length for 1024-dim (non-3072) for better similarity."""
    import math

    norm = math.sqrt(sum(x * x for x in values))
    if norm <= 0:
        return values
    return [x / norm for x in values]


def fetch_exam_problems(client, *, limit: int | None = None):
    """Fetch exam_problems; optionally limit count. Yields rows with statement not null/empty."""
    query = client.table("exam_problems").select("*").order("id")
    if limit is not None:
        query = query.limit(limit)
    response = query.execute()
    for row in response.data or []:
        st = row.get("statement")
        if st is None or (isinstance(st, str) and not st.strip()):
            continue
        yield row


def embed_batch(statements: list[str], api_key: str):
    """Embed a batch of statements with Gemini; return list of 1024-dim normalized vectors."""
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=api_key)
    result = client.models.embed_content(
        model="gemini-embedding-001",
        contents=statements,
        config=types.EmbedContentConfig(
            output_dimensionality=EMBED_DIM,
            task_type="RETRIEVAL_DOCUMENT",
        ),
    )
    embeddings = []
    for emb in result.embeddings:
        vals = list(emb.values)
        embeddings.append(normalize_embedding(vals))
    return embeddings


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Index exam_problems statements into documents vector table (Gemini 1024-dim).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only fetch and count rows; do not embed or insert.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=EMBED_BATCH_SIZE,
        metavar="N",
        help=f"Batch size for embedding and insert (default: {EMBED_BATCH_SIZE}).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Limit number of exam_problems to process (for testing).",
    )
    args = parser.parse_args()

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY")
    if not url or not key:
        sys.exit("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (or SUPABASE_ANON_KEY) in .env")

    try:
        from supabase import create_client
    except ImportError:
        sys.exit("Install supabase: poetry add supabase")

    client = create_client(url, key)
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not args.dry_run and not api_key:
        sys.exit("Set GOOGLE_API_KEY in .env for embedding")

    rows = list(fetch_exam_problems(client, limit=args.limit))
    print(f"Found {len(rows)} exam_problems with non-empty statement.", flush=True)
    if not rows:
        return
    if args.dry_run:
        print("Dry run: no embed or insert.", flush=True)
        return

    batch_size = max(1, args.batch_size)
    inserted = 0
    for i in range(0, len(rows), batch_size):
        chunk = rows[i : i + batch_size]
        statements = [r["statement"] for r in chunk]
        metadatas = [build_metadata(r) for r in chunk]
        exam_problem_ids = [r["id"] for r in chunk]

        # Idempotency: remove existing documents for these exam_problem ids
        for eid in exam_problem_ids:
            try:
                r = client.table("documents").select("id").eq("metadata->>id", str(eid)).execute()
                for row in r.data or []:
                    client.table("documents").delete().eq("id", row["id"]).execute()
            except Exception:
                pass

        embeddings = embed_batch(statements, api_key)
        if len(embeddings) != len(chunk):
            print(f"Embed batch size mismatch at batch {i // batch_size + 1}", file=sys.stderr, flush=True)
            continue

        docs = [
            {"content": st, "metadata": meta, "embedding": emb}
            for st, meta, emb in zip(statements, metadatas, embeddings)
        ]
        try:
            client.table("documents").insert(docs).execute()
            inserted += len(docs)
            print(f"Inserted {inserted}/{len(rows)} documents.", flush=True)
        except Exception as e:
            print(f"Insert failed at batch {i // batch_size + 1}: {e}", file=sys.stderr, flush=True)
            raise

    print(f"Done. Inserted {inserted} rows into documents.", flush=True)


if __name__ == "__main__":
    main()
