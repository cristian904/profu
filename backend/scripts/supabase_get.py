"""
Insert a dummy user into local Supabase, then GET users to verify.
Uses stdlib only. Set SUPABASE_URL and SUPABASE_ANON_KEY in repo root .env.
Use SUPABASE_SERVICE_ROLE_KEY (from npx supabase status) to see the user in the GET (RLS).
Run from repo root: uv run python backend/scripts/supabase_get.py  (or from backend: python scripts/supabase_get.py)
"""
import json
import os
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

# Load repo root .env if present (python-dotenv not required; manual load)
_env_file = Path(__file__).resolve().parent.parent.parent / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value

SUPABASE_URL = os.getenv("SUPABASE_URL", "http://127.0.0.1:54321")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "sb_secret_N7UND0UgjKTVK-Uodkm0Hg_xSvEMPvz")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "sb_secret_N7UND0UgjKTVK-Uodkm0Hg_xSvEMPvz")

BASE_HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json",
}

# Dummy user payload (required: email, password_hash). Email made unique so script is rerunnable.
def _dummy_user() -> dict:
    return {
        "email": f"dummy-{int(time.time())}@profu.test",
        "password_hash": "dummy-hash-for-test",
        "first_name": "Dummy",
        "last_name": "User",
        "study_year": 12,
    }


def request(
    method: str,
    url: str,
    key: str,
    data: bytes | None = None,
    extra_headers: dict | None = None,
) -> bytes:
    """Send request to Supabase REST API; return response body."""
    headers = {
        **BASE_HEADERS,
        "apikey": key,
        "Authorization": f"Bearer {key}",
    }
    if extra_headers:
        headers.update(extra_headers)
    req = Request(url, data=data, headers=headers, method=method)
    with urlopen(req) as resp:
        return resp.read()


def main() -> None:
    if not SUPABASE_ANON_KEY:
        print(
            "Set SUPABASE_ANON_KEY in repo root .env (from 'npx supabase status').",
            file=sys.stderr,
        )
        sys.exit(1)

    base = SUPABASE_URL.rstrip("/")
    users_url = f"{base}/rest/v1/users"

    # 1) INSERT dummy user (anon key can insert via RLS policy)
    print("Inserting dummy user...")
    try:
        dummy = _dummy_user()
        body = request(
            "POST",
            users_url,
            SUPABASE_ANON_KEY,
            data=json.dumps(dummy).encode(),
            extra_headers={"Prefer": "return=representation"},
        )
        inserted = json.loads(body.decode())
        # PostgREST can return a list when Prefer: return=representation
        if isinstance(inserted, list) and inserted:
            inserted = inserted[0]
        print("Inserted:", json.dumps(inserted, indent=2))
    except HTTPError as e:
        print(f"INSERT failed: {e.code} {e.reason}", file=sys.stderr)
        if e.fp:
            print(e.fp.read().decode(), file=sys.stderr)
        sys.exit(1)
    except URLError as e:
        print(f"Request failed: {e.reason}", file=sys.stderr)
        sys.exit(1)

    # 2) GET users (use service_role to bypass RLS and see the row; anon would see [])
    key_for_get = SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY
    if not SUPABASE_SERVICE_ROLE_KEY:
        print(
            "\n(Using anon key for GET; RLS may return []. Set SUPABASE_SERVICE_ROLE_KEY to see all users.)",
            file=sys.stderr,
        )

    print("\nGET users...")
    try:
        body = request("GET", f"{users_url}?select=*", key_for_get)
        users = json.loads(body.decode())
        print(json.dumps(users, indent=2))
        if users and any(u.get("email") == dummy["email"] for u in users):
            print("\nDummy user found in response.")
        elif not users and not SUPABASE_SERVICE_ROLE_KEY:
            print("\nEmpty list: anon key + RLS hide other users. Add SUPABASE_SERVICE_ROLE_KEY to .env to see them.")
    except HTTPError as e:
        print(f"GET failed: {e.code} {e.reason}", file=sys.stderr)
        if e.fp:
            print(e.fp.read().decode(), file=sys.stderr)
        sys.exit(1)
    except URLError as e:
        print(f"Request failed: {e.reason}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
