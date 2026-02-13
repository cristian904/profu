-- Profu PostgreSQL initial schema
-- Run this script against your PostgreSQL database (e.g. psql -f init.sql or Supabase SQL editor)

BEGIN;

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
CREATE TABLE IF NOT EXISTS exam_simulations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    started_at TIMESTAMPTZ DEFAULT NOW(),
    finished_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_exam_simulations_user_id ON exam_simulations(user_id);

-- Problems included in a simulation (many problems per exam)
CREATE TABLE IF NOT EXISTS exam_simulation_problems (
    id SERIAL PRIMARY KEY,
    exam_simulation_id INTEGER NOT NULL REFERENCES exam_simulations(id) ON DELETE CASCADE,
    exam_problem_id INTEGER NOT NULL REFERENCES exam_problems(id) ON DELETE CASCADE,
    order_index INTEGER,
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

create table if not exists documents (
  id uuid primary key default gen_random_uuid(),
  content text,
  metadata jsonb,
  embedding vector(1536) -- Match this to your model's dimensions
);

COMMIT;
