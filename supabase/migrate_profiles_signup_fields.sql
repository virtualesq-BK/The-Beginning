-- The Beginning — profiles 회원 가입 필드 확장
-- Supabase SQL Editor에 붙여넣고 Run
-- 이미 schema.sql을 실행한 경우에도 안전하게 재실행 가능

alter table public.profiles
  add column if not exists phone text,
  add column if not exists job_title text,
  add column if not exists address text,
  add column if not exists usage_purposes text[] not null default '{}',
  add column if not exists other_requests text;

comment on column public.profiles.phone is '전화번호';
comment on column public.profiles.job_title is '직책/직위';
comment on column public.profiles.address is '주소';
comment on column public.profiles.usage_purposes is '사용목적 (다수 선택)';
comment on column public.profiles.other_requests is '기타 요청 사항';

-- 가입 시 auth.users.raw_user_meta_data → profiles 반영
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

-- 본인 프로필 insert 허용 (세션이 바로 생긴 경우 upsert용)
drop policy if exists "profiles_insert_own" on public.profiles;
create policy "profiles_insert_own" on public.profiles
  for insert to authenticated
  with check (auth.uid() = id);

-- 확인
select column_name, data_type
from information_schema.columns
where table_schema = 'public'
  and table_name = 'profiles'
order by ordinal_position;
