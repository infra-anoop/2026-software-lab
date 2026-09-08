# Smart Writer — Documentation

## ARCHITECTURE.md

The architecture note describes purpose, data shapes, the writer–assessor loop, and optional persistence (`public.runs` / `public.turns` in Supabase when configured). DDL: `db/supabase/runs_turns.sql` at the monorepo root.

## PDF from Markdown

To produce a PDF from `ARCHITECTURE.md` with rendered Mermaid diagrams, use the same approach as other apps in this repo (e.g. `md-to-pdf` or Mermaid CLI + Pandoc). See `ARCHITECTURE.md` in this folder for diagram sources if present.
