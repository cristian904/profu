-- Combined database init script for Profu
-- Runs all schema and migrations in order. Use on a fresh DB (e.g. psql -f init_full.sql).
-- Requires PostgreSQL with Supabase Auth (auth.users) for RLS and profiles.

BEGIN;

-- =============================================================================
-- 1. Base schema (from init.sql)
-- =============================================================================

-- Users
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(50),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    password_hash VARCHAR(255) NOT NULL,
    study_year INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Exam problems (catalog of problems)
CREATE TABLE IF NOT EXISTS exam_problems (
    id SERIAL PRIMARY KEY,
    subject_number INTEGER,
    problem_number INTEGER,
    choices JSONB,
    items JSONB,
    topic VARCHAR(255),
    school_subject VARCHAR(100),
    difficulty VARCHAR(50),
    source VARCHAR(20) CHECK (source IS NULL OR source IN ('var', 'exam', 'test')),
    year INTEGER,
    statement TEXT,
    solution JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Conversations (thread container per user)
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title VARCHAR(500),
    school_subject VARCHAR(100),
    type VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);

-- Conversation messages (one row per message)
CREATE TABLE IF NOT EXISTS conversation_messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    speaker VARCHAR(20) NOT NULL,
    content TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conversation_messages_conversation_id ON conversation_messages(conversation_id);

-- Exam simulation session (one exam per user)
-- user_id is optional: Simulari flow inserts auth_user_id only (JWT); legacy rows may set user_id.
CREATE TABLE IF NOT EXISTS exam_simulations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    -- Optional: direct link to Supabase auth user for RLS-friendly queries
    auth_user_id UUID,
    -- School subject for the simulation (e.g. math, informatics)
    school_subject VARCHAR(100) DEFAULT 'math' NOT NULL,
    -- Total score given by the student for this simulation (0-100)
    student_score NUMERIC(5, 2),
    started_at TIMESTAMPTZ DEFAULT NOW(),
    finished_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_exam_simulations_user_id ON exam_simulations(user_id);
CREATE INDEX IF NOT EXISTS idx_exam_simulations_auth_user_id ON exam_simulations(auth_user_id);
CREATE INDEX IF NOT EXISTS idx_exam_simulations_user_subject_started_at
    ON exam_simulations(user_id, school_subject, started_at);

-- Problems included in a simulation (many problems per exam)
CREATE TABLE IF NOT EXISTS exam_simulation_problems (
    id SERIAL PRIMARY KEY,
    exam_simulation_id INTEGER NOT NULL REFERENCES exam_simulations(id) ON DELETE CASCADE,
    exam_problem_id INTEGER NOT NULL REFERENCES exam_problems(id) ON DELETE CASCADE,
    -- Display order of problems within the simulation
    order_index INTEGER,
    -- Bac subiect number (1, 2, 3)
    subject_number INTEGER NOT NULL,
    -- Problem number within the subiect (e.g. 1..6 for Subiectul I, 1..2 for II/III)
    problem_number INTEGER NOT NULL,
    -- Score given by the student for this problem
    student_score NUMERIC(5, 2),
    UNIQUE(exam_simulation_id, exam_problem_id)
);

CREATE INDEX IF NOT EXISTS idx_exam_simulation_problems_simulation_id ON exam_simulation_problems(exam_simulation_id);
CREATE INDEX IF NOT EXISTS idx_exam_simulation_problems_problem_id ON exam_simulation_problems(exam_problem_id);

