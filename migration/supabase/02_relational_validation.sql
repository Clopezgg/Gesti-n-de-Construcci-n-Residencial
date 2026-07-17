-- Read-only integrity checks. Every query should return zero rows.

select 'profile_without_project' as issue, p.id::text as record_id, p.project_id
from public.app_user_profiles p
left join public.construction_projects c on c.project_id = p.project_id
where c.project_id is null;

select 'version_without_project' as issue, v.id::text as record_id, v.project_id
from public.construction_project_versions v
left join public.construction_projects c on c.project_id = v.project_id
where c.project_id is null;

select 'audit_without_project' as issue, a.id::text as record_id, a.project_id
from public.construction_audit_events a
left join public.construction_projects c on c.project_id = a.project_id
where c.project_id is null;

select 'partner_without_project' as issue, b.id::text as record_id, b.project_id
from public.construction_business_partners b
left join public.construction_projects c on c.project_id = b.project_id
where c.project_id is null;

select 'payable_without_project' as issue, p.id::text as record_id, p.project_id
from public.construction_payables p
left join public.construction_projects c on c.project_id = p.project_id
where c.project_id is null;

select project_id, id, count(*) as duplicates
from public.app_user_profiles
group by project_id, id
having count(*) > 1;

select project_id, event_hash, count(*) as duplicates
from public.construction_audit_events
group by project_id, event_hash
having count(*) > 1;

select project_id
from public.construction_projects
where data is null or jsonb_typeof(data) <> 'object' or jsonb_typeof(data->'settings') <> 'object';
