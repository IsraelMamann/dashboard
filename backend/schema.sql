-- Run in Supabase SQL Editor as project owner. No service-role key belongs in the website.
-- Rerunnable; existing reports, profiles and assignments are preserved.
begin;

create table if not exists public.members (
 id uuid primary key references auth.users(id) on delete cascade,
 email text not null unique,
 role text not null default 'viewer' check (role in ('viewer','account_manager','admin')),
 created_at timestamptz not null default now()
);
create table if not exists public.access_invitations (
 email text primary key, role text not null check (role in ('viewer','account_manager','admin')),
 invited_by uuid references auth.users(id), expires_at timestamptz not null default now()+interval '7 days',
 accepted_at timestamptz, created_at timestamptz not null default now()
);
create table if not exists public.report_snapshots (
 id uuid primary key default gen_random_uuid(),
 kind text not null check (kind in ('baseline','current')),
 snapshot_date date not null,
 rows jsonb not null check (jsonb_typeof(rows)='array'),
 employee_count integer not null default 0, covered_lives bigint not null default 0,
 uploaded_by uuid references auth.users(id), created_at timestamptz not null default now(),
 unique(kind,snapshot_date)
);
create table if not exists public.employer_assignments (
 employer_account text primary key, account_manager text not null default '', parent_account text not null default '',
 updated_at timestamptz not null default now()
);

create table if not exists public.workspace_state (id integer primary key check(id=1),revision bigint not null default 1);
insert into public.workspace_state(id,revision) values(1,1) on conflict(id) do nothing;
create or replace function public.bump_workspace_revision() returns trigger language plpgsql security definer set search_path='' as $$
begin update public.workspace_state set revision=revision+1 where id=1;return null;end $$;
drop trigger if exists members_revision on public.members;
create trigger members_revision after insert or update or delete on public.members for each statement execute function public.bump_workspace_revision();
drop trigger if exists reports_revision on public.report_snapshots;
create trigger reports_revision after insert or update or delete on public.report_snapshots for each statement execute function public.bump_workspace_revision();
drop trigger if exists assignments_revision on public.employer_assignments;
create trigger assignments_revision after insert or update or delete on public.employer_assignments for each statement execute function public.bump_workspace_revision();
drop trigger if exists invitations_revision on public.access_invitations;
create trigger invitations_revision after insert or update or delete on public.access_invitations for each statement execute function public.bump_workspace_revision();
revoke all on public.workspace_state from anon,authenticated;
revoke all on function public.bump_workspace_revision() from public,anon,authenticated;
alter table public.workspace_state enable row level security;

create or replace function public.app_role() returns text
language sql stable security definer set search_path='' as $$
 select m.role from public.members m join auth.users u on u.id=m.id
 where m.id=auth.uid() and u.email_confirmed_at is not null
 and lower(m.email)=lower(auth.jwt()->>'email')
$$;

drop policy if exists state_read on public.workspace_state;
create policy state_read on public.workspace_state for select to authenticated using (public.app_role() is not null);
grant select on public.workspace_state to authenticated;
create or replace function public.dashboard_revision() returns jsonb language plpgsql security invoker set search_path='' as $$
begin
 if public.app_role() is null then raise exception 'Verified workspace membership required' using errcode='42501'; end if;
 return jsonb_build_object('revision',(select revision from public.workspace_state where id=1),'role',public.app_role());
end $$;

create or replace function public.enrollment_member_signup() returns trigger
language plpgsql security definer set search_path='' as $$
declare mail text=lower(trim(new.email)); granted text; pending text;
begin
 select i.role into pending from public.access_invitations i where i.email=mail and i.expires_at>now();
 if mail='israelmamann@gmail.com' then granted='admin';
 elsif pending is not null then granted=pending;
 elsif mail like '%@thebigplan.com' then granted='viewer';
 else raise exception 'This email is not approved for The Big Plan workspace'; end if;
 insert into public.members(id,email,role) values(new.id,mail,granted)
 on conflict(id) do update set email=excluded.email,role=case when public.members.email=excluded.email then public.members.role else excluded.role end;
 if pending is not null then update public.access_invitations set accepted_at=now() where email=mail; end if;
 return new;
end
$$;
drop trigger if exists enrollment_member_signup on auth.users;
create trigger enrollment_member_signup after insert or update of email on auth.users for each row execute function public.enrollment_member_signup();

