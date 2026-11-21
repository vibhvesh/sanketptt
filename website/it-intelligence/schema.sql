-- Sanket IT Intelligence schema: private per-user inventory
create extension if not exists pgcrypto;
create table if not exists public.assets (
 id uuid primary key default gen_random_uuid(),
 name text not null check (char_length(name) between 1 and 120),
 hostname text, asset_type text not null default 'Server', platform text,
 environment text not null default 'Production',
 owner text, status text not null default 'Healthy'
   check(status in ('Healthy','Warning','Critical','Maintenance')),
 notes text, owner_id uuid references auth.users(id) default auth.uid(),
 created_at timestamptz not null default now(),
 updated_at timestamptz not null default now()
);
alter table public.assets add column if not exists owner_id uuid references auth.users(id) default auth.uid();
alter table public.assets enable row level security;
drop policy if exists "Authenticated users can read assets" on public.assets;
drop policy if exists "Authenticated users can insert assets" on public.assets;
drop policy if exists "Authenticated users can update assets" on public.assets;
drop policy if exists "Authenticated users can delete assets" on public.assets;
drop policy if exists "Users read own assets" on public.assets;
drop policy if exists "Users insert own assets" on public.assets;
drop policy if exists "Users update own assets" on public.assets;
drop policy if exists "Users delete own assets" on public.assets;
create policy "Users read own assets" on public.assets for select to authenticated using (owner_id = auth.uid());
create policy "Users insert own assets" on public.assets for insert to authenticated with check (owner_id = auth.uid());
create policy "Users update own assets" on public.assets for update to authenticated using (owner_id = auth.uid()) with check (owner_id = auth.uid());
create policy "Users delete own assets" on public.assets for delete to authenticated using (owner_id = auth.uid());
create index if not exists assets_owner_id_idx on public.assets(owner_id);
create index if not exists assets_status_idx on public.assets(status);
