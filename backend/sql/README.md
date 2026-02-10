# SQL scripts

## Initial schema (init.sql)

Creates all tables for Profu: users, exam_problems, conversations, conversation_messages, exam_simulations, exam_simulation_problems, exam_grades, scoring_scales.

### How to run

1. **psql (local PostgreSQL):**
   ```bash
   psql -U postgres -d profu -f backend/sql/init.sql
   ```
   Create the database first if needed: `createdb -U postgres profu`

2. **Supabase:** Open the SQL Editor in the dashboard and paste the contents of `init.sql`, then run.

3. **From project root:**
   ```bash
   cd backend && psql "$DATABASE_URL" -f sql/init.sql
   ```
   (If `DATABASE_URL` is a postgres:// URL, use it as-is; psql accepts it.)

### Notes

- The script uses `CREATE TABLE IF NOT EXISTS` and is safe to run multiple times.
- It is wrapped in `BEGIN`/`COMMIT` so either all statements succeed or none do.
- The trigger `users_updated_at` updates `users.updated_at` on every row update.

## Auth and RLS migration (auth_and_rls_migration.sql)

Run **after** init.sql when using Supabase Auth. Creates `public.profiles`, a trigger to create a profile per new auth user, alters `conversations.user_id` from INTEGER to UUID (references `auth.users(id)`), and enables RLS on `conversations` and `conversation_messages`. Truncates existing conversation data so the column type change is safe.

### How to run

- **Supabase:** Open the SQL Editor and run `auth_and_rls_migration.sql`. Requires Supabase (auth schema and `auth.users` exist).