-- Grade per problem attempt within a simulation
CREATE TABLE IF NOT EXISTS exam_grades (
    id SERIAL PRIMARY KEY,
    exam_simulation_problem_id INTEGER NOT NULL REFERENCES exam_simulation_problems(id) ON DELETE CASCADE,
    difficulty VARCHAR(50),
    grade NUMERIC(5, 2) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_exam_grades_simulation_problem_id ON exam_grades(exam_simulation_problem_id);

-- Scoring rubric per exam problem (barem)
CREATE TABLE IF NOT EXISTS scoring_scales (
    id SERIAL PRIMARY KEY,
    exam_problem_id INTEGER NOT NULL REFERENCES exam_problems(id) ON DELETE CASCADE,
    solution TEXT NOT NULL,
    order_index INTEGER,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_scoring_scales_exam_problem_id ON scoring_scales(exam_problem_id);

-- Optional: trigger to update users.updated_at
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS users_updated_at ON users;
CREATE TRIGGER users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE PROCEDURE set_updated_at();

-- pgvector extension required for embedding column (Supabase has it; local Postgres may need: apt install postgresql-16-pgvector)
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS documents (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  content text,
  metadata jsonb,
  embedding vector(1024)
);

-- Vector similarity RPC for RAG (PostgREST: /rest/v1/rpc/match_documents)
CREATE OR REPLACE FUNCTION public.match_documents(
  query_embedding vector(1024),
  match_count integer DEFAULT 5
)
RETURNS TABLE (
  id uuid,
  content text,
  metadata jsonb
)
LANGUAGE sql
STABLE
PARALLEL SAFE
AS $$
  SELECT
    d.id,
    d.content,
    d.metadata
  FROM public.documents AS d
  WHERE d.embedding IS NOT NULL
  ORDER BY d.embedding <=> query_embedding
  LIMIT LEAST(match_count, 100);
$$;

GRANT EXECUTE ON FUNCTION public.match_documents(vector, integer) TO anon;
GRANT EXECUTE ON FUNCTION public.match_documents(vector, integer) TO authenticated;
GRANT EXECUTE ON FUNCTION public.match_documents(vector, integer) TO service_role;

-- =============================================================================
-- 2. Supabase Auth + profiles + conversations by auth.users (UUID) + RLS
-- =============================================================================

-- Profiles table (one per auth user)
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    username TEXT,
    display_name TEXT,
    avatar_url TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Trigger: create profile row when a new auth user is created
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (id)
    VALUES (NEW.id);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
    AFTER INSERT ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION public.handle_new_user();

-- Conversations: switch user_id from integer to UUID (auth.users)
TRUNCATE TABLE conversation_messages, conversations;

DROP POLICY IF EXISTS "Users can view own conversations" ON conversations;
DROP POLICY IF EXISTS "Users can insert own conversations" ON conversations;
DROP POLICY IF EXISTS "Users can update own conversations" ON conversations;
DROP POLICY IF EXISTS "Users can delete own conversations" ON conversations;
DROP POLICY IF EXISTS conversations_select_own ON conversations;
DROP POLICY IF EXISTS conversations_insert_own ON conversations;
DROP POLICY IF EXISTS conversations_update_own ON conversations;
DROP POLICY IF EXISTS conversations_delete_own ON conversations;

DROP POLICY IF EXISTS "Users can view messages of own conversations" ON conversation_messages;
DROP POLICY IF EXISTS "Users can insert messages in own conversations" ON conversation_messages;
DROP POLICY IF EXISTS "Users can update messages in own conversations" ON conversation_messages;
DROP POLICY IF EXISTS "Users can delete messages in own conversations" ON conversation_messages;
DROP POLICY IF EXISTS conversation_messages_select_own ON conversation_messages;
DROP POLICY IF EXISTS conversation_messages_insert_own ON conversation_messages;
DROP POLICY IF EXISTS conversation_messages_update_own ON conversation_messages;
DROP POLICY IF EXISTS conversation_messages_delete_own ON conversation_messages;

ALTER TABLE conversations
    DROP CONSTRAINT IF EXISTS conversations_user_id_fkey;

ALTER TABLE conversations
    DROP COLUMN user_id;

ALTER TABLE conversations
    ADD COLUMN user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);

-- RLS on conversations
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view own conversations"
    ON conversations FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own conversations"
    ON conversations FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own conversations"
    ON conversations FOR UPDATE
    TO authenticated
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own conversations"
    ON conversations FOR DELETE
    TO authenticated
    USING (auth.uid() = user_id);

-- RLS on conversation_messages
ALTER TABLE conversation_messages ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users can view messages of own conversations"
    ON conversation_messages FOR SELECT
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM conversations c
            WHERE c.id = conversation_messages.conversation_id
            AND c.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can insert messages in own conversations"
    ON conversation_messages FOR INSERT
    TO authenticated
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM conversations c
            WHERE c.id = conversation_messages.conversation_id
            AND c.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can update messages in own conversations"
    ON conversation_messages FOR UPDATE
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM conversations c
            WHERE c.id = conversation_messages.conversation_id
            AND c.user_id = auth.uid()
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM conversations c
            WHERE c.id = conversation_messages.conversation_id
            AND c.user_id = auth.uid()
        )
    );

