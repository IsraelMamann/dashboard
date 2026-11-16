"""Verify PDF exports against the connected workspace's actual role contract."""
from pathlib import Path
import functools,http.server,threading,json
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]/'deployment'/'workspace'
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(root)));threading.Thread(target=server.serve_forever,daemon=True).start()
state={'role':'viewer','exportRole':'viewer','revisionChecks':0}
row={'group':'Example Employer','email':'example@example.test','name':'PRIVATE NAME','phone':'PRIVATE PHONE','status':'ENROLLED','lives':2,'state':'NY','carrier':'Aetna','effective':'01/01/2026','termination':'','consent':'2026-11-16'}
def handle(route):
 request=route.request;url=request.url;headers={'Content-Type':'application/json','Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'apikey,authorization,content-type','Access-Control-Allow-Methods':'POST,GET,OPTIONS'}
 if request.method=='OPTIONS':route.fulfill(status=204,headers=headers);return
 if '/auth/v1/user' in url:result={'id':'member','email':'member@thebigplan.com'}
 elif url.endswith('/load_dashboard'):result={'member':{'id':'member','email':'member@thebigplan.com','role':state['role']},'baseline':[row],'current':[{**row,'effective':'01/01/2027'}],'history':[],'assignments':{'Example Employer':'Jordan'},'parents':{},'nonRenewals':{},'members':[],'invitations':[],'revision':1}
 elif url.endswith('/dashboard_revision'):state['revisionChecks']+=1;result={'role':state['exportRole'],'revision':1}
 else:raise AssertionError('Unexpected remote service '+url)
 route.fulfill(status=200,headers=headers,body=json.dumps(result))
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=b.new_page(viewport={'width':1440,'height':1000});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.route('**/config.js*',lambda route:route.fulfill(content_type='application/javascript',body='window.BIG_PLAN_CONFIG={supabaseUrl:"https://abcdefghijklmnopqrst.supabase.co",publishableKey:"sb_publishable_test"}'))
 page.route('https://abcdefghijklmnopqrst.supabase.co/**',handle)
 page.add_init_script('localStorage.setItem("big-plan-workspace-session",JSON.stringify({accessToken:"test-access",refreshToken:"test-refresh",expiresAt:Date.now()+3600000}))')
 page.goto(f'http://127.0.0.1:{server.server_port}/index.html');page.locator('#cloud-signout').wait_for();page.locator('[data-page=reports]').click();assert page.locator('#progress-preview').is_visible();assert page.locator('#progress-export').is_disabled();assert page.evaluate('canExportProgressReport()') is False
 assert 'requires account manager' in page.evaluate('downloadProgressReport().then(()=>"unexpected",e=>e.message)')
 state['role']='account_manager';state['exportRole']='account_manager';page.reload();page.locator('#cloud-signout').wait_for();page.locator('[data-page=reports]').click();page.locator('#progress-manager').select_option('Jordan')
 with page.expect_download() as download:page.locator('#progress-export').click()
 assert download.value.suggested_filename.startswith('big-plan-manager-jordan-');assert state['revisionChecks']>=1
 # A stale client role cannot authorize a PDF when the server has revoked export permission.
 state['exportRole']='viewer';page.locator('#progress-export').click();page.wait_for_function('document.querySelector("#progress-status").textContent.includes("requires account manager")')
 page.evaluate('Cloud.lock()');assert not page.locator('main').is_visible();assert page.evaluate('canExportProgressReport()') is False;assert not errors,errors;b.close()
server.shutdown()
print('PASS shared report PDF download for account managers, viewer denial, server role recheck and sign-out gate; no external PDF service or contact export endpoint.')
