begin;
alter table public.employer_assignments add column if not exists not_renewing boolean not null default false;
create or replace function public.set_nonrenewal(p_employer text,p_not_renewing boolean) returns void
language plpgsql security definer set search_path='' as $$
begin
 if public.app_role() is distinct from 'admin' then raise exception 'Only admins can change renewal decisions' using errcode='42501'; end if;
 if p_not_renewing is null then raise exception 'A renewal decision is required'; end if;
 if not exists(select 1 from public.report_snapshots s cross join lateral jsonb_array_elements(s.rows) r where r->>'group'=p_employer) then raise exception 'Unknown employer'; end if;
 insert into public.employer_assignments(employer_account,not_renewing) values(p_employer,p_not_renewing)
 on conflict(employer_account) do update set not_renewing=excluded.not_renewing,updated_at=now();
end $$;

create or replace function public.load_dashboard() returns jsonb
language plpgsql security invoker set search_path='' as $$
declare result jsonb;
begin
 if public.app_role() is null then raise exception 'Verified workspace membership required' using errcode='42501'; end if;
 select jsonb_build_object(
  'revision',(select revision from public.workspace_state where id=1),
  'baseline',(select rows from public.report_snapshots where kind='baseline' order by created_at desc limit 1),
  'current',(select rows from public.report_snapshots where kind='current' order by snapshot_date desc,created_at desc limit 1),
  'history',coalesce((select jsonb_agg(jsonb_build_object('date',snapshot_date,'n',employee_count,'uploadedAt',created_at,'name','Shared daily snapshot') order by snapshot_date) from public.report_snapshots where kind='current'),'[]'),
  'assignments',coalesce((select jsonb_object_agg(employer_account,account_manager) from public.employer_assignments),'{}'),
  'nonRenewals',coalesce((select jsonb_object_agg(employer_account,not_renewing) from public.employer_assignments),'{}'),
  'parents',coalesce((select jsonb_object_agg(employer_account,parent_account) from public.employer_assignments),'{}'),
  'member',(select to_jsonb(m) from public.members m where id=auth.uid()),
  'members',case when public.app_role()='admin' then coalesce((select jsonb_agg(to_jsonb(m) order by m.email) from public.members m),'[]') else '[]'::jsonb end,
  'invitations',case when public.app_role()='admin' then coalesce((select jsonb_agg(to_jsonb(i) order by i.created_at desc) from public.access_invitations i where i.accepted_at is null and i.expires_at>now()),'[]') else '[]'::jsonb end
 ) into result;
 return result;
end
$$;


revoke all on function public.set_nonrenewal(text,boolean) from public,anon,authenticated;
grant execute on function public.set_nonrenewal(text,boolean) to authenticated;
commit;
