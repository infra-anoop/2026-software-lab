-- Research Auditor only: distilled audit summary (CLI save_to_supabase).
-- Source of truth: apps/research-auditor/app/main.py → save_to_supabase.
-- Unlinked from public.runs by design (Python does not write a run_id FK).
-- Idempotent: safe to re-run in the Supabase SQL Editor (greenfield / CREATE IF NOT EXISTS).

CREATE TABLE IF NOT EXISTS public.research_audits (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    title       text NOT NULL,
    findings    jsonb NOT NULL,
    verdict     text NOT NULL,
    critique    jsonb NOT NULL,
    iterations  integer NOT NULL,
    created_at  timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS research_audits_created_at_idx
    ON public.research_audits (created_at DESC);
CREATE INDEX IF NOT EXISTS research_audits_verdict_idx
    ON public.research_audits (verdict);
