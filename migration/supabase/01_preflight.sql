-- Read-only preflight for the ConstruControl source Supabase project.
-- Run in Supabase SQL Editor before exporting. This script changes no data.

select 'construction_projects' as entity, count(*)::bigint as records from public.construction_projects
union all select 'app_user_profiles', count(*) from public.app_user_profiles
union all select 'construction_project_versions', count(*) from public.construction_project_versions
union all select 'construction_audit_events', count(*) from public.construction_audit_events
union all select 'construction_device_sessions', count(*) from public.construction_device_sessions
union all select 'construction_business_partners', count(*) from public.construction_business_partners
union all select 'construction_catalog_items', count(*) from public.construction_catalog_items
union all select 'construction_payables', count(*) from public.construction_payables
union all select 'construction_document_templates', count(*) from public.construction_document_templates
union all select 'construction_automation_rules', count(*) from public.construction_automation_rules
union all select 'construction_automation_jobs', count(*) from public.construction_automation_jobs
order by entity;

select p.project_id, p.updated_at, octet_length(p.data::text) as snapshot_bytes,
       coalesce(jsonb_array_length(p.data->'phases'), 0) as phases,
       coalesce(jsonb_array_length(p.data->'incomes'), 0) as incomes,
       coalesce(jsonb_array_length(p.data->'expenses'), 0) as expenses,
       coalesce(jsonb_array_length(p.data->'laborContracts'), 0) as labor_contracts,
       coalesce(jsonb_array_length(p.data->'materials'), 0) as materials,
       coalesce(jsonb_array_length(p.data->'inventoryMovements'), 0) as inventory_movements,
       coalesce(jsonb_array_length(p.data->'progressUpdates'), 0) as progress_updates,
       coalesce(jsonb_array_length(p.data->'weeklyClosings'), 0) as weekly_closings,
       coalesce(jsonb_array_length(p.data->'auditLogs'), 0) as audit_logs,
       coalesce(jsonb_array_length(p.data->'userAccounts'), 0) as user_accounts
from public.construction_projects p
order by p.project_id;

select bucket_id, count(*)::bigint as objects, coalesce(sum((metadata->>'size')::bigint), 0) as bytes
from storage.objects
where bucket_id = 'construction-evidence'
group by bucket_id;

select schemaname, tablename, policyname, roles, cmd, qual, with_check
from pg_policies
where schemaname in ('public', 'storage')
  and (tablename like 'construction_%' or tablename = 'app_user_profiles' or tablename = 'objects')
order by schemaname, tablename, policyname;