alter table public.members enable row level security;
alter table public.access_invitations enable row level security;
alter table public.report_snapshots enable row level security;
alter table public.employer_assignments enable row level security;
drop policy if exists members_read on public.members;
create policy members_read on public.members for select to authenticated using (public.app_role() is not null and (id=auth.uid() or public.app_role()='admin'));
drop policy if exists invitations_read on public.access_invitations;
create policy invitations_read on public.access_invitations for select to authenticated using (public.app_role()='admin');
drop policy if exists reports_read on public.report_snapshots;
create policy reports_read on public.report_snapshots for select to authenticated using (public.app_role() is not null);
drop policy if exists assignments_read on public.employer_assignments;
create policy assignments_read on public.employer_assignments for select to authenticated using (public.app_role() is not null);
revoke all on public.members,public.access_invitations,public.report_snapshots,public.employer_assignments from anon,authenticated;
grant select on public.members,public.access_invitations,public.report_snapshots,public.employer_assignments to authenticated;

-- This allowlist runs on the database as well as in the browser. Extra source fields are discarded.
create or replace function public.ensure_membership() returns void
language plpgsql security definer set search_path='' as $$
declare mail text; granted text; pending text;
begin
 select lower(u.email) into mail from auth.users u where u.id=auth.uid() and u.email_confirmed_at is not null and lower(u.email)=lower(auth.jwt()->>'email');
 if mail is null then raise exception 'Verify your email before joining the workspace' using errcode='42501'; end if;
 if public.app_role() is not null then return; end if;
 select i.role into pending from public.access_invitations i where i.email=mail and i.expires_at>now();
 if mail='israelmamann@gmail.com' then granted='admin'; elsif pending is not null then granted=pending; elsif mail like '%@thebigplan.com' then granted='viewer'; else raise exception 'This email has not been invited' using errcode='42501'; end if;
 insert into public.members(id,email,role) values(auth.uid(),mail,granted) on conflict(id) do nothing;
 if pending is not null then update public.access_invitations set accepted_at=now() where email=mail; end if;
end
$$;

create or replace function public.normalize_report(p_rows jsonb) returns jsonb
language plpgsql security definer set search_path='' as $$
declare r jsonb; clean jsonb='[]'::jsonb;
begin
 if jsonb_typeof(p_rows)<>'array' or jsonb_array_length(p_rows)>50000 then raise exception 'A report must contain at most 50000 employee rows'; end if;
 for r in select value from jsonb_array_elements(p_rows) loop
  if jsonb_typeof(r)<>'object' or length(trim(coalesce(r->>'group','')))=0 or length(trim(coalesce(r->>'email','')))=0 then raise exception 'Each employee needs an employer and email'; end if;
  if jsonb_typeof(r->'lives') is distinct from 'number' or (r->>'lives')::numeric<1 or (r->>'lives')::numeric<>trunc((r->>'lives')::numeric) then raise exception 'Covered lives must be a positive whole number'; end if;
  if length(r->>'email')>320 or length(r->>'group')>400 then raise exception 'Employer or email field is too long'; end if;
  if exists(select 1 from unnest(array['erAllowance','erApplied','fullPremium','age']) k where r?k and r->k<>'null'::jsonb and (jsonb_typeof(r->k)<>'number' or (r->>k)::numeric<0)) then raise exception 'Costs and age must be nonnegative numbers or null'; end if;
  if r->'age'<>'null'::jsonb and (r->>'age')::numeric>120 then raise exception 'Employee age is invalid'; end if;
 end loop;
 select coalesce(jsonb_agg(jsonb_build_object(
   'group',trim(source.r->>'group'),'email',trim(source.r->>'email'),'name',coalesce(source.r->>'name',''),'phone',coalesce(source.r->>'phone',''),
   'status',upper(replace(trim(coalesce(source.r->>'status','')),' ','_')),'lives',(source.r->>'lives')::integer,
   'state',coalesce(source.r->>'state',''),'carrier',coalesce(source.r->>'carrier',''),'effective',coalesce(source.r->>'effective',''),
   'termination',coalesce(source.r->>'termination',''),'consent',coalesce(source.r->>'consent',''),
   'erAllowance',source.r->'erAllowance','erApplied',source.r->'erApplied','fullPremium',source.r->'fullPremium','age',source.r->'age','tier',coalesce(source.r->>'tier','unknown')
  ) order by n),'[]'::jsonb) into clean from jsonb_array_elements(p_rows) with ordinality as source(r,n);
 return clean;
