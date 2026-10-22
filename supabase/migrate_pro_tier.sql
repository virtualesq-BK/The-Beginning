-- Pro 플랜 지원: profiles 테이블에 is_pro 컬럼 추가
-- Supabase Dashboard → SQL Editor → 실행

alter table public.profiles
  add column if not exists is_pro boolean not null default false,
  add column if not exists pro_since timestamptz;

comment on column public.profiles.is_pro   is 'Pro 플랜 활성화 여부 (관리자가 직접 설정)';
comment on column public.profiles.pro_since is 'Pro 플랜 활성화 일시';
