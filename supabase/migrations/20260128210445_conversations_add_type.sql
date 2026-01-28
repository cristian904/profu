-- Add type column to conversations to track origin of the conversation.
-- Example values:
--   - \"solve_problem\"     (from \"Vreau să rezolv o problemă\" / \"Rezolvă o problemă\" page)
--   - \"clarify_once\"      (from \"N-am înțeles la clasă\" – one-shot tab)
--   - \"clarify_step_by_step\" (from \"N-am înțeles la clasă\" – guided tab)

ALTER TABLE public.conversations
ADD COLUMN IF NOT EXISTS type VARCHAR(50);

