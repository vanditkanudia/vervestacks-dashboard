-- Create VerveStacks Dashboard Database
-- Run this first:
--   psql -h localhost -U postgres -d postgres -f 00_create_database.sql

\echo 'Ensuring database "vervestacks_dashboard" exists...'

-- This SELECT returns the text "CREATE DATABASE ..." only if the DB is missing.
-- \gexec tells psql: take the output rows and execute them as SQL.
SELECT 'CREATE DATABASE vervestacks_dashboard'
WHERE NOT EXISTS (
    SELECT 1 FROM pg_database WHERE datname = 'vervestacks_dashboard'
);\gexec

\echo 'Database check/creation finished.'
