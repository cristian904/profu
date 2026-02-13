-- Add solution and statement columns to exam_problems (for merged exam data load).
-- Run against existing DBs; init.sql already defines these for fresh installs.

ALTER TABLE exam_problems ADD COLUMN IF NOT EXISTS solution JSONB;
ALTER TABLE exam_problems ADD COLUMN IF NOT EXISTS statement TEXT;
