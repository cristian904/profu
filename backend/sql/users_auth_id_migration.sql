-- Migration: link public.users to Supabase Auth (auth_id) + RLS
-- Run after init.sql and auth_and_rls_migration.sql. Requires auth.users.

BEGIN;

-- 1. Add auth_id column (one row per auth user)
ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS auth_id UUID UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE;

-- 2. Allow auth-only users (no password in this table)
ALTER TABLE public.users
    ALTER COLUMN password_hash DROP NOT NULL;

-- 3. RLS on public.users
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can view own row" ON public.users;
CREATE POLICY "Users can view own row"
    ON public.users FOR SELECT
    TO authenticated
    USING (auth_id = auth.uid());

DROP POLICY IF EXISTS "Users can insert own row" ON public.users;
CREATE POLICY "Users can insert own row"
    ON public.users FOR INSERT
    TO authenticated
    WITH CHECK (auth_id = auth.uid());

DROP POLICY IF EXISTS "Users can update own row" ON public.users;
CREATE POLICY "Users can update own row"
    ON public.users FOR UPDATE
    TO authenticated
    USING (auth_id = auth.uid())
    WITH CHECK (auth_id = auth.uid());

COMMIT;
