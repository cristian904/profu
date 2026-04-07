-- =============================================================================
-- RPC for PostgREST / Supabase: vector similarity over public.documents
-- Required by ai_backend RAG (POST /rag/suggest-problem).
--
-- Run this in the Supabase SQL editor (or psql) if you see:
--   PGRST202 Could not find the function public.match_documents(...)
--
-- Expects documents.embedding as vector(1024) (Gemini gemini-embedding-001).
-- =============================================================================

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

COMMENT ON FUNCTION public.match_documents(vector, integer) IS
  'Nearest-neighbor search on documents.embedding (cosine distance <=>). Used by Profu RAG.';

-- PostgREST must see EXECUTE for the DB role your client uses (service_role from backend).
GRANT EXECUTE ON FUNCTION public.match_documents(vector, integer) TO anon;
GRANT EXECUTE ON FUNCTION public.match_documents(vector, integer) TO authenticated;
GRANT EXECUTE ON FUNCTION public.match_documents(vector, integer) TO service_role;
