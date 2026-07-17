-- Capture this result next to the JSON/Storage export and compare it with the
-- importer run's input_counts_json. This script changes no source data.

with snapshots as (
  select project_id, data from public.construction_projects
), counts as (
  select project_id, 'phases' as entity, coalesce(jsonb_array_length(data->'phases'), 0)::bigint as records from snapshots
  union all select project_id, 'incomes', coalesce(jsonb_array_length(data->'incomes'), 0) from snapshots
  union all select project_id, 'expenses', coalesce(jsonb_array_length(data->'expenses'), 0) from snapshots
  union all select project_id, 'laborContracts', coalesce(jsonb_array_length(data->'laborContracts'), 0) from snapshots
  union all select project_id, 'materials', coalesce(jsonb_array_length(data->'materials'), 0) from snapshots
  union all select project_id, 'inventoryMovements', coalesce(jsonb_array_length(data->'inventoryMovements'), 0) from snapshots
  union all select project_id, 'progressUpdates', coalesce(jsonb_array_length(data->'progressUpdates'), 0) from snapshots
  union all select project_id, 'weeklyClosings', coalesce(jsonb_array_length(data->'weeklyClosings'), 0) from snapshots
  union all select project_id, 'reports', coalesce(jsonb_array_length(data->'reports'), 0) from snapshots
  union all select project_id, 'notificationLogs', coalesce(jsonb_array_length(data->'notificationLogs'), 0) from snapshots
  union all select project_id, 'auditLogs', coalesce(jsonb_array_length(data->'auditLogs'), 0) from snapshots
  union all select project_id, 'userAccounts', coalesce(jsonb_array_length(data->'userAccounts'), 0) from snapshots
)
select project_id, entity, records from counts order by project_id, entity;

select bucket_id, name as object_path, (metadata->>'size')::bigint as bytes, created_at, updated_at
from storage.objects
where bucket_id = 'construction-evidence'
order by name;
