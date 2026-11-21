-- Sanket IT Intelligence demo inventory
-- Run this AFTER schema.sql in Supabase SQL Editor.
-- Uses illustrative sample infrastructure only; no real hosts or credentials.
insert into public.assets
  (name, hostname, asset_type, platform, environment, owner, status, notes)
select v.name, v.hostname, v.asset_type, v.platform, v.environment, v.owner, v.status, v.notes
from (values
 ('Citrix Delivery Controller 01','ctx-ddc-01.demo','Server','Windows Server 2022 / Citrix CVAD','Production','EU​​C Infrastructure','Healthy','Demo primary delivery controller'),
 ('Citrix Delivery Controller 02','ctx-ddc-02.demo','Server','Windows Server 2022 / Citrix CVAD','Production','EU​​C Infrastructure','Healthy','Demo secondary delivery controller'),
 ('Citrix StoreFront 01','ctx-sf-01.demo','Server','Windows Server 2022 / StoreFront','Production','EU​​C Infrastructure','Healthy','Demo StoreFront node'),
 ('Citrix Virtual Apps Worker 01','ctx-vda-01.demo','Server','Windows Server 2019 / VDA','Production','EU​​C Infrastructure','Warning','Demo patch compliance review'),
 ('Citrix Virtual Apps Worker 02','ctx-vda-02.demo','Server','Windows Server 2019 / VDA','Production','EU​​C Infrastructure','Healthy','Demo session host'),
 ('NetScaler ADC Primary','nsadc-pri.demo','Network','Citrix NetScaler ADC','Production','Network Operations','Healthy','Demo load balancing appliance'),
 ('NetScaler ADC Secondary','nsadc-sec.demo','Network','Citrix NetScaler ADC','DR','Network Operations','Maintenance','Demo scheduled firmware maintenance'),
 ('VMware vCenter','vcsa-01.demo','Application','VMware vSphere 8','Production','Virtualisation','Healthy','Demo virtualisation management'),
 ('VMware ESXi Host 01','esx-01.demo','Server','VMware ESXi 8','Production','Virtualisation','Healthy','Demo hypervisor host'),
 ('VMware ESXi Host 02','esx-02.demo','Server','VMware ESXi 8','Production','Virtualisation','Warning','Demo datastore capacity warning'),
 ('Active Directory Domain Controller 01','ad-dc-01.demo','Server','Windows Server 2022 / AD DS','Production','Identity Team','Healthy','Demo domain controller'),
 ('DNS / DHCP Server','infra-dns-01.demo','Server','Windows Server 2022 / DNS DHCP','Production','Infrastructure','Healthy','Demo core network services'),
 ('Backup Repository','bkp-repo-01.demo','Storage','Linux / Backup Repository','DR','Backup Team','Critical','Demo backup job failure alert'),
 ('PostgreSQL Database','db-pg-01.demo','Application','PostgreSQL 16','Production','Database Team','Healthy','Demo application database'),
 ('Linux Monitoring Node','mon-linux-01.demo','Server','Ubuntu Server 24.04','Development','SRE','Healthy','Demo monitoring and metrics node'),
 ('Wireless Controller','wlc-01.demo','Network','Cisco Wireless LAN Controller','UAT','Network Operations','Maintenance','Demo planned maintenance'),
 ('File Services Cluster','fs-cluster-01.demo','Storage','Windows Server 2022 / SOFS','Production','Storage Team','Warning','Demo storage threshold approaching'),
 ('Public Web Frontend','web-frontend-01.demo','Application','Nginx / Linux','Production','Web Operations','Healthy','Demo public website frontend'),
 ('Endpoint Management','uem-01.demo','Application','Microsoft Intune','Production','Endpoint Team','Healthy','Demo endpoint management service'),
 ('Test API Service','api-test-01.demo','Application','FastAPI / Python','Development','Application Team','Critical','Demo failed health check')
) as v(name,hostname,asset_type,platform,environment,owner,status,notes)
where not exists (
  select 1 from public.assets a where a.hostname = v.hostname
);
