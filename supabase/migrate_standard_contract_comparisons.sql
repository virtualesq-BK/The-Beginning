-- The Beginning — 표준계약서(대리점·OEM/ODM·라이선스) 비교 결과 저장
-- Supabase SQL Editor에서 실행 (schema.sql 다음에 실행)
--
-- fidic_comparisons와 동일한 구조를 대리점/OEM·ODM/라이선스 비교
-- (agents/standard_contract_comparison.py, /api/v1/standard-contracts/compare*)에
-- 맞게 재구성한다. bias_scores(발주자/시공사 편향)는 FIDIC 전용 개념이라 제외하고,
-- 대신 어떤 계약유형을 비교했는지 식별하는 contract_type 컬럼을 둔다.
--
-- 성공 확인:
-- select table_name from information_schema.tables
-- where table_schema = 'public' and table_name = 'standard_contract_comparisons';

-- ============================================================
-- STEP 1. standard_contract_comparisons
-- ============================================================
create table if not exists public.standard_contract_comparisons (
  comparison_id text primary key,
  user_id uuid references auth.users (id) on delete set null,
  contract_type text not null check (contract_type in ('distributor', 'oem_odm', 'license')),
  contract_text text,
  overall_score integer not null default 0,
  balance text not null default '균형형',
  summary text,
  focus_areas text[] not null default '{}',
  issues jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists standard_contract_comparisons_user_id_idx
  on public.standard_contract_comparisons (user_id);

create index if not exists standard_contract_comparisons_contract_type_idx
  on public.standard_contract_comparisons (contract_type);

create index if not exists standard_contract_comparisons_created_at_idx
  on public.standard_contract_comparisons (created_at desc);

-- ============================================================
-- STEP 2. updated_at 자동 갱신 트리거
-- schema.sql의 public.set_updated_at() 함수를 재사용한다 (schema.sql이
-- 먼저 실행되어 있어야 함).
-- ============================================================
drop trigger if exists standard_contract_comparisons_set_updated_at on public.standard_contract_comparisons;
create trigger standard_contract_comparisons_set_updated_at
before update on public.standard_contract_comparisons
for each row execute function public.set_updated_at();

-- ============================================================
-- STEP 3. RLS
-- fidic_comparisons와 동일하게, user_id가 없는(비로그인 저장) 레코드는
-- 누구나 조회 가능하게 열어둔다. 실제로는 서버가 로그인 사용자만 저장을
-- 시도하므로 user_id가 null인 레코드는 거의 없다.
-- ============================================================
alter table public.standard_contract_comparisons enable row level security;

drop policy if exists "standard_contract_comparisons_select_own" on public.standard_contract_comparisons;
create policy "standard_contract_comparisons_select_own" on public.standard_contract_comparisons
  for select to authenticated using (auth.uid() = user_id or user_id is null);

drop policy if exists "standard_contract_comparisons_insert_own" on public.standard_contract_comparisons;
create policy "standard_contract_comparisons_insert_own" on public.standard_contract_comparisons
  for insert to authenticated with check (auth.uid() = user_id or user_id is null);

drop policy if exists "standard_contract_comparisons_update_own" on public.standard_contract_comparisons;
create policy "standard_contract_comparisons_update_own" on public.standard_contract_comparisons
  for update to authenticated
  using (auth.uid() = user_id or user_id is null)
  with check (auth.uid() = user_id or user_id is null);

drop policy if exists "standard_contract_comparisons_delete_own" on public.standard_contract_comparisons;
create policy "standard_contract_comparisons_delete_own" on public.standard_contract_comparisons
  for delete to authenticated using (auth.uid() = user_id or user_id is null);

-- ============================================================
-- STEP 4. 생성 확인
-- ============================================================
select table_name
from information_schema.tables
where table_schema = 'public'
  and table_name = 'standard_contract_comparisons';
