-- Shared execution-trace tables for smart-writer and research-auditor.
-- Source of truth: modules/lab_shared/.../supabase_repo.py (do not invent columns).
-- Idempotent: safe to re-run in the Supabase SQL Editor (greenfield / CREATE IF NOT EXISTS).
-- Does NOT ALTER existing tables if columns already diverge — treat as operator greenfield.

-- runs: one row per workflow execution
CREATE TABLE IF NOT EXISTS public.runs (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    topic         text NOT NULL,
    status        text NOT NULL
                  CHECK (status IN ('running', 'completed', 'failed')),
    created_at    timestamptz NOT NULL DEFAULT now(),
    completed_at  timestamptz,
    final_output  jsonb,
    error         text,
    trace_id      text
);

-- turns: one row per agent step within a run
CREATE TABLE IF NOT EXISTS public.turns (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id      uuid NOT NULL REFERENCES public.runs (id) ON DELETE CASCADE,
    step        integer NOT NULL,
    agent       text NOT NULL,
    input       jsonb NOT NULL,
    output      jsonb,
    ok          boolean NOT NULL,
    error       text,
    created_at  timestamptz NOT NULL DEFAULT now()
);

-- Indexes for FK lookups and common filters
CREATE INDEX IF NOT EXISTS turns_run_id_idx ON public.turns (run_id);
CREATE INDEX IF NOT EXISTS turns_run_id_step_idx ON public.turns (run_id, step);
CREATE INDEX IF NOT EXISTS runs_created_at_idx ON public.runs (created_at DESC);
CREATE INDEX IF NOT EXISTS runs_status_idx ON public.runs (status);
