-- Migration: Add optional user-defined name for conversations
-- Run after auth_and_rls_migration.sql. Adds a nullable `name` column to public.conversations.

BEGIN;

ALTER TABLE public.conversations
    ADD COLUMN IF NOT EXISTS name TEXT;

COMMIT;

