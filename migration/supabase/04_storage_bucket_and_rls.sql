-- Apply only after taking a Supabase database backup and exporting Storage.
-- This keeps the legacy bucket private.  ERPNext uses a server-only service-role
-- credential, while the existing ConstruControl policies continue to govern
-- direct authenticated access to project-prefixed legacy objects.

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'construction-evidence',
  'construction-evidence',
  false,
  12582912,
  array['image/jpeg', 'image/png', 'image/webp', 'application/pdf']
)
on conflict (id) do update set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

-- Remove obsolete policies that ever allowed anonymous/public reads.
drop policy if exists "ConstruControl evidence public read" on storage.objects;
drop policy if exists "ConstruControl evidence authenticated read" on storage.objects;
drop policy if exists "ConstruControl evidence upload" on storage.objects;
drop policy if exists "ConstruControl evidence update" on storage.objects;

-- Frappe-managed objects live below frappe/<site>/... and are intentionally not
-- granted to anon/authenticated.  service_role bypasses RLS on the server.
-- Verify the absence of a permissive policy with 01_preflight.sql.

select id, name, public, file_size_limit, allowed_mime_types
from storage.buckets
where id = 'construction-evidence';
