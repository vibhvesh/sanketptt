-- Sanket IT Intelligence: generate 1,000 realistic synthetic infrastructure assets.
-- Run in Supabase SQL Editor after schema.sql and the public-test RLS policies.
-- Safe to re-run: hostnames are deterministic and duplicates are skipped.
-- All records are fictional demo data; no real devices are discovered.

with generated as (
  select
    n,
    (array['Server','Network','Storage','Application','Endpoint','Cloud service','Other'])[((n-1)%7)+1] as asset_type,
    (array['Production','UAT','Development','DR','Lab'])[((n-1)%5)+1] as environment,
    (array['Healthy','Healthy','Healthy','Warning','Critical','Maintenance'])[((n-1)%6)+1] as status,
    (array['EU​​C Infrastructure','Virtualisation','Network Operations','Database Team','Storage Team','SRE','Security Operations','Endpoint Team','Application Support','Cloud Platform'])[((n-1)%10)+1] as owner,
    (array[
      'Windows Server 2022','Windows Server 2019','Ubuntu Server 24.04','Red Hat Enterprise Linux 9',
      'VMware ESXi 8','Citrix NetScaler ADC','PostgreSQL 16','Microsoft SQL Server 2022',
      'Nginx / Linux','Cisco IOS-XE','Microsoft Active Directory','Kubernetes','VMware vCenter 8',
      'Microsoft Intune','Redis 7','Rocky Linux 9','Proxmox VE','Pure Storage','Veeam Backup',
      'Microsoft Exchange Server'
    ])[((n-1)%20)+1] as platform
  from generate_series(1,1000) as s(n)
),
rows_to_insert as (
  select
    case asset_type
      when 'Server' then (array['Compute Node','Domain Controller','Citrix Delivery Controller','Session Host','Web Server','Monitoring Node','File Server','Application Server'])[((n-1)%8)+1]
      when 'Network' then (array['Core Switch','Edge Router','Load Balancer','Firewall','Wireless Controller','VPN Gateway'])[((n-1)%6)+1]
      when 'Storage' then (array['Backup Repository','SAN Array','NAS Cluster','Object Storage Node','Storage Gateway'])[((n-1)%5)+1]
      when 'Application' then (array['API Service','Database Service','Web Portal','Message Broker','Identity Service','Monitoring Platform'])[((n-1)%6)+1]
      when 'Endpoint' then (array['Managed Workstation','VDI Endpoint','Kiosk Terminal','Engineering Workstation'])[((n-1)%4)+1]
      when 'Cloud service' then (array['Cloud VM','Object Bucket','Managed Database','Container Cluster'])[((n-1)%4)+1]
      else (array['Test Appliance','Lab Device','Utility Service'])[((n-1)%3)+1]
    end || ' ' || lpad(n::text,4,'0') as name,
    'sanket-demo-' || lpad(n::text,4,'0') || '.demo' as hostname,
    asset_type,
    platform,
    environment,
    owner,
    status,
    'Synthetic test record #' || n || '. Generated for Sanket IT Intelligence dashboard testing; not a real discovered asset.' as notes
  from generated
)
insert into public.assets (name,hostname,asset_type,platform,environment,owner,status,notes)
select name,hostname,asset_type,platform,environment,owner,status,notes
from rows_to_insert
where not exists (
  select 1 from public.assets existing where existing.hostname=rows_to_insert.hostname
);

-- Verify count of generated demo assets:
select count(*) as generated_demo_assets
from public.assets
where hostname like 'sanket-demo-%.demo';
