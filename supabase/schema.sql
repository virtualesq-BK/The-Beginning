-- The Beginning — Supabase 초기 스키마
-- 실행 위치: Supabase Dashboard → SQL Editor → New query → 붙여넣기 → Run
--
-- 성공 확인 (아래 쿼리 결과에 3개 테이블이 보이면 OK):
-- select table_name from information_schema.tables
-- where table_schema = 'public'
--   and table_name in ('profiles', 'contract_analyses', 'expert_requests');

-- ============================================================
-- STEP 1. profiles
-- ============================================================
create table if not exists public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  email text,
  full_name text,
  company_name text,
  phone text,
  job_title text,
  address text,
  usage_purposes text[] not null default '{}',
  other_requests text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- ============================================================
-- STEP 2. contract_analyses
-- ============================================================
create table if not exists public.contract_analyses (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  file_name text,
  file_ext text,
  file_size bigint,
  mime_type text,
  storage_path text,
  page_count integer,
  document_summary text,
  clause_count integer not null default 0,
  high_risk_count integer not null default 0,
  report jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists contract_analyses_user_id_idx
  on public.contract_analyses (user_id);

-- ============================================================
-- STEP 3. expert_requests
-- ============================================================
do $$
begin
  if not exists (select 1 from pg_type where typname = 'expert_request_type') then
    create type public.expert_request_type as enum (
      'translation_review',
      'legal_expert'
    );
  end if;

  if not exists (select 1 from pg_type where typname = 'expert_request_status') then
    create type public.expert_request_status as enum (
      'pending',
      'sent',
      'in_progress',
      'completed',
      'cancelled'
    );
  end if;
end $$;

create table if not exists public.expert_requests (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  analysis_id uuid references public.contract_analyses (id) on delete set null,
  request_type public.expert_request_type not null,
  status public.expert_request_status not null default 'pending',
  user_email text,
  note text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists expert_requests_user_id_idx
  on public.expert_requests (user_id);

-- ============================================================
-- STEP 4. updated_at 트리거
-- ============================================================
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

drop trigger if exists profiles_set_updated_at on public.profiles;
create trigger profiles_set_updated_at
before update on public.profiles
for each row execute function public.set_updated_at();

drop trigger if exists contract_analyses_set_updated_at on public.contract_analyses;
create trigger contract_analyses_set_updated_at
before update on public.contract_analyses
for each row execute function public.set_updated_at();

drop trigger if exists expert_requests_set_updated_at on public.expert_requests;
create trigger expert_requests_set_updated_at
before update on public.expert_requests
for each row execute function public.set_updated_at();

-- ============================================================
-- STEP 5. 가입 시 profiles 자동 생성 (metadata 반영)
-- ============================================================
create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  meta jsonb := coalesce(new.raw_user_meta_data, '{}'::jsonb);
  purposes text[];
begin
  purposes := coalesce(
    (
      select array_agg(value)
      from jsonb_array_elements_text(coalesce(meta->'usage_purposes', '[]'::jsonb)) as t(value)
    ),
    '{}'::text[]
  );

  insert into public.profiles (
    id,
    email,
    full_name,
    company_name,
    phone,
    job_title,
    address,
    usage_purposes,
    other_requests
  )
  values (
    new.id,
    new.email,
    nullif(meta->>'full_name', ''),
    nullif(meta->>'company_name', ''),
    nullif(meta->>'phone', ''),
    nullif(meta->>'job_title', ''),
    nullif(meta->>'address', ''),
    purposes,
    nullif(meta->>'other_requests', '')
  )
  on conflict (id) do update
    set email = excluded.email,
        full_name = coalesce(excluded.full_name, public.profiles.full_name),
        company_name = coalesce(excluded.company_name, public.profiles.company_name),
        phone = coalesce(excluded.phone, public.profiles.phone),
        job_title = coalesce(excluded.job_title, public.profiles.job_title),
        address = coalesce(excluded.address, public.profiles.address),
        usage_purposes = case
          when excluded.usage_purposes = '{}'::text[] then public.profiles.usage_purposes
          else excluded.usage_purposes
        end,
        other_requests = coalesce(excluded.other_requests, public.profiles.other_requests),
        updated_at = now();

  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row execute function public.handle_new_user();

-- 기존 가입자 백필
insert into public.profiles (id, email)
select id, email from auth.users
on conflict (id) do update
  set email = excluded.email,
      updated_at = now();

-- ============================================================
-- STEP 6. RLS
-- ============================================================
alter table public.profiles enable row level security;
alter table public.contract_analyses enable row level security;
alter table public.expert_requests enable row level security;

drop policy if exists "profiles_select_own" on public.profiles;
create policy "profiles_select_own" on public.profiles
  for select to authenticated using (auth.uid() = id);

drop policy if exists "profiles_insert_own" on public.profiles;
create policy "profiles_insert_own" on public.profiles
  for insert to authenticated
  with check (auth.uid() = id);

drop policy if exists "profiles_update_own" on public.profiles;
create policy "profiles_update_own" on public.profiles
  for update to authenticated
  using (auth.uid() = id) with check (auth.uid() = id);

drop policy if exists "contract_analyses_select_own" on public.contract_analyses;
create policy "contract_analyses_select_own" on public.contract_analyses
  for select to authenticated using (auth.uid() = user_id);

drop policy if exists "contract_analyses_insert_own" on public.contract_analyses;
create policy "contract_analyses_insert_own" on public.contract_analyses
  for insert to authenticated with check (auth.uid() = user_id);

drop policy if exists "contract_analyses_update_own" on public.contract_analyses;
create policy "contract_analyses_update_own" on public.contract_analyses
  for update to authenticated
  using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "contract_analyses_delete_own" on public.contract_analyses;
create policy "contract_analyses_delete_own" on public.contract_analyses
  for delete to authenticated using (auth.uid() = user_id);

drop policy if exists "expert_requests_select_own" on public.expert_requests;
create policy "expert_requests_select_own" on public.expert_requests
  for select to authenticated using (auth.uid() = user_id);

drop policy if exists "expert_requests_insert_own" on public.expert_requests;
create policy "expert_requests_insert_own" on public.expert_requests
  for insert to authenticated with check (auth.uid() = user_id);

drop policy if exists "expert_requests_update_own" on public.expert_requests;
create policy "expert_requests_update_own" on public.expert_requests
  for update to authenticated
  using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- ============================================================
-- STEP 7. 생성 확인
-- ============================================================
select table_name
from information_schema.tables
where table_schema = 'public'
  and table_name in ('profiles', 'contract_analyses', 'expert_requests')
order by table_name;
