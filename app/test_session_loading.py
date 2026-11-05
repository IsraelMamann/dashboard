"""Delay auth/report responses to reproduce false logout and token-rotation reloads."""
from pathlib import Path
import base64,functools,http.server,json,threading
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parent.parent/'deployment/workspace'
api='https://abcdefghijklmnopqrst.supabase.co'
key='big-plan-workspace-session'
def jwt(subject,serial=1):
 def part(value):return base64.urlsafe_b64encode(json.dumps(value).encode()).decode().rstrip('=')
 return part({'alg':'HS256'})+'.'+part({'sub':subject,'serial':serial})+'.fixture'
class Handler(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_GET(self):
  if self.path.startswith('/blank'):
   self.send_response(200);self.send_header('Content-Type','text/html');self.end_headers();self.wfile.write(b'<!doctype html><title>Other tab</title>');return
  super().do_GET()
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Handler,directory=str(root)))
threading.Thread(target=server.serve_forever,daemon=True).start()
url=f'http://127.0.0.1:{server.server_port}'
state={'loads':0,'users':0,'refreshes':0,'hold_reports':True,'hold_users':True,'reports':[],'user_requests':[],'identity':'viewer'}
headers={'Content-Type':'application/json','Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'apikey,authorization,content-type','Access-Control-Allow-Methods':'POST,GET,OPTIONS'}
def user():return {'id':state['identity'],'email':state['identity']+'@thebigplan.com'}
def report():return {'baseline':[],'current':[],'history':[],'assignments':{},'parents':{},'nonRenewals':{},'member':{**user(),'role':'viewer'},'members':[],'invitations':[],'revision':1}
def fulfill(route,data):route.fulfill(status=200,headers=headers,body=json.dumps(data))
def handle(route):
 req=route.request;path=req.url
 if req.method=='OPTIONS':route.fulfill(status=204,headers=headers);return
 if '/auth/v1/user' in path:
  state['users']+=1
  if state['hold_users']:state['user_requests'].append(route);return
  data=user()
 elif path.endswith('/load_dashboard'):
  state['loads']+=1
  if state['hold_reports']:state['reports'].append(route);return
  data=report()
 elif '/auth/v1/token' in path:
  state['refreshes']+=1;data={'access_token':jwt(state['identity'],3),'refresh_token':'refresh-3','expires_in':3600}
 elif path.endswith('/dashboard_revision'):data={'role':'viewer','revision':1}
 else:raise AssertionError('Unexpected endpoint '+path)
 fulfill(route,data)
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);context=b.new_context();errors=[]
 context.on('page',lambda page:page.on('pageerror',lambda e:errors.append(str(e))))
 context.route('**/config.js*',lambda route:route.fulfill(content_type='application/javascript',body=f'window.BIG_PLAN_CONFIG={{supabaseUrl:"{api}",publishableKey:"sb_publishable_test"}}'))
 context.route(api+'/**',handle)
 page=context.new_page()
 page.add_init_script('''window.loginWasShown=false;new MutationObserver(()=>{if(document.querySelector('#cloud-login-form'))window.loginWasShown=true}).observe(document,{childList:true,subtree:true})''')
 # Seed a previously verified browser, with no report rows in storage.
 page.add_init_script(f'''if(!localStorage.getItem({json.dumps(key)}))localStorage.setItem({json.dumps(key)},JSON.stringify({{accessToken:{json.dumps(jwt('viewer'))},refreshToken:'refresh-1',expiresAt:Date.now()+3600000}}))''')
 page.goto(url+'/index.html',wait_until='domcontentloaded')
 page.get_by_role('heading',name='Opening your dashboard.').wait_for()
 page.wait_for_timeout(100)
 assert state['loads']==state['users']==1,'User and report checks should start in parallel'
 assert page.locator('#cloud-login-form').count()==0;assert not page.locator('main').is_visible()
 page.evaluate('()=>{window.extraLoads=[Cloud.load(true),Cloud.load(true)]}')
 page.wait_for_timeout(50);assert state['loads']==1,'Concurrent refreshes should reuse the pending report request'
 # Even if the private report arrives first, identity verification must finish before display.
 fulfill(state['reports'].pop(),report());state['hold_reports']=False
 page.wait_for_timeout(50);assert not page.locator('main').is_visible()
 fulfill(state['user_requests'].pop(),user());state['hold_users']=False
 page.locator('#cloud-signout').wait_for();page.evaluate('Promise.all(window.extraLoads)')
 assert not page.evaluate('window.loginWasShown')
 assert page.locator('[data-filter=carrier] option').first.inner_text()=='Carriers'
 assert page.get_by_role('heading',name='Carrier mix',exact=True).is_visible()
 print('PASS delayed report restoration shows loading without a login flash, checks identity in parallel, coalesces full loads and keeps reports hidden until verified')
 # Another browser tab writes the next token, as happens when Supabase renews that tab's session.
 other=context.new_page();other.goto(url+'/blank');page.bring_to_front()
 other.evaluate('(token)=>localStorage.setItem("big-plan-workspace-session",JSON.stringify({accessToken:token,refreshToken:"refresh-2",expiresAt:Date.now()+3600000}))',jwt('viewer',2))
 page.wait_for_function('(token)=>Cloud.session.accessToken===token',arg=jwt('viewer',2))
 assert page.locator('main').is_visible();assert not page.evaluate('window.loginWasShown');assert state['loads']==1
 # Expiry still renews silently, without reloading reports.
 other.evaluate('const saved=JSON.parse(localStorage.getItem("big-plan-workspace-session"));saved.expiresAt=Date.now()-1000;localStorage.setItem("big-plan-workspace-session",JSON.stringify(saved))')
 page.wait_for_function('Cloud.session.refreshToken==="refresh-3"')
 assert page.locator('main').is_visible();assert state['refreshes']==1;assert state['loads']==1
 print('PASS same-user cross-tab token rotation and automatic expiry renewal keep the dashboard visible and avoid full report reloads')
 # A different account must go through the gate and full verification again.
 state['identity']='other';state['hold_reports']=True
 other.evaluate('(token)=>localStorage.setItem("big-plan-workspace-session",JSON.stringify({accessToken:token,refreshToken:"other-refresh",expiresAt:Date.now()+3600000}))',jwt('other'))
 page.get_by_role('heading',name='Opening your dashboard.').wait_for();assert not page.locator('main').is_visible();assert not page.evaluate('window.loginWasShown')
 page.wait_for_timeout(100);assert state['loads']==2
 fulfill(state['reports'].pop(),report());page.wait_for_function('Cloud.member?.id==="other" && document.body.classList.contains("authenticated")')
 assert page.locator('main').is_visible()
 # Explicit logout in another tab must continue clearing data immediately.
 other.evaluate('localStorage.removeItem("big-plan-workspace-session")');page.locator('#cloud-login-form').wait_for()
 assert page.evaluate('Cloud.member===null && uploads.base===null && uploads.current===null');assert not page.locator('main').is_visible()
 assert not errors,errors;b.close()
 print('PASS account changes require full verification and cross-tab sign-out still clears remembered auth and report data')
server.shutdown()
