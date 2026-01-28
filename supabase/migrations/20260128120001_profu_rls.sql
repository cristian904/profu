-- Row Level Security for Profu tables.
-- Links public.users to Supabase Auth via auth_id (UUID from auth.users).
-- Run after initial schema. When using Supabase Auth, set users.auth_id on signup.

-- Link app users to Supabase Auth (optional; set on signup)
ALTER TABLE public.users
ADD COLUMN IF NOT EXISTS auth_id UUID UNIQUE REFERENCES auth.users(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_users_auth_id ON public.users(auth_id);

-- Users: users can read/update only their own row (by auth_id)
ALTER TABLE public.users ENABLE ROW LEVEL SECURITY;

CREATE POLICY "users_select_own"
ON public.users FOR SELECT
USING (auth_id = auth.uid());

CREATE POLICY "users_update_own"
ON public.users FOR UPDATE
USING (auth_id = auth.uid());

-- Service role can manage all users (e.g. signup flow)
CREATE POLICY "users_insert_service"
ON public.users FOR INSERT
WITH CHECK (true);

-- Conversations: users can CRUD only their own (via user_id -> users.auth_id)
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "conversations_select_own"
ON public.conversations FOR SELECT
USING (
  user_id IN (SELECT id FROM public.users WHERE auth_id = auth.uid())
);

CREATE POLICY "conversations_insert_own"
ON public.conversations FOR INSERT
WITH CHECK (
  user_id IN (SELECT id FROM public.users WHERE auth_id = auth.uid())
);

CREATE POLICY "conversations_update_own"
ON public.conversations FOR UPDATE
USING (
  user_id IN (SELECT id FROM public.users WHERE auth_id = auth.uid())
);

CREATE POLICY "conversations_delete_own"
ON public.conversations FOR DELETE
USING (
  user_id IN (SELECT id FROM public.users WHERE auth_id = auth.uid())
);

-- Conversation messages: CRUD only if the conversation belongs to the user
ALTER TABLE public.conversation_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "conversation_messages_select_own"
ON public.conversation_messages FOR SELECT
USING (
  EXISTS (
    SELECT 1 FROM public.conversations c
    WHERE c.id = conversation_id
    AND c.user_id IN (SELECT id FROM public.users WHERE auth_id = auth.uid())
  )
);

CREATE POLICY "conversation_messages_insert_own"
ON public.conversation_messages FOR INSERT
WITH CHECK (
  EXISTS (
    SELECT 1 FROM public.conversations c
    WHERE c.id = conversation_id
    AND c.user_id IN (SELECT id FROM public.users WHERE auth_id = auth.uid())
  )
);

CREATE POLICY "conversation_messages_update_own"
ON public.conversation_messages FOR UPDATE
USING (
  EXISTS (
    SELECT 1 FROM public.conversations c
    WHERE c.id = conversation_id
    AND c.user_id IN (SELECT id FROM public.users WHERE auth_id = auth.uid())
  )
);

CREATE POLICY "conversation_messages_delete_own"
ON public.conversation_messages FOR DELETE
USING (
  EXISTS (
    SELECT 1 FROM public.conversations c
    WHERE c.id = conversation_id
    AND c.user_id IN (SELECT id FROM public.users WHERE auth_id = auth.uid())
  )
);

-- Exam simulations: users can CRUD only their own
ALTER TABLE public.exam_simulations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "exam_simulations_select_own"
ON public.exam_simulations FOR SELECT
USING (
  user_id IN (SELECT id FROM public.users WHERE auth_id = auth.uid())
);

CREATE POLICY "exam_simulations_insert_own"
ON public.exam_simulations FOR INSERT
WITH CHECK (
  user_id IN (SELECT id FROM public.users WHERE auth_id = auth.uid())
);

CREATE POLICY "exam_simulations_update_own"
ON public.exam_simulations FOR UPDATE
USING (
  user_id IN (SELECT id FROM public.users WHERE auth_id = auth.uid())
);

CREATE POLICY "exam_simulations_delete_own"
ON public.exam_simulations FOR DELETE
USING (
  user_id IN (SELECT id FROM public.users WHERE auth_id = auth.uid())
);

-- Exam simulation problems: CRUD if the simulation belongs to the user
ALTER TABLE public.exam_simulation_problems ENABLE ROW LEVEL SECURITY;

CREATE POLICY "exam_simulation_problems_all_own"
ON public.exam_simulation_problems FOR ALL
USING (
  EXISTS (
    SELECT 1 FROM public.exam_simulations es
    WHERE es.id = exam_simulation_id
    AND es.user_id IN (SELECT id FROM public.users WHERE auth_id = auth.uid())
  )
);

-- Exam grades: CRUD if the simulation problem's simulation belongs to the user
ALTER TABLE public.exam_grades ENABLE ROW LEVEL SECURITY;

CREATE POLICY "exam_grades_all_own"
ON public.exam_grades FOR ALL
USING (
  EXISTS (
    SELECT 1 FROM public.exam_simulation_problems esp
    JOIN public.exam_simulations es ON es.id = esp.exam_simulation_id
    WHERE esp.id = exam_simulation_problem_id
    AND es.user_id IN (SELECT id FROM public.users WHERE auth_id = auth.uid())
  )
);

-- Exam problems and scoring scales: allow read for anon/authenticated (catalog data)
ALTER TABLE public.exam_problems ENABLE ROW LEVEL SECURITY;

CREATE POLICY "exam_problems_select_public"
ON public.exam_problems FOR SELECT
USING (true);

CREATE POLICY "exam_problems_all_service"
ON public.exam_problems FOR ALL
TO service_role
USING (true);

ALTER TABLE public.scoring_scales ENABLE ROW LEVEL SECURITY;

CREATE POLICY "scoring_scales_select_public"
ON public.scoring_scales FOR SELECT
USING (true);

CREATE POLICY "scoring_scales_all_service"
ON public.scoring_scales FOR ALL
TO service_role
USING (true);
