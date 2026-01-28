# Local Supabase (Docker)

Run Supabase locally for the Profu schema. Requires **Docker Desktop** and **Node.js 20+**.

## One-time setup

1. **Install dependencies** (from repo root):
   ```bash
   npm install
   ```
2. **Start the stack** (from repo root):
   ```bash
   npx supabase start
   ```
   On first run, Docker will pull images; then migrations in `supabase/migrations/` are applied.

3. **Note the output**: API URL (e.g. `http://127.0.0.1:54321`), anon key, and Studio URL (e.g. `http://127.0.0.1:54323`). Use these in the Flutter app and in Studio.

## Daily workflow

- **Start:** `npx supabase start`
- **Stop:** `npx supabase stop`
- **Studio:** Open the URL shown after start (e.g. http://127.0.0.1:54323) to inspect tables and run SQL.

## Schema and RLS

- Initial tables are created by `migrations/20260128120000_profu_initial_schema.sql`.
- RLS policies are in `migrations/20260128120001_profu_rls.sql` (user-scoped access on conversations, exam_simulations, etc.).

## Connecting the Flutter app

Set the Supabase URL and anon key in your app (e.g. from env or a config file). For local dev use the values printed by `npx supabase start`.
