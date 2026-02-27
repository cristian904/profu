-- Migration: Solve-problem monthly quota count (from account creation).
-- Run after auth_and_rls_migration.sql. Requires auth.users and public.conversations.
-- Counts conversations with type = 'problem_solving' in the "current month" for the user,
-- where the first month is from auth.users.created_at to end of that calendar month.

BEGIN;

CREATE OR REPLACE FUNCTION public.get_solve_conversations_count_current_month(p_user_id UUID)
RETURNS INTEGER
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
  user_created_at TIMESTAMPTZ;
  period_start TIMESTAMPTZ;
  period_end TIMESTAMPTZ;
  same_calendar_month BOOLEAN;
  cnt INTEGER;
BEGIN
  -- Get user's account creation date from auth.users
  SELECT created_at INTO user_created_at
  FROM auth.users
  WHERE id = p_user_id;

  IF user_created_at IS NULL THEN
    RETURN 0;
  END IF;

  -- Same calendar month as account creation? (same year-month and we're past creation)
  same_calendar_month := (
    date_trunc('month', user_created_at) = date_trunc('month', current_timestamp)
    AND user_created_at <= current_timestamp
  );

  IF same_calendar_month THEN
    period_start := user_created_at;
    period_end := date_trunc('month', user_created_at) + interval '1 month' - interval '1 second';
  ELSE
    period_start := date_trunc('month', current_timestamp);
    period_end := date_trunc('month', current_timestamp) + interval '1 month' - interval '1 second';
  END IF;

  SELECT COUNT(*)::INTEGER INTO cnt
  FROM public.conversations c
  WHERE c.user_id = p_user_id
    AND c.type = 'problem_solving'
    AND c.created_at >= period_start
    AND c.created_at <= period_end;

  RETURN cnt;
END;
$$;

COMMIT;