end
$$;

create or replace function public.save_report(p_kind text,p_snapshot_date date,p_rows jsonb) returns uuid
language plpgsql security definer set search_path='' as $$
declare clean jsonb; result uuid; count_ee integer; count_lives bigint;
begin
 if public.app_role() is distinct from 'admin' then raise exception 'Only admins can upload reports' using errcode='42501'; end if;
 if p_kind not in ('baseline','current') or p_snapshot_date is null then raise exception 'Invalid report type or date'; end if;
 clean=public.normalize_report(p_rows);
 select count(*),coalesce(sum((r->>'lives')::integer),0) into count_ee,count_lives from jsonb_array_elements(clean) r
 where case when p_kind='baseline' then r->>'status'='ENROLLED' else r->>'status' in ('ENROLLED','APPLICATION_READY','PAYMENT_READY','STUCK') end;
 insert into public.report_snapshots(kind,snapshot_date,rows,employee_count,covered_lives,uploaded_by)
 values(p_kind,p_snapshot_date,clean,count_ee,count_lives,auth.uid())
 on conflict(kind,snapshot_date) do update set rows=excluded.rows,employee_count=excluded.employee_count,covered_lives=excluded.covered_lives,uploaded_by=excluded.uploaded_by,created_at=now()
 returning id into result;
 return result;
end
$$;

create or replace function public.save_assignments(p_assignments jsonb) returns integer
language plpgsql security definer set search_path='' as $$
declare r jsonb; employer text; parent_label text; known jsonb;
begin
 if public.app_role() is distinct from 'admin' then raise exception 'Only admins can manage assignments' using errcode='42501'; end if;
 if jsonb_typeof(p_assignments)<>'array' then raise exception 'Assignments must be a list'; end if;
 if exists(select 1 from jsonb_array_elements(p_assignments) a group by a->>'employer_account' having count(*)>1) then raise exception 'Duplicate employer in assignment file'; end if;
 select coalesce(jsonb_agg(distinct e->>'group'),'[]') into known from
 (select rows from public.report_snapshots where kind='baseline' order by created_at desc limit 1) b cross join lateral jsonb_array_elements(b.rows) e;
 known=known||coalesce((select jsonb_agg(distinct e->>'group') from
 (select rows from public.report_snapshots where kind='current' order by snapshot_date desc,created_at desc limit 1) c cross join lateral jsonb_array_elements(c.rows) e),'[]');
 for r in select value from jsonb_array_elements(p_assignments) loop
  employer=trim(coalesce(r->>'employer_account',''));parent_label=trim(coalesce(r->>'parent_account',''));
  if not known?employer then raise exception 'Unknown employer in assignment file'; end if;
  if parent_label=employer then parent_label=''; end if;
  insert into public.employer_assignments(employer_account,account_manager,parent_account)
  values(employer,trim(coalesce(r->>'account_manager','')),parent_label)
  on conflict(employer_account) do update set account_manager=excluded.account_manager,parent_account=excluded.parent_account,updated_at=now();
 end loop;
 if exists(select 1 from public.employer_assignments a join public.employer_assignments p on p.employer_account=a.parent_account where a.parent_account<>'' and p.parent_account<>'' and p.parent_account<>p.employer_account) then raise exception 'Use one parent account level only'; end if;
 return jsonb_array_length(p_assignments);
end
$$;

create or replace function public.set_member_role(p_member_id uuid,p_role text) returns void
language plpgsql security definer set search_path='' as $$
begin
 if public.app_role() is distinct from 'admin' then raise exception 'Only admins can manage roles' using errcode='42501'; end if;
 if p_role not in ('viewer','account_manager','admin') then raise exception 'Invalid role'; end if;
 if exists(select 1 from public.members where id=p_member_id and email='israelmamann@gmail.com') and p_role<>'admin' then raise exception 'The workspace owner must remain an admin'; end if;
 update public.members set role=p_role where id=p_member_id;
 if not found then raise exception 'Member not found'; end if;
