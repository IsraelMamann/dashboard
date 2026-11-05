from pathlib import Path
from urllib.parse import urlparse,parse_qs
import http.server,threading,functools,json,csv,io
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parent
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT.parent/'deployment'/'workspace')))
threading.Thread(target=server.serve_forever,daemon=True).start()
state={'baseline':None,'current':None,'history':[],'assignments':{},'parents':{},'revision':1,'members':[{'id':'owner','email':'israelmamann@gmail.com','role':'admin'},{'id':'viewer','email':'viewer@thebigplan.com','role':'viewer'}],'invitations':[]}
active={'email':None}
requests=[]
def handle(route):
 request=route.request;url=request.url;headers={'Content-Type':'application/json','Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'apikey,authorization,content-type','Access-Control-Allow-Methods':'POST,GET,OPTIONS'}
 if request.method=='OPTIONS':route.fulfill(status=204,headers=headers);return
 args=request.post_data_json if request.method=='POST' else {};requests.append((url,args))
 if '/auth/v1/otp' in url:
  if args['email']=='limited@thebigplan.com':route.fulfill(status=429,headers=headers,body=json.dumps({'msg':'email rate limit exceeded'}));return
  active['email']=args['email'];result={}
 elif '/auth/v1/verify' in url:
  if args['token']!='123456':route.fulfill(status=400,headers=headers,body=json.dumps({'msg':'Invalid code'}));return
  result={'access_token':'test-access','refresh_token':'test-refresh','expires_in':3600}
 elif '/auth/v1/token' in url:result={'access_token':'test-access-refreshed','refresh_token':'test-refresh-new','expires_in':3600}
 elif '/auth/v1/user' in url:
  if request.headers.get('authorization')=='Bearer rejected':route.fulfill(status=401,headers=headers,body=json.dumps({'msg':'Invalid access token'}));return
  result={'email':active['email']}
 elif '/auth/v1/logout' in url:result={}
 else:
  member=next(m for m in state['members'] if m['email']==active['email']);rpc=url.rsplit('/',1)[-1]
  if rpc=='ensure_membership':result=None
  elif rpc=='load_dashboard':result={**state,'member':member,'members':state['members'] if member['role']=='admin' else [],'invitations':state['invitations'] if member['role']=='admin' else []}
  elif rpc=='dashboard_revision':result={'revision':state['revision'],'role':member['role']}
  elif rpc=='save_report':
   if member['role']!='admin':route.fulfill(status=403,headers=headers,body=json.dumps({'message':'Only admins can upload reports'}));return
   state[args['p_kind']]=args['p_rows'];state['revision']+=1
   if args['p_kind']=='current':state['history']=[{'date':args['p_snapshot_date'],'n':len(args['p_rows']),'uploadedAt':'2026-11-04T12:00:00Z','name':'Shared daily snapshot'}]
   result='report-id'
  elif rpc=='save_assignments':
   for row in args['p_assignments']:state['assignments'][row['employer_account']]=row['account_manager'];state['parents'][row['employer_account']]=row['parent_account']
   state['revision']+=1;result=len(args['p_assignments'])
  elif rpc=='invite_member':state['invitations'].append({'email':args['p_email'],'role':args['p_role']});state['revision']+=1;result={'existing_member':False}
  elif rpc=='export_contacts':
   if member['role']=='viewer':route.fulfill(status=403,headers=headers,body=json.dumps({'message':'Export requires account manager or admin access'}));return
   result=[{'Group':'Employer A','Employee name':'Test Person','Email':'employee@example.com','Phone':'202-555-0100'}]
  else:raise AssertionError('Unexpected API '+url)
 route.fulfill(status=200,headers=headers,body=json.dumps(result))
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=b.new_page(viewport={'width':1440,'height':1100});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.route('**/config.js*',lambda route:route.fulfill(content_type='application/javascript',body='window.BIG_PLAN_CONFIG={supabaseUrl:"https://abcdefghijklmnopqrst.supabase.co",publishableKey:"sb_publishable_test"}'))
 page.route('https://abcdefghijklmnopqrst.supabase.co/**',handle)
 page.goto(f'http://127.0.0.1:{server.server_port}/index.html');page.locator('#cloud-login-form').wait_for();assert not page.locator('main').is_visible()
 page.locator('#cloud-email').fill('limited@thebigplan.com');page.locator('#cloud-login-form button').click();page.get_by_text('Email delivery is currently rate-limited',exact=False).wait_for();count=len([u for u,a in requests if '/auth/v1/otp' in u]);page.locator('#cloud-login-form button').click();page.get_by_text('Please wait a minute',exact=False).wait_for();assert len([u for u,a in requests if '/auth/v1/otp' in u])==count
 page.reload();page.locator('#cloud-login-form').wait_for()
 print('PASS provider rate-limit guidance and no immediate repeat email request')
 def login(email):
  page.locator('#cloud-email').fill(email);page.locator('#cloud-login-form button').click();page.locator('#cloud-code').wait_for();page.locator('#cloud-code').fill('123456');page.locator('#cloud-verify-form button').click();page.locator('#cloud-signout').wait_for()
 login('israelmamann@gmail.com');assert all(parse_qs(urlparse(url).query).get('redirect_to')==['https://israelmamann.github.io/dashboard/'] for url,args in requests if '/auth/v1/otp' in url);assert page.evaluate('Cloud.member.role')=='admin';assert page.locator('#role').is_hidden();assert page.locator('#mode').is_hidden()
 page.locator('[data-page=admin]').click();page.locator('#real-invite').wait_for()
 report='company_name,employee_email,first_name,last_name,enrollment_status,total_lives_on_plan,address_permanent_state,ssn,address_permanent_street,dependent_1_ssn,ichra_allotted,premium\nEmployer A,employee@example.com,Test,Person,ENROLLED,2,NY,SECRET-SSN,SECRET-STREET,SECRET-DEPENDENT,$ 600.00,$ 800.00\n'
 for kind in ['base','current']:
  page.locator(f'[data-upload={kind}]').set_input_files({'name':kind+'.csv','mimeType':'text/csv','buffer':report.encode()});page.get_by_text('Saved to the shared workspace.',exact=True).wait_for()
  page.wait_for_function(f'uploads.{kind} !== null')
 assert page.locator('#stored-field-audit').is_visible()
 assert page.evaluate('Cloud.fieldAudit.baseline.rows')==1
 assert page.evaluate('Cloud.fieldAudit.baseline.unexpectedFields.length')==0
 assert page.evaluate('storedFieldAudit([{group:"A",ssn:"PRIVATE-SENTINEL"}]).unexpectedFields')==['ssn']
 assert 'PRIVATE-SENTINEL' not in page.locator('#stored-field-audit').inner_text()
 assert 'SECRET-' not in json.dumps(state)
 assert [args['p_kind'] for url,args in requests if url.endswith('/save_report')]==['baseline','current']
 assert all(len(r)==16 for r in state['baseline'])
 assert state['baseline'][0]['erAllowance']==600
 assert state['current'][0]['fullPremium']==800
 assert page.evaluate('Cloud.fieldAudit.baseline.numericCoverage.erAllowance.numeric')==1
 page.locator('[data-assign="Employer A"]').fill('Jordan');page.locator('[data-assign="Employer A"]').press('Tab');page.wait_for_function('assignment["Employer A"] === "Jordan"')
 page.locator('[data-parent-assign="Employer A"]').fill('Recover Care');page.locator('[data-parent-assign="Employer A"]').press('Tab');page.wait_for_function('parents["Employer A"] === "Recover Care"')
 page.locator('#real-invite-email').fill('newadmin@example.com');page.locator('#real-invite button').click();page.get_by_text('newadmin@example.com · Admin',exact=False).wait_for()
 print('PASS explicit published-site email redirect, real auth API contract, hidden private UI before verification, server-loaded role, shared report saves, minimized payloads, assignments and invitations')
 page.locator('#cloud-signout').click();page.locator('#cloud-login-form').wait_for();assert page.evaluate('uploads.base === null && !Cloud.member');assert 'employee@example.com' not in page.locator('#app').inner_text();assert page.evaluate('sessionStorage.getItem("big-plan-workspace-session")') is None
 login('viewer@thebigplan.com');assert page.evaluate('role')=='Viewer';assert page.evaluate('uploads.current.length')==1;assert page.evaluate('parents["Employer A"]')=='Recover Care'
 page.locator('[data-page=groups]').click();page.locator('[data-parent="Recover Care"]').click();page.locator('.dialog [data-group="Employer A"]').click();assert page.locator('#export').is_disabled();page.locator('#close').click()
 result=page.evaluate('Cloud.rpc("export_contacts",{p_selections:[]}).then(()=>"BAD").catch(e=>e.message)');assert 'Export requires' in result
 page.locator('[data-page=admin]').click();assert page.locator('[data-upload]').count()==0
 page.reload();page.locator('#cloud-signout').wait_for();assert page.evaluate('role')=='Viewer';assert page.evaluate('uploads.current.length')==1
 print('PASS logout clears employee data/tokens, viewer sees shared persisted report on a separate login, server export denial, restricted admin UI and session restoration')
 page.locator('#cloud-signout').click()
 page.goto(f'http://127.0.0.1:{server.server_port}/index.html#access_token=verified-link-token&refresh_token=link-refresh&expires_in=3600');page.locator('#cloud-signout').wait_for();assert '#' not in page.url;assert page.evaluate('Cloud.member.role')=='viewer'
 page.goto(f'http://127.0.0.1:{server.server_port}/index.html#access_token=rejected&refresh_token=bad&expires_in=3600');page.locator('#cloud-login-form').wait_for();assert not page.locator('main').is_visible();assert '#' not in page.url;assert page.evaluate('sessionStorage.getItem("big-plan-workspace-session")') is None
 print('PASS secure-link callback is verified against the auth service, tokens removed from URL, and invalid callbacks are cleared/denied')
 page.set_viewport_size({'width':390,'height':844});assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
 assert not errors,errors;print('PASS responsive sign-in and no browser errors (mock service; live email and Supabase project still require verification)');b.close()
