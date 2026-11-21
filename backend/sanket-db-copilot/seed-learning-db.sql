-- Sanket AI Database Copilot learning schema.
-- Run once against the disposable Prisma PostgreSQL database.
CREATE TABLE IF NOT EXISTS it_assets (
  asset_id BIGSERIAL PRIMARY KEY,
  asset_name TEXT NOT NULL,
  hostname TEXT UNIQUE NOT NULL,
  asset_type TEXT NOT NULL,
  vendor TEXT NOT NULL,
  model TEXT NOT NULL,
  operating_system TEXT,
  os_version TEXT,
  environment TEXT NOT NULL,
  region TEXT NOT NULL,
  owner_team TEXT NOT NULL,
  status TEXT NOT NULL,
  cpu_cores INTEGER,
  memory_gb INTEGER,
  storage_gb INTEGER,
  purchase_date DATE,
  warranty_end DATE,
  last_seen TIMESTAMPTZ NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS it_incidents (
  incident_id BIGSERIAL PRIMARY KEY,
  asset_id BIGINT REFERENCES it_assets(asset_id),
  incident_type TEXT NOT NULL,
  severity TEXT NOT NULL,
  incident_status TEXT NOT NULL,
  opened_at TIMESTAMPTZ NOT NULL,
  resolved_at TIMESTAMPTZ,
  assigned_team TEXT NOT NULL,
  downtime_minutes INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS it_changes (
  change_id BIGSERIAL PRIMARY KEY,
  asset_id BIGINT REFERENCES it_assets(asset_id),
  change_type TEXT NOT NULL,
  change_status TEXT NOT NULL,
  risk_level TEXT NOT NULL,
  requested_by TEXT NOT NULL,
  scheduled_at TIMESTAMPTZ NOT NULL,
  completed_at TIMESTAMPTZ
);
CREATE TABLE IF NOT EXISTS it_vulnerabilities (
  vulnerability_id BIGSERIAL PRIMARY KEY,
  asset_id BIGINT REFERENCES it_assets(asset_id),
  cve_id TEXT NOT NULL,
  title TEXT NOT NULL,
  severity TEXT NOT NULL,
  cvss_score NUMERIC(3,1),
  exploited_in_wild BOOLEAN NOT NULL DEFAULT false,
  detected_at TIMESTAMPTZ NOT NULL,
  remediation_status TEXT NOT NULL,
  due_date DATE
);
INSERT INTO it_assets(asset_name,hostname,asset_type,vendor,model,operating_system,os_version,environment,region,owner_team,status,cpu_cores,memory_gb,storage_gb,purchase_date,warranty_end,last_seen)
SELECT
  initcap(replace(vendor,'-',' '))||' '||typ||' '||lpad(i::text,4,'0'),
  'lab-'||lpad(i::text,4,'0')||'.sanket-demo.local',
  typ,vendor,model,os,ver,env,region,team,status,cpu,mem,storage,
  current_date - ((i*17)%1500), current_date + ((i*13)%900)-300,
  now() - ((i%72)||' hours')::interval
FROM generate_series(1,1000) i
CROSS JOIN LATERAL (
 SELECT (ARRAY['Server','Router','Firewall','Switch','Storage','Endpoint','Virtual Machine'])[1+((i-1)%7)] AS typ,
        (ARRAY['dell','hpe','cisco','juniper','fortinet','vmware','lenovo'])[1+((i*3)%7)] AS vendor,
        (ARRAY['PowerEdge R750','ProLiant DL380','Catalyst 9300','SRX 340','FortiGate 200F','vSphere VM','ThinkSystem SR650'])[1+((i*5)%7)] AS model,
        (ARRAY['Windows Server','Ubuntu','Red Hat Enterprise Linux','VMware ESXi','FortiOS','Cisco IOS XE'])[1+((i*7)%6)] AS os,
        (ARRAY['2019','2022','22.04','9.4','8.0','7.0 U3'])[1+((i*11)%6)] AS ver,
        (ARRAY['Production','UAT','Development','DR','Lab'])[1+((i*13)%5)] AS env,
        (ARRAY['India-West','India-South','Singapore','Europe','US-East'])[1+((i*17)%5)] AS region,
        (ARRAY['Infrastructure','Network Operations','Security','Cloud Platform','End User Computing'])[1+((i*19)%5)] AS team,
        (ARRAY['Healthy','Healthy','Healthy','Warning','Critical','Maintenance'])[1+((i*23)%6)] AS status,
        (ARRAY[4,8,16,24,32,48,64])[1+((i*29)%7)] AS cpu,
        (ARRAY[8,16,32,64,128,256])[1+((i*31)%6)] AS mem,
        (ARRAY[256,512,1024,2048,4096,8192])[1+((i*37)%6)] AS storage
) v
ON CONFLICT(hostname) DO NOTHING;
INSERT INTO it_incidents(asset_id,incident_type,severity,incident_status,opened_at,resolved_at,assigned_team,downtime_minutes)
SELECT asset_id,(ARRAY['CPU saturation','Disk capacity','Network latency','Service unavailable','Authentication failure','Memory pressure'])[1+((asset_id*3)%6)],
 (ARRAY['Low','Medium','High','Critical'])[1+((asset_id*7)%4)],
 (ARRAY['Open','In Progress','Resolved','Closed'])[1+((asset_id*11)%4)],
 now()-((asset_id%60)||' days')::interval,
 CASE WHEN asset_id%4 IN (2,3) THEN now()-((asset_id%30)||' days')::interval ELSE NULL END,
 owner_team,(asset_id*13)%600
FROM it_assets WHERE asset_id%4=0
ON CONFLICT DO NOTHING;
INSERT INTO it_changes(asset_id,change_type,change_status,risk_level,requested_by,scheduled_at,completed_at)
SELECT asset_id,(ARRAY['Patch deployment','Firmware upgrade','Capacity expansion','Configuration update','Certificate renewal'])[1+((asset_id*5)%5)],
 (ARRAY['Requested','Approved','In Progress','Completed','Rejected'])[1+((asset_id*7)%5)],
 (ARRAY['Low','Medium','High'])[1+((asset_id*11)%3)],
 owner_team,now()+((asset_id%20)||' days')::interval,
 CASE WHEN asset_id%5=3 THEN now()-((asset_id%15)||' days')::interval ELSE NULL END
FROM it_assets WHERE asset_id%5=0
ON CONFLICT DO NOTHING;
INSERT INTO it_vulnerabilities(asset_id,cve_id,title,severity,cvss_score,exploited_in_wild,detected_at,remediation_status,due_date)
SELECT asset_id,'CVE-'||(2021+(asset_id%5))||'-'||lpad((1000+asset_id)::text,5,'0'),
 (ARRAY['Remote code execution','Privilege escalation','Authentication bypass','Information disclosure','Denial of service'])[1+((asset_id*3)%5)],
 (ARRAY['Low','Medium','High','Critical'])[1+((asset_id*7)%4)],
 (ARRAY[3.1,5.4,7.5,8.8,9.8])[1+((asset_id*11)%5)],
 asset_id%9=0,now()-((asset_id%45)||' days')::interval,
 (ARRAY['Open','In Progress','Patched','Accepted Risk'])[1+((asset_id*13)%4)],
 current_date+((asset_id%60)-20)
FROM it_assets WHERE asset_id%3=0
ON CONFLICT DO NOTHING;
CREATE INDEX IF NOT EXISTS idx_assets_type_status ON it_assets(asset_type,status);
CREATE INDEX IF NOT EXISTS idx_incidents_asset ON it_incidents(asset_id);
CREATE INDEX IF NOT EXISTS idx_changes_asset ON it_changes(asset_id);
CREATE INDEX IF NOT EXISTS idx_vulns_asset ON it_vulnerabilities(asset_id);
