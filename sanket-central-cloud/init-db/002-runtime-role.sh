#!/bin/sh
set -eu
: "${POSTGRES_APP_PASSWORD:?POSTGRES_APP_PASSWORD must be set}"
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'SQL'
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'sanket_cloud_app') THEN
    CREATE ROLE sanket_cloud_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
  END IF;
END
$$;
SQL
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" \
  --set=app_password="$POSTGRES_APP_PASSWORD" <<'SQL'
SELECT format('ALTER ROLE sanket_cloud_app PASSWORD %L', :'app_password') \\gexec
GRANT CONNECT ON DATABASE sanket_cloud TO sanket_cloud_app;
GRANT USAGE ON SCHEMA public TO sanket_cloud_app;
GRANT SELECT, INSERT, UPDATE ON sites, devices, stored_objects, backups TO sanket_cloud_app;
SQL