CREATE POLICY "Users can delete messages in own conversations"
    ON conversation_messages FOR DELETE
    TO authenticated
    USING (
        EXISTS (
            SELECT 1 FROM conversations c
            WHERE c.id = conversation_messages.conversation_id
            AND c.user_id = auth.uid()
        )
    );

-- =============================================================================
-- 3. Link public.users to Supabase Auth (auth_id) + RLS on users
-- =============================================================================

ALTER TABLE public.users
    ADD COLUMN IF NOT EXISTS auth_id UUID UNIQUE REFERENCES auth.users(id) ON DELETE CASCADE;

ALTER TABLE public.users
    ALTER COLUMN password_hash DROP NOT NULL;

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

-- =============================================================================
-- 4. Add optional columns to exam_problems (statement/solution if missing)
-- =============================================================================

ALTER TABLE exam_problems ADD COLUMN IF NOT EXISTS solution JSONB;
ALTER TABLE exam_problems ADD COLUMN IF NOT EXISTS statement TEXT;

-- =============================================================================
-- 5. Add optional user-defined name for conversations
-- =============================================================================

ALTER TABLE public.conversations
    ADD COLUMN IF NOT EXISTS name TEXT;

-- =============================================================================
-- 6. Solve-problem monthly quota count function
-- =============================================================================

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
  SELECT created_at INTO user_created_at
  FROM auth.users
  WHERE id = p_user_id;

  IF user_created_at IS NULL THEN
    RETURN 0;
  END IF;

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

-- =============================================================================
-- 7. Simulari: columns for exam_simulations on existing databases (PostgREST PGRST204)
-- =============================================================================
-- CREATE TABLE IF NOT EXISTS does not add new columns to an already-created table.
-- If auth_user_id (etc.) is missing, API inserts fail with "not found in the schema cache".
-- After applying, refresh PostgREST if needed: NOTIFY pgrst, 'reload schema';

ALTER TABLE exam_simulations ADD COLUMN IF NOT EXISTS auth_user_id UUID;
ALTER TABLE exam_simulations ADD COLUMN IF NOT EXISTS school_subject VARCHAR(100);
ALTER TABLE exam_simulations ADD COLUMN IF NOT EXISTS student_score NUMERIC(5, 2);

UPDATE exam_simulations SET school_subject = COALESCE(school_subject, 'mate')
WHERE school_subject IS NULL;

ALTER TABLE exam_simulations ALTER COLUMN school_subject SET DEFAULT 'mate';

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM exam_simulations WHERE school_subject IS NULL) THEN
        ALTER TABLE exam_simulations ALTER COLUMN school_subject SET NOT NULL;
    END IF;
END;
$$;

-- Simulari inserts do not send legacy user_id; allow NULL.
ALTER TABLE exam_simulations ALTER COLUMN user_id DROP NOT NULL;

CREATE INDEX IF NOT EXISTS idx_exam_simulations_auth_user_id ON exam_simulations(auth_user_id);
CREATE INDEX IF NOT EXISTS idx_exam_simulations_user_subject_started_at
    ON exam_simulations(user_id, school_subject, started_at);

ALTER TABLE exam_simulation_problems ADD COLUMN IF NOT EXISTS subject_number INTEGER;
ALTER TABLE exam_simulation_problems ADD COLUMN IF NOT EXISTS problem_number INTEGER;
ALTER TABLE exam_simulation_problems ADD COLUMN IF NOT EXISTS student_score NUMERIC(5, 2);

-- =============================================================================
-- 8. Helper view for simulation scores history
-- =============================================================================

CREATE OR REPLACE VIEW public.v_simulation_scores AS
SELECT
    s.id AS simulation_id,
    s.auth_user_id,
    s.school_subject,
    s.started_at,
    s.finished_at,
    s.student_score
FROM exam_simulations s;

COMMIT;
