-- ConstruControl destination Storage setup.
-- Run this ONLY in the Supabase project used by the new ERPNext deployment,
-- after taking a database backup. Do not run it in the legacy source project.
--
-- Security model: browser clients never receive a Supabase server key and never
-- access these buckets directly. ERPNext is the authorization boundary and uses
-- a server-only sb_secret_ key (or a temporary legacy service_role key) to bypass
-- Storage RLS. Therefore this script intentionally creates NO anon/authenticated
-- policies for the three buckets.

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values
  (
    'construction-evidence',
    'construction-evidence',
    false,
    12582912,
    array['image/jpeg', 'image/png', 'image/webp', 'application/pdf']::text[]
  ),
  (
    'construcontrol-migration',
    'construcontrol-migration',
    false,
    2147483648,
    array['application/zip', 'application/x-zip-compressed', 'application/octet-stream']::text[]
  ),
  (
    'construcontrol-backups',
    'construcontrol-backups',
    false,
    5368709120,
    array[
      'application/gzip',
      'application/x-gzip',
      'application/x-tar',
      'application/json',
      'application/octet-stream'
    ]::text[]
  )
on conflict (id) do update set
  name = excluded.name,
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

-- Remove only obsolete ConstruControl policies created by earlier project drafts.
-- No replacement client policies are created: direct browser access remains denied.
drop policy if exists "ConstruControl evidence public read" on storage.objects;
drop policy if exists "ConstruControl evidence authenticated read" on storage.objects;
drop policy if exists "ConstruControl evidence upload" on storage.objects;
drop policy if exists "ConstruControl evidence update" on storage.objects;
drop policy if exists "ConstruControl evidence delete" on storage.objects;
drop policy if exists "ConstruControl migration access" on storage.objects;
drop policy if exists "ConstruControl backup access" on storage.objects;

-- Fail immediately if any managed bucket is public.
do $$
begin
  if exists (
    select 1
    from storage.buckets
    where id in ('construction-evidence', 'construcontrol-migration', 'construcontrol-backups')
      and public is true
  ) then
    raise exception 'One or more ConstruControl buckets are public; aborting.';
  end if;
end
$$;

-- Expected result: three rows, all with public = false.
select id, name, public, file_size_limit, allowed_mime_types
from storage.buckets
where id in ('construction-evidence', 'construcontrol-migration', 'construcontrol-backups')
order by id;

-- Expected result for a clean destination project: zero policies whose SQL
-- expression references a ConstruControl bucket. Any returned row must be
-- reviewed before production.
select policyname, roles, cmd, qual, with_check
from pg_policies
where schemaname = 'storage'
  and tablename = 'objects'
  and coalesce(qual, '') || coalesce(with_check, '') ~
      '(construction-evidence|construcontrol-migration|construcontrol-backups)'
order by policyname;
