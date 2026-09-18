-- The Beginning — 계약 Lifecycle 데이터 + Benchmark/전문가 Feedback Loop
-- Supabase SQL Editor에서 실행 (schema.sql, migrate_contract_uploads.sql 다음에 실행)
--
-- 이 마이그레이션이 다루는 것:
--   1) 계약 Lifecycle: Draft -> Negotiation -> Revised Draft -> Final Contract
--      -> Execution -> Claim -> Dispute -> Outcome 전체를 저장하는 테이블
--   2) 협상 이력(negotiation_events): AI 위험탐지 -> 협상포인트 -> 상대방 반응
--   3) expert_feedback: 변호사가 AI 판단을 수정한 이력 (Rule 개선의 원재료)
--   4) benchmark_cases: expert_feedback에서 승격된 Ground Truth 평가 데이터셋
--
-- 성공 확인:
-- select table_name from information_schema.tables
-- where table_schema = 'public'
--   and table_name in ('contracts', 'contract_versions', 'negotiation_events',
--                       'expert_feedback', 'benchmark_cases');

-- ============================================================
-- STEP 1. contracts — 하나의 "딜(deal)"을 대표하는 상위 엔티티.
-- contract_analyses는 지금까지 "업로드 1건 = 분석 1건"이었지만, 같은 딜의
-- 여러 버전(초안 v1, v2, 최종본...)을 하나로 묶으려면 상위 그룹이 필요하다.
-- ============================================================
create table if not exists public.contracts (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  title text,
  counterparty_name text,
  contract_type text, -- 예: 'FIDIC-Red', 'FIDIC-Yellow', 'FIDIC-Silver', 'EPC', 'Supply'
  status text not null default 'draft', -- draft | negotiation | executed | disputed | closed
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists contracts_user_id_idx on public.contracts (user_id);

-- ============================================================
-- STEP 2. contract_versions — Draft -> Revised Draft -> Final Contract의
-- 각 시점을 저장한다. 기존 contract_analyses 레코드를 특정 버전에 연결해
-- "이 버전에서 AI가 무엇을 탐지했는가"를 그대로 재사용한다.
-- ============================================================
create table if not exists public.contract_versions (
  id uuid primary key default gen_random_uuid(),
  contract_id uuid not null references public.contracts (id) on delete cascade,
  analysis_id uuid references public.contract_analyses (id) on delete set null,
  version_number integer not null,
  stage text not null default 'draft',
  -- draft | negotiation | revised_draft | final | executed
  source text not null default 'contractor', -- 'contractor' | 'counterparty' | 'lawyer'
  notes text,
  created_at timestamptz not null default now(),
  unique (contract_id, version_number)
);

create index if not exists contract_versions_contract_id_idx
  on public.contract_versions (contract_id);

-- ============================================================
-- STEP 3. negotiation_events — AI Risk Detection -> Negotiation Point ->
-- Counterparty Response 흐름을 조항 단위로 기록한다. 이 테이블이 쌓이면
-- "유사 계약 N건 중 M%가 협상에서 수정되었다" 통계의 원천 데이터가 된다.
-- ============================================================
create table if not exists public.negotiation_events (
  id uuid primary key default gen_random_uuid(),
  contract_id uuid not null references public.contracts (id) on delete cascade,
  from_version_id uuid references public.contract_versions (id) on delete set null,
  to_version_id uuid references public.contract_versions (id) on delete set null,
  rule_id text, -- risk_ontology.py의 RiskNode.node_id (예: 'FIDIC-DELAY-LD')
  clause_type text,
  ai_negotiation_point text, -- AI가 제시한 협상 포인트
  requested_change text, -- 실제로 요청한 변경사항
  counterparty_response text, -- 'accepted' | 'rejected' | 'countered' | 'pending'
  final_resolution text, -- 최종적으로 합의된 문구/조건
  created_at timestamptz not null default now()
);

create index if not exists negotiation_events_contract_id_idx
  on public.negotiation_events (contract_id);

create index if not exists negotiation_events_rule_id_idx
  on public.negotiation_events (rule_id);

-- ============================================================
-- STEP 4. expert_feedback — "AI 판단 -> 변호사 수정 -> 수정 이유" 루프.
-- risk_analyzer.analyze_clause()가 반환한 risk_score/rules_applied를
-- 변호사가 수정할 때마다 기록한다. 결과만 저장하지 않고 "왜 바뀌었는지"를
-- 구조화하는 것이 Domain-specific Evaluation Dataset의 핵심이다.
-- ============================================================
create table if not exists public.expert_feedback (
  id uuid primary key default gen_random_uuid(),
  analysis_id uuid references public.contract_analyses (id) on delete set null,
  reviewer_user_id uuid references auth.users (id) on delete set null,
  clause_type text not null,
  clause_text text not null,
  ai_risk_score integer not null,
  ai_rules_applied text[] not null default '{}',
  human_risk_score integer not null,
  human_rules_applied text[] not null default '{}',
  correction_reason text not null, -- "왜 다른가" - 필수값. 결과만 남기지 않는다.
  disagreement_type text, -- 'score_only' | 'rule_missing' | 'rule_wrong' | 'evidence_wrong'
  promoted_to_benchmark boolean not null default false,
  created_at timestamptz not null default now()
);

create index if not exists expert_feedback_analysis_id_idx
  on public.expert_feedback (analysis_id);

create index if not exists expert_feedback_promoted_idx
  on public.expert_feedback (promoted_to_benchmark);

-- ============================================================
-- STEP 5. benchmark_cases — Contract Intelligence Benchmark.
-- expert_feedback 중 검증된 항목을 Ground Truth로 승격한 데이터셋.
-- agents/benchmark.py의 evaluate_predictions()가 이 테이블(또는 이와
-- 동일한 스키마의 로컬 JSON export)을 ground truth로 사용한다.
-- ============================================================
create table if not exists public.benchmark_cases (
  id uuid primary key default gen_random_uuid(),
  source_feedback_id uuid references public.expert_feedback (id) on delete set null,
  clause_type text not null,
  clause_text text not null,
  expected_risk_score integer not null,
  expected_rules_applied text[] not null default '{}',
  expected_evidence_quote text,
  expected_negotiation_point text,
  reviewed_by uuid references auth.users (id) on delete set null,
  created_at timestamptz not null default now()
);

create index if not exists benchmark_cases_clause_type_idx
  on public.benchmark_cases (clause_type);

-- ============================================================
-- STEP 6. updated_at 트리거 (기존 set_updated_at() 함수 재사용)
-- ============================================================
drop trigger if exists contracts_set_updated_at on public.contracts;
create trigger contracts_set_updated_at
before update on public.contracts
for each row execute function public.set_updated_at();

-- ============================================================
-- STEP 7. RLS
-- ============================================================
alter table public.contracts enable row level security;
alter table public.contract_versions enable row level security;
alter table public.negotiation_events enable row level security;
alter table public.expert_feedback enable row level security;
alter table public.benchmark_cases enable row level security;

drop policy if exists "contracts_select_own" on public.contracts;
create policy "contracts_select_own" on public.contracts
  for select to authenticated using (auth.uid() = user_id);

drop policy if exists "contracts_insert_own" on public.contracts;
create policy "contracts_insert_own" on public.contracts
  for insert to authenticated with check (auth.uid() = user_id);

drop policy if exists "contracts_update_own" on public.contracts;
create policy "contracts_update_own" on public.contracts
  for update to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists "contracts_delete_own" on public.contracts;
create policy "contracts_delete_own" on public.contracts
  for delete to authenticated using (auth.uid() = user_id);

-- contract_versions/negotiation_events: 부모 contracts를 통해 소유권 확인
drop policy if exists "contract_versions_select_own" on public.contract_versions;
create policy "contract_versions_select_own" on public.contract_versions
  for select to authenticated using (
    exists (select 1 from public.contracts c where c.id = contract_id and c.user_id = auth.uid())
  );

drop policy if exists "contract_versions_insert_own" on public.contract_versions;
create policy "contract_versions_insert_own" on public.contract_versions
  for insert to authenticated with check (
    exists (select 1 from public.contracts c where c.id = contract_id and c.user_id = auth.uid())
  );

drop policy if exists "contract_versions_update_own" on public.contract_versions;
create policy "contract_versions_update_own" on public.contract_versions
  for update to authenticated using (
    exists (select 1 from public.contracts c where c.id = contract_id and c.user_id = auth.uid())
  );

drop policy if exists "contract_versions_delete_own" on public.contract_versions;
create policy "contract_versions_delete_own" on public.contract_versions
  for delete to authenticated using (
    exists (select 1 from public.contracts c where c.id = contract_id and c.user_id = auth.uid())
  );

drop policy if exists "negotiation_events_select_own" on public.negotiation_events;
create policy "negotiation_events_select_own" on public.negotiation_events
  for select to authenticated using (
    exists (select 1 from public.contracts c where c.id = contract_id and c.user_id = auth.uid())
  );

drop policy if exists "negotiation_events_insert_own" on public.negotiation_events;
create policy "negotiation_events_insert_own" on public.negotiation_events
  for insert to authenticated with check (
    exists (select 1 from public.contracts c where c.id = contract_id and c.user_id = auth.uid())
  );

drop policy if exists "negotiation_events_update_own" on public.negotiation_events;
create policy "negotiation_events_update_own" on public.negotiation_events
  for update to authenticated using (
    exists (select 1 from public.contracts c where c.id = contract_id and c.user_id = auth.uid())
  );

-- expert_feedback / benchmark_cases: 전문가(내부 검토자)만 쓰기 가능하도록
-- 별도 역할이 정해지기 전까지는 본인이 남긴 피드백만 조회 가능하게 제한.
-- 정식 운영 시에는 별도 'reviewer' role 기반 정책으로 교체 예정.
drop policy if exists "expert_feedback_select_own" on public.expert_feedback;
create policy "expert_feedback_select_own" on public.expert_feedback
  for select to authenticated using (auth.uid() = reviewer_user_id);

drop policy if exists "expert_feedback_insert_own" on public.expert_feedback;
create policy "expert_feedback_insert_own" on public.expert_feedback
  for insert to authenticated with check (auth.uid() = reviewer_user_id);

drop policy if exists "benchmark_cases_select_reviewer" on public.benchmark_cases;
create policy "benchmark_cases_select_reviewer" on public.benchmark_cases
  for select to authenticated using (auth.uid() = reviewed_by);

drop policy if exists "benchmark_cases_insert_reviewer" on public.benchmark_cases;
create policy "benchmark_cases_insert_reviewer" on public.benchmark_cases
  for insert to authenticated with check (auth.uid() = reviewed_by);

-- ============================================================
-- STEP 8. 생성 확인
-- ============================================================
select table_name
from information_schema.tables
where table_schema = 'public'
  and table_name in ('contracts', 'contract_versions', 'negotiation_events',
                      'expert_feedback', 'benchmark_cases')
order by table_name;
