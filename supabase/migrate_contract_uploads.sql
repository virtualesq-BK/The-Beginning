-- 계약서 업로드 파일 Storage + contract_analyses 컬럼 확장
-- Supabase SQL Editor에서 실행

-- 1) DB 컬럼
alter table public.contract_analyses
  add column if not exists storage_path text,
  add column if not exists file_size bigint,
  add column if not exists mime_type text;

comment on column public.contract_analyses.storage_path is 'Supabase Storage 경로 (contract-uploads 버킷)';
comment on column public.contract_analyses.file_size is '업로드 파일 바이트 크기';
comment on column public.contract_analyses.mime_type is '업로드 파일 MIME 타입';

-- 2) Storage 버킷 (비공개)
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'contract-uploads',
  'contract-uploads',
  false,
  20971520, -- 20MB
  array[
    'text/plain',
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/octet-stream'
  ]
)
on conflict (id) do update
  set public = excluded.public,
      file_size_limit = excluded.file_size_limit,
      allowed_mime_types = excluded.allowed_mime_types;

-- 3) Storage RLS: 본인 폴더({user_id}/...)만 접근
drop policy if exists "contract_uploads_select_own" on storage.objects;
create policy "contract_uploads_select_own"
on storage.objects
for select
to authenticated
using (
  bucket_id = 'contract-uploads'
  and (storage.foldername(name))[1] = auth.uid()::text
);

drop policy if exists "contract_uploads_insert_own" on storage.objects;
create policy "contract_uploads_insert_own"
on storage.objects
for insert
to authenticated
with check (
  bucket_id = 'contract-uploads'
  and (storage.foldername(name))[1] = auth.uid()::text
);

drop policy if exists "contract_uploads_update_own" on storage.objects;
create policy "contract_uploads_update_own"
on storage.objects
for update
to authenticated
using (
  bucket_id = 'contract-uploads'
  and (storage.foldername(name))[1] = auth.uid()::text
)
with check (
  bucket_id = 'contract-uploads'
  and (storage.foldername(name))[1] = auth.uid()::text
);

drop policy if exists "contract_uploads_delete_own" on storage.objects;
create policy "contract_uploads_delete_own"
on storage.objects
for delete
to authenticated
using (
  bucket_id = 'contract-uploads'
  and (storage.foldername(name))[1] = auth.uid()::text
);

-- 확인
select id, name, public, file_size_limit
from storage.buckets
where id = 'contract-uploads';

select column_name
from information_schema.columns
where table_schema = 'public'
  and table_name = 'contract_analyses'
  and column_name in ('storage_path', 'file_size', 'mime_type');
