-- Smart Writer V2 — per-environment database login + schemas (backlog A31, spec 002 D5).
--
-- Run in the Supabase SQL editor of project `2026-software-lab`, once per environment.
-- Edit the two values marked EDIT, run, then discard the edited text (do not save it as a snippet).
-- Idempotent: re-running with a new password rotates it.
--
-- Result for env = '<env>':
--   login   swv2_<env>          (LOGIN, no other attributes)
--   schemas swv2_<env>, swv2_<env>_langgraph, swv2_<env>_queue
--           USAGE + CREATE granted to the login only; objects it creates are its own (full DML).
--   search_path = swv2_<env>, swv2_<env>_langgraph, swv2_<env>_queue (role level)
--   nothing granted on `public` or on the other environment's schemas.

DO $bootstrap$
DECLARE
    env text := 'staging';                          -- EDIT: 'prod' or 'staging'
    pw  text := 'REPLACE_WITH_GENERATED_PASSWORD';  -- EDIT: output of `openssl rand -hex 24`
    login text;
    other text;
    s text;
BEGIN
    IF env NOT IN ('prod', 'staging') THEN
        RAISE EXCEPTION 'env must be prod or staging, got %', env;
    END IF;
    IF pw = 'REPLACE_WITH_GENERATED_PASSWORD' OR length(pw) < 32 THEN
        RAISE EXCEPTION 'set pw to a generated password (openssl rand -hex 24) before running';
    END IF;

    login := 'swv2_' || env;
    other := CASE env WHEN 'prod' THEN 'swv2_staging' ELSE 'swv2_prod' END;

    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = login) THEN
        -- Non-superusers (the SQL editor's `postgres`) may not name SUPERUSER / REPLICATION / BYPASSRLS here.
        EXECUTE format('ALTER ROLE %I WITH LOGIN PASSWORD %L', login, pw);
    ELSE
        EXECUTE format('CREATE ROLE %I WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS PASSWORD %L', login, pw);
    END IF;

    FOREACH s IN ARRAY ARRAY[login, login || '_langgraph', login || '_queue'] LOOP
        EXECUTE format('CREATE SCHEMA IF NOT EXISTS %I', s);
        EXECUTE format('REVOKE ALL ON SCHEMA %I FROM PUBLIC', s);
        EXECUTE format('GRANT USAGE, CREATE ON SCHEMA %I TO %I', s, login);
    END LOOP;

    EXECUTE format('ALTER ROLE %I SET search_path = %I, %I, %I',
                   login, login, login || '_langgraph', login || '_queue');

    IF has_schema_privilege(login, 'public', 'CREATE') THEN
        RAISE EXCEPTION '% can create objects in public (granted to PUBLIC?); run REVOKE CREATE ON SCHEMA public FROM PUBLIC first', login;
    END IF;
    FOREACH s IN ARRAY ARRAY[other, other || '_langgraph', other || '_queue'] LOOP
        IF EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = s) THEN
            EXECUTE format('REVOKE ALL ON SCHEMA %I FROM %I', s, login);
        END IF;
    END LOOP;

    RAISE NOTICE 'ok: login % with schemas %, %_langgraph, %_queue', login, login, login, login;
END
$bootstrap$;
