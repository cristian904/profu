# Scripts

Utility scripts for the Profu project.

## Available Scripts

### `start-langfuse.sh`

Starts **Langfuse v3** locally with Docker Compose. The stack includes:

- **langfuse-web** + **langfuse-worker** (Langfuse 3.x)
- **PostgreSQL** — app metadata
- **ClickHouse** — traces / analytics (required by Langfuse v3)
- **Redis** — queue
- **MinIO** — S3-compatible storage for uploads

Compose file: `scripts/langfuse/docker-compose.yml` (copied to `.langfuse/docker-compose.yml`).

Runtime env: `.langfuse/.env` (created on first start; **not** committed — see `.gitignore`).

**Usage:**

```bash
# Start Langfuse
./scripts/start-langfuse.sh

# Stop Langfuse
./scripts/start-langfuse.sh stop

# Restart Langfuse
./scripts/start-langfuse.sh restart

# View logs
./scripts/start-langfuse.sh logs

# Check status
./scripts/start-langfuse.sh status

# Replace compose + regenerate .env (after upgrading this repo’s template)
./scripts/start-langfuse.sh reconfigure

# Show help
./scripts/start-langfuse.sh help
```

**Access:**

- UI: `http://localhost:3000` (or `LANGFUSE_PORT`)
- API: `http://localhost:3000/api`

**First-time setup:**

1. Run `./scripts/start-langfuse.sh`
2. Open the UI URL printed at the end (and use credentials printed for Postgres, ClickHouse, Redis, MinIO)
3. Create an account and project in Langfuse
4. In the Langfuse UI: **Project settings → API keys**, create or copy the **full** keys into the **repository root** `.env` (not `.langfuse/.env` — that file only has Docker/NextAuth secrets, **not** `pk-lf` / `sk-lf`):

```env
LANGFUSE_PUBLIC_KEY=pk-lf-<paste the entire key from the UI>
LANGFUSE_SECRET_KEY=sk-lf-<paste the entire key from the UI>
LANGFUSE_HOST=http://localhost:3000
```

**401 Unauthorized:** Values like `pk-lf-...` or `sk-lf-...` copied from docs are **placeholders**. You must paste the real strings from the UI. The seed script exits early if it still sees `...` in a key.

**Custom ports:**

```bash
LANGFUSE_PORT=3001 ./scripts/start-langfuse.sh start
POSTGRES_PORT=5433 ./scripts/start-langfuse.sh start
```

**Upgrading from the old single-container compose**

If you previously used an older `docker-compose.yml` (Postgres + `langfuse:latest` only), Langfuse v3 **requires ClickHouse**. The script auto-replaces an outdated `.langfuse/docker-compose.yml` when it does not contain a `clickhouse` service.

If containers still fail, from `.langfuse/` run:

```bash
docker compose down -v
```

Then `./scripts/start-langfuse.sh` again (this **deletes** Docker volumes).

**Requirements:**

- Docker
- Docker Compose v2 (or `docker-compose` v1)

---

### `seed_langfuse_prompts.py`

Python CLI: uploads every **`system_prompt`** block from `backend/ai_backend/prompts.yaml` into **Langfuse Prompt Management** as **text** prompts.

**Names:** `profu/<yaml-path>` (e.g. `profu/clarify_chat`, `profu/problem_solving/hint_provider`).

**Environment (same as the app):**

- `LANGFUSE_PUBLIC_KEY`
- `LANGFUSE_SECRET_KEY`
- `LANGFUSE_HOST` (e.g. `http://localhost:3000` for local)

The script loads the repository **`.env`** from the project root automatically (use **`--env-file`** for another path).

**Usage:**

```bash
uv run python scripts/seed_langfuse_prompts.py --dry-run
uv run python scripts/seed_langfuse_prompts.py
```

**Note:** Prompts embedded only in code (e.g. OCR vision text in `ocr.py`) are **not** in `prompts.yaml` and are not seeded.

---

### `version_langfuse_prompt.py` (Langfuse Integration Skill)

Python CLI: creates a **new version** in Langfuse Prompt Management for **one prompt**.

Use this when you changed a single prompt and do not want to re-seed all prompts. Located in `.cursor/skills/langfuse-integration/scripts/`.

**Name mapping:**

- Dot path `guided_learning.question_asker` -> `profu/guided_learning/question_asker`

**Prompt source options (priority order):**

1. `--prompt-text`
2. `--prompt-file`
3. `--from-yaml` (or default behavior when no source option is passed)

**Usage:**

```bash
# Read prompt text from backend/ai_backend/prompts.yaml at the provided dot path
uv run python .cursor/skills/langfuse-integration/scripts/version_langfuse_prompt.py --dot-path guided_learning.question_asker --from-yaml

# Inline text
uv run python .cursor/skills/langfuse-integration/scripts/version_langfuse_prompt.py --dot-path clarify_chat --prompt-text "You are..."

# Read text from file
uv run python .cursor/skills/langfuse-integration/scripts/version_langfuse_prompt.py --dot-path clarify_chat --prompt-file /tmp/clarify_chat_prompt.txt

# Validate only (no API call)
uv run python .cursor/skills/langfuse-integration/scripts/version_langfuse_prompt.py --dot-path clarify_chat --from-yaml --dry-run
```
