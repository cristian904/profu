-- Add source and year to exam_problems (var/exam/test, publication year)
ALTER TABLE public.exam_problems
ADD COLUMN IF NOT EXISTS source VARCHAR(20) CHECK (source IS NULL OR source IN ('var', 'exam', 'test'));

ALTER TABLE public.exam_problems
ADD COLUMN IF NOT EXISTS year INTEGER;

COMMENT ON COLUMN public.exam_problems.source IS 'Origin of the problem: var, exam, or test';
COMMENT ON COLUMN public.exam_problems.year IS 'Year when the source was published';
