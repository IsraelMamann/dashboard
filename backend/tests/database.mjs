import { PGlite } from '@electric-sql/pglite';
import {readFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
const db=new PGlite();
await db.exec(`CREATE ROLE anon; CREATE ROLE authenticated; CREATE SCHEMA auth; CREATE TABLE auth.users(id uuid PRIMARY KEY,email text UNIQUE,encrypted_password text DEFAULT '',email_confirmed_at timestamptz); CREATE FUNCTION auth.uid() RETURNS uuid LANGUAGE sql STABLE AS $$SELECT nullif(current_setting('request.jwt.claim.sub',true),'')::uuid$$; CREATE FUNCTION auth.jwt() RETURNS jsonb LANGUAGE sql STABLE AS $$SELECT coalesce(nullif(current_setting('request.jwt.claims',true),''),'{}')::jsonb$$; GRANT USAGE ON SCHEMA auth TO authenticated; GRANT EXECUTE ON FUNCTION auth.uid(),auth.jwt() TO authenticated;`);
const schema=await readFile(new URL('../schema.sql',import.meta.url),'utf8');await db.exec(schema);await db.exec(schema);
// Upgrade an existing workspace too, after the test has saved reports and assignments.
const migration=await readFile(new URL('../nonrenewal-migration.sql',import.meta.url),'utf8');
const ids={owner:'00000000-0000-0000-0000-000000000001',viewer:'00000000-0000-0000-0000-000000000002',manager:'00000000-0000-0000-0000-000000000003',pending:'00000000-0000-0000-0000-000000000004',invited:'00000000-0000-0000-0000-000000000005'};
async function user(id,email,confirmed=true){await db.query('INSERT INTO auth.users(id,email,email_confirmed_at) VALUES($1,$2,$3)',[id,email,confirmed?new Date().toISOString():null])}
async function as(who,email){await db.exec('RESET ROLE');await db.query("SELECT set_config('request.jwt.claim.sub',$1,false),set_config('request.jwt.claims',$2,false)",[ids[who],JSON.stringify({email})]);await db.exec('SET ROLE authenticated')}
async function fails(fn,needle){await assert.rejects(fn,needle)}
await user(ids.owner,'israelmamann@gmail.com');await user(ids.viewer,'viewer@thebigplan.com');await user(ids.manager,'manager@thebigplan.com');await user(ids.pending,'pending@thebigplan.com',false);
await fails(()=>user('00000000-0000-0000-0000-000000000006','stranger@example.net'),/not approved/);
await db.query("INSERT INTO auth.users(id,email,encrypted_password) VALUES($1,'otp-new-user@thebigplan.com','temporary-auth-password-hash')",['00000000-0000-0000-0000-000000000007']);
await db.query("SELECT set_config('request.jwt.claim.sub','00000000-0000-0000-0000-000000000007',false),set_config('request.jwt.claims','{\"email\":\"otp-new-user@thebigplan.com\"}',false)");await db.exec('SET ROLE authenticated');await fails(()=>db.query('SELECT public.load_dashboard()'),/membership required/);await db.exec('RESET ROLE');
await db.exec('SET ROLE anon');await fails(()=>db.query('SELECT public.load_dashboard()'),/permission denied/);await fails(()=>db.query('SELECT * FROM public.report_snapshots'),/permission denied/);
await as('pending','pending@thebigplan.com');await fails(()=>db.query('SELECT public.ensure_membership()'),/Verify your email/);await fails(()=>db.query('SELECT public.load_dashboard()'),/membership required/);assert.equal((await db.query('SELECT * FROM public.report_snapshots')).rows.length,0);
await as('viewer','viewer@thebigplan.com');await db.query('SELECT public.ensure_membership()');assert.equal((await db.query('SELECT public.app_role() AS role')).rows[0].role,'viewer');
await fails(()=>db.query("SELECT public.save_report('baseline','2026-01-01','[]')"),/Only admins/);await fails(()=>db.query("SELECT public.save_assignments('[]')"),/Only admins/);await fails(()=>db.query("UPDATE public.members SET role='admin' WHERE id=$1",[ids.viewer]),/permission denied/);await fails(()=>db.query("SELECT public.export_contacts('[]')"),/Export requires/);
console.log('PASS anonymous/unsigned membership denial, verified-domain viewer default, unverified temporary-password OTP signup denial and server-enforced write/export roles');
await as('owner','israelmamann@gmail.com');await db.query('SELECT public.set_member_role($1,$2)',[ids.manager,'account_manager']);await fails(()=>db.query('SELECT public.set_member_role($1,$2)',[ids.owner,'viewer']),/owner must remain/);
function row(email='employee@example.com'){return {group:'Employer A',email,name:'Test Employee',phone:'202-555-0100',status:'ENROLLED',lives:3,state:'NY',carrier:'Aetna',effective:'01/01/2026',termination:'',consent:'11/01/2025',age:40,erAllowance:600,erApplied:500,fullPremium:800,tier:'silver',ssn:'SECRET-SSN',address:'SECRET-ADDRESS',dependent_1_ssn:'SECRET-DEPENDENT',birthday:'SECRET-DOB'}}
await db.query('SELECT public.save_report($1,$2,$3)', ['baseline','2026-01-01',JSON.stringify([row()])]);await db.query('SELECT public.save_report($1,$2,$3)', ['current','2026-11-04',JSON.stringify([{...row(),lives:4,status:'PAYMENT_READY'}])]);
let report=(await db.query('SELECT public.load_dashboard() AS data')).rows[0].data;assert.equal(report.baseline[0].lives,3);assert.equal(report.baseline[0].erAllowance,600);assert.equal(report.baseline[0].fullPremium,800);assert.equal(report.baseline[0].age,40);assert.equal(report.current[0].lives,4);assert.equal(Object.keys(report.current[0]).length,16);assert(!JSON.stringify(report).includes('SECRET-'));assert.equal(report.history[0].n,1);
await db.query('SELECT public.save_report($1,$2,$3)', ['current','2026-11-04',JSON.stringify([{...row(),lives:5}])]);assert.equal((await db.query('SELECT count(*)::int n FROM public.report_snapshots')).rows[0].n,2);
await fails(()=>db.query('SELECT public.save_report($1,$2,$3)',['current','2026-11-05',JSON.stringify([{...row(),lives:0}])]),/positive whole/);
await db.query('SELECT public.save_assignments($1)',[JSON.stringify([{employer_account:'Employer A',account_manager:'Jordan',parent_account:'Recover Care'}])]);await fails(()=>db.query('SELECT public.save_assignments($1)',[JSON.stringify([{employer_account:'Employer A',account_manager:'Changed',parent_account:''},{employer_account:'Unknown',account_manager:'Bad',parent_account:''}])]),/Unknown employer/);assert.equal((await db.query('SELECT account_manager FROM public.employer_assignments')).rows[0].account_manager,'Jordan');
await db.exec('RESET ROLE');
await db.exec('ALTER TABLE public.employer_assignments DROP COLUMN not_renewing');
await db.exec(migration);await db.exec(migration);
await as('owner','israelmamann@gmail.com');
const revisionBefore=(await db.query('SELECT public.dashboard_revision() data')).rows[0].data.revision;
await db.query("SELECT public.set_nonrenewal('Employer A',true)");
report=(await db.query('SELECT public.load_dashboard() data')).rows[0].data;
assert.equal(report.nonRenewals['Employer A'],true);assert.equal(report.assignments['Employer A'],'Jordan');assert.equal(report.parents['Employer A'],'Recover Care');assert.equal(report.baseline.length,1);assert.equal(report.current[0].lives,5);assert(report.revision>revisionBefore);
await db.query('SELECT public.save_assignments($1)',[JSON.stringify([{employer_account:'Employer A',account_manager:'Jordan',parent_account:'Recover Care'}])]);
assert.equal((await db.query('SELECT public.load_dashboard() data')).rows[0].data.nonRenewals['Employer A'],true);
await fails(()=>db.query("SELECT public.set_nonrenewal('Unknown',true)"),/Unknown employer/);
await fails(()=>db.query("SELECT public.set_nonrenewal('Employer A',null)"),/decision is required/);
await db.exec('RESET ROLE');await db.exec('SET ROLE anon');await fails(()=>db.query("SELECT public.set_nonrenewal('Employer A',false)"),/permission denied/);
for(const who of ['viewer','manager']){await as(who,who+'@thebigplan.com');await fails(()=>db.query("SELECT public.set_nonrenewal('Employer A',false)"),/Only admins/);assert.equal((await db.query('SELECT public.load_dashboard() data')).rows[0].data.nonRenewals['Employer A'],true);await fails(()=>db.query("UPDATE public.employer_assignments SET not_renewing=false"),/permission denied/)}
await as('owner','israelmamann@gmail.com');await db.query("SELECT public.set_nonrenewal('Employer A',false)");assert.equal((await db.query('SELECT public.load_dashboard() data')).rows[0].data.nonRenewals['Employer A'],false);
console.log('PASS rerunnable renewal-decision migration, shared admin-only flags, revision updates, unchanged reports/mappings, preserved flags on assignment imports, unknown-employer rejection and restoring expectations');
await db.query("SELECT public.invite_member('invited@example.net','admin')");await db.exec('RESET ROLE');await user(ids.invited,'invited@example.net');await as('invited','invited@example.net');await db.query('SELECT public.ensure_membership()');assert.equal((await db.query('SELECT public.app_role() role')).rows[0].role,'admin');
console.log('PASS atomic shared snapshot replacement, database data allowlist, privacy stripping, employer assignment validation, invited external admin and owner protection');
await as('viewer','viewer@thebigplan.com');report=(await db.query('SELECT public.load_dashboard() data')).rows[0].data;assert.equal(report.current[0].lives,5);assert.equal(report.members.length,0);assert.equal((await db.query('SELECT count(*)::int n FROM public.members')).rows[0].n,1);
await as('manager','manager@thebigplan.com');await fails(()=>db.query("SELECT public.save_report('current','2026-11-05','[]')"),/Only admins/);const contacts=(await db.query('SELECT public.export_contacts($1) data',[JSON.stringify([{group:'Employer A',email:'employee@example.com'}])])).rows[0].data;assert.deepEqual(contacts,[{Group:'Employer A','Employee name':'Test Employee',Email:'employee@example.com',Phone:'202-555-0100'}]);
await as('viewer','forged@example.net');await fails(()=>db.query('SELECT public.load_dashboard()'),/membership required/);
console.log('PASS approved shared reads, hidden member directory for viewers, manager exports, blocked manager writes and mismatched-identity denial');
await db.close();