end
$$;
create or replace function public.invite_member(p_email text,p_role text default 'admin') returns jsonb
language plpgsql security definer set search_path='' as $$
declare mail text=lower(trim(p_email)); member_id uuid;
begin
 if public.app_role() is distinct from 'admin' then raise exception 'Only admins can invite members' using errcode='42501'; end if;
 if mail!~'^[^[:space:]@]+@[^[:space:]@]+\.[^[:space:]@]+$' or p_role not in ('viewer','account_manager','admin') then raise exception 'Invalid invitation'; end if;
 select id into member_id from public.members where email=mail;
 if member_id is not null then perform public.set_member_role(member_id,p_role);return jsonb_build_object('existing_member',true); end if;
 insert into public.access_invitations(email,role,invited_by) values(mail,p_role,auth.uid())
 on conflict(email) do update set role=excluded.role,invited_by=excluded.invited_by,expires_at=now()+interval '7 days',accepted_at=null,created_at=now();
 return jsonb_build_object('existing_member',false);
end
$$;
create or replace function public.revoke_invitation(p_email text) returns void
language plpgsql security definer set search_path='' as $$
begin
 if public.app_role() is distinct from 'admin' then raise exception 'Only admins can revoke invitations' using errcode='42501'; end if;
 delete from public.access_invitations where email=lower(trim(p_email)) and accepted_at is null;
end
$$;

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
  'parents',coalesce((select jsonb_object_agg(employer_account,parent_account) from public.employer_assignments),'{}'),
  'member',(select to_jsonb(m) from public.members m where id=auth.uid()),
  'members',case when public.app_role()='admin' then coalesce((select jsonb_agg(to_jsonb(m) order by m.email) from public.members m),'[]') else '[]'::jsonb end,
  'invitations',case when public.app_role()='admin' then coalesce((select jsonb_agg(to_jsonb(i) order by i.created_at desc) from public.access_invitations i where i.accepted_at is null and i.expires_at>now()),'[]') else '[]'::jsonb end
 ) into result;
 return result;
end
$$;

create or replace function public.export_contacts(p_selections jsonb) returns jsonb
language plpgsql security invoker set search_path='' as $$
declare current_map jsonb; prior_map jsonb; selected jsonb; contact jsonb; result jsonb='[]'::jsonb; key text;
begin
 if coalesce(public.app_role(),'') not in ('admin','account_manager') then raise exception 'Export requires account manager or admin access' using errcode='42501'; end if;
 if jsonb_typeof(p_selections)<>'array' or jsonb_array_length(p_selections)>50000 then raise exception 'Invalid contact selection'; end if;
 select coalesce(jsonb_object_agg(replace(lower(trim(r->>'email')),'delete',''),r),'{}') into current_map from
 (select rows from public.report_snapshots where kind='current' order by snapshot_date desc,created_at desc limit 1) s cross join lateral jsonb_array_elements(s.rows) r
 where r->>'status' in ('ENROLLED','APPLICATION_READY','PAYMENT_READY','STUCK');
 select coalesce(jsonb_object_agg((r->>'group')||'|'||replace(lower(trim(r->>'email')),'delete',''),r),'{}') into prior_map from
 (select rows from public.report_snapshots where kind='baseline' order by created_at desc limit 1) s cross join lateral jsonb_array_elements(s.rows) r where r->>'status'='ENROLLED';
 for selected in select value from jsonb_array_elements(p_selections) loop
  key=replace(lower(trim(selected->>'email')),'delete','');
  contact=coalesce(current_map->key,prior_map->((selected->>'group')||'|'||key));
  if contact is not null then result=result||jsonb_build_array(jsonb_build_object('Group',selected->>'group','Employee name',contact->>'name','Email',contact->>'email','Phone',contact->>'phone')); end if;
 end loop;
 return result;
end
$$;

revoke all on function public.normalize_report(jsonb) from public,anon,authenticated;
revoke all on function public.enrollment_member_signup() from public,anon,authenticated;
revoke all on function public.app_role(),public.dashboard_revision(),public.ensure_membership(), public.save_report(text,date,jsonb),public.save_assignments(jsonb),public.set_member_role(uuid,text),public.invite_member(text,text),public.revoke_invitation(text),public.load_dashboard(),public.export_contacts(jsonb) from public,anon,authenticated;
grant execute on function public.app_role(),public.dashboard_revision(),public.ensure_membership(),public.save_report(text,date,jsonb),public.save_assignments(jsonb),public.set_member_role(uuid,text),public.invite_member(text,text),public.revoke_invitation(text),public.load_dashboard(),public.export_contacts(jsonb) to authenticated;
commit;
