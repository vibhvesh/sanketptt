-- Sanket Central Cloud initial schema (PostgreSQL 16+)
-- Apply with a migration owner. The runtime DB role must NOT own these tables
-- and must NOT have BYPASSRLS.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS sites (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    name text NOT NULL,
    external_ref text,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, id)
);

CREATE TABLE IF NOT EXISTS devices (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    site_id uuid NOT NULL,
    name text NOT NULL,
    device_type text NOT NULL DEFAULT 'raspberry_pi',
    software_version text,
    last_seen_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, id),
    FOREIGN KEY (tenant_id, site_id) REFERENCES sites(tenant_id, id)
);

CREATE TABLE IF NOT EXISTS stored_objects (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL,
    site_id uuid NOT NULL,
    device_id uuid NOT NULL,
    category text NOT NULL CHECK (category IN
      ('recordings','transcripts','backups','images','diagnostics','screenshots','exports','releases')),
    object_key text NOT NULL UNIQUE,
    file_name text NOT NULL,
    content_type text NOT NULL,
    size_bytes bigint NOT NULL CHECK (size_bytes >= 0),
    sha256 char(64) NOT NULL,
    uploaded_by text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (tenant_id, site_id) REFERENCES sites(tenant_id, id),
    FOREIGN KEY (tenant_id, device_id) REFERENCES devices(tenant_id, id)
);

CREATE TABLE IF NOT EXISTS backups (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id uuid NOT NULL,
    site_id uuid NOT NULL,
    source_device_id uuid NOT NULL,
    object_id uuid NOT NULL UNIQUE,
    backup_type text NOT NULL CHECK (backup_type IN
      ('config_clone','full_migration','disaster_recovery','scheduled')),
    manifest jsonb NOT NULL,
    sha256 char(64) NOT NULL,
    size_bytes bigint NOT NULL CHECK (size_bytes >= 0),
    created_at timestamptz NOT NULL DEFAULT now(),
    FOREIGN KEY (tenant_id, site_id) REFERENCES sites(tenant_id, id),
    FOREIGN KEY (tenant_id, source_device_id) REFERENCES devices(tenant_id, id),
    FOREIGN KEY (object_id) REFERENCES stored_objects(id)
);

CREATE INDEX IF NOT EXISTS idx_objects_tenant_created ON stored_objects(tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_objects_tenant_site_category ON stored_objects(tenant_id, site_id, category);
CREATE INDEX IF NOT EXISTS idx_backups_tenant_created ON backups(tenant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_devices_tenant_site ON devices(tenant_id, site_id);

ALTER TABLE sites ENABLE ROW LEVEL SECURITY;
ALTER TABLE sites FORCE ROW LEVEL SECURITY;
ALTER TABLE devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE devices FORCE ROW LEVEL SECURITY;
ALTER TABLE stored_objects ENABLE ROW LEVEL SECURITY;
ALTER TABLE stored_objects FORCE ROW LEVEL SECURITY;
ALTER TABLE backups ENABLE ROW LEVEL SECURITY;
ALTER TABLE backups FORCE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS tenant_isolation_sites ON sites;
CREATE POLICY tenant_isolation_sites ON sites
  USING (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid)
  WITH CHECK (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid);

DROP POLICY IF EXISTS tenant_isolation_devices ON devices;
CREATE POLICY tenant_isolation_devices ON devices
  USING (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid)
  WITH CHECK (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid);

DROP POLICY IF EXISTS tenant_isolation_objects ON stored_objects;
CREATE POLICY tenant_isolation_objects ON stored_objects
  USING (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid)
  WITH CHECK (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid);

DROP POLICY IF EXISTS tenant_isolation_backups ON backups;
CREATE POLICY tenant_isolation_backups ON backups
  USING (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid)
  WITH CHECK (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid);

-- Create a separate runtime role; set its password out-of-band.
-- CREATE ROLE sanket_cloud_app LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
-- GRANT CONNECT ON DATABASE sanket_cloud TO sanket_cloud_app;
-- GRANT USAGE ON SCHEMA public TO sanket_cloud_app;
-- GRANT SELECT, INSERT, UPDATE ON sites, devices, stored_objects, backups TO sanket_cloud_app;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO sanket_cloud_app;
-- Do not grant BYPASSRLS or table ownership to sanket_cloud_app.
