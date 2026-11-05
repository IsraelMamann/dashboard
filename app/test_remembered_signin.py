"""Remember a browser across tab closure/restart, without persisting report rows."""
from pathlib import Path
import functools,http.server,json,tempfile,threading
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parent.parent/'deployment/workspace'
class QuietHandler(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
 def do_GET(self):
  if self.path.split('?')[0]=='/config.js':
   body=b'window.BIG_PLAN_CONFIG={supabaseUrl:"https://abcdefghijklmnopqrst.supabase.co",publishableKey:"sb_publishable_test"}'
   self.send_response(200);self.send_header('Content-Type','application/javascript');self.end_headers();self.wfile.write(body);return
  super().do_GET()
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(QuietHandler,directory=str(root)))
threading.Thread(target=server.serve_forever,daemon=True).start()
url=f'http://127.0.0.1:{server.server_port}/index.html'
api='https://abcdefghijklmnopqrst.supabase.co'
state={'emails':0,'refreshes':0,'outage':False,'reject_refresh':False,'held':None,'hold_refresh':False}
errors=[]
def handle(route):
 request=route.request;path=request.url;args=request.post_data_json if request.method=='POST' else {}
 headers={'Content-Type':'application/json','Access-Control-Allow-Origin':'*','Access-Control-Allow-Headers':'apikey,authorization,content-type','Access-Control-Allow-Methods':'POST,GET,OPTIONS'}
 if request.method=='OPTIONS':route.fulfill(status=204,headers=headers);return
 status=200
 if '/auth/v1/otp' in path:state['emails']+=1;result={}
 elif '/auth/v1/verify' in path:result={'access_token':'test-access','refresh_token':'test-refresh','expires_in':3600}
 elif '/auth/v1/token' in path:
  if state['hold_refresh']:state['held']=(route,headers);return
  state['refreshes']+=1
  if state['reject_refresh']:status=400;result={'msg':'Refresh token has been revoked'}
  else:result={'access_token':f'access-{state["refreshes"]}','refresh_token':f'refresh-{state["refreshes"]}','expires_in':3600}
 elif '/auth/v1/user' in path:
  if state['outage']:status=503;result={'msg':'Temporarily unavailable'}
  else:result={'email':'viewer@thebigplan.com'}
 elif '/auth/v1/logout' in path:result={}
 elif path.endswith('/load_dashboard'):
  result={'baseline':[],'current':[],'history':[],'assignments':{},'parents':{},'nonRenewals':{},'member':{'id':'viewer','email':'viewer@thebigplan.com','role':'viewer'},'members':[],'invitations':[],'revision':1}
 elif path.endswith('/dashboard_revision'):result={'revision':1,'role':'viewer'}
 else:raise AssertionError('Unexpected API endpoint')
 route.fulfill(status=status,headers=headers,body=json.dumps(result))
def context(browser_api,profile):
 c=browser_api.launch_persistent_context(profile,executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
 c.route('**/config.js*',lambda route:route.fulfill(content_type='application/javascript',body=f'window.BIG_PLAN_CONFIG={{supabaseUrl:"{api}",publishableKey:"sb_publishable_test"}}'))
 c.route(api+'/**',handle)
 c.on('page',lambda page:page.on('pageerror',lambda e:errors.append(str(e))))
 for extra in c.pages[1:]:extra.close()
 return c
key='big-plan-workspace-session'
with tempfile.TemporaryDirectory(prefix='dashboard-remember-') as profile,sync_playwright() as p:
 c=context(p.chromium,profile);page=c.pages[0];page.goto(url);page.locator('#cloud-email').fill('viewer@thebigplan.com');page.locator('#cloud-login-form button').click();page.locator('#cloud-code').fill('123456');page.locator('#cloud-verify-form button').click();page.locator('#cloud-signout').wait_for()
 assert page.evaluate('Object.keys(JSON.parse(localStorage.getItem(SESSION_KEY))).sort()')==['accessToken','expiresAt','refreshToken']
 assert page.evaluate('sessionStorage.getItem(SESSION_KEY)') is None
 # A newly opened tab has none of the old tab's sessionStorage.
 page.close();page=c.new_page();page.goto(url);page.locator('#cloud-signout').wait_for();assert state['emails']==1
 page.goto('about:blank');c.close()
 # An actual browser process restart retains auth, but still fetches/validates identity.
 c=context(p.chromium,profile);page=c.pages[0];page.goto(url);page.locator('#cloud-signout').wait_for();assert state['emails']==1
 print('PASS remembered browser survives closing the last tab and restarting Chromium, with no new email; report rows are not stored locally')
 # Existing tab-only sessions migrate without a new sign-in email.
 page.evaluate('sessionStorage.setItem(SESSION_KEY,localStorage.getItem(SESSION_KEY));localStorage.removeItem(SESSION_KEY)')
 page.reload();page.locator('#cloud-signout').wait_for();assert page.evaluate('localStorage.getItem(SESSION_KEY)!==null && sessionStorage.getItem(SESSION_KEY)===null');assert state['emails']==1
 # Expired access is renewed automatically and persisted.
 page.evaluate('const s=JSON.parse(localStorage.getItem(SESSION_KEY));s.expiresAt=Date.now()-1000;localStorage.setItem(SESSION_KEY,JSON.stringify(s))')
 page.reload();page.locator('#cloud-signout').wait_for()
 assert state['refreshes']==1;assert page.evaluate('Cloud.session.refreshToken')=='refresh-1'
 # Two tabs contend for one rotating refresh token: the second reuses the saved replacement.
 other=c.new_page();other.goto(url);other.locator('#cloud-signout').wait_for()
 page.evaluate('()=>{const s=JSON.parse(localStorage.getItem(SESSION_KEY));s.expiresAt=Date.now()-1000;localStorage.setItem(SESSION_KEY,JSON.stringify(s));window.refreshResult=Cloud.freshToken()}')
 other.evaluate('()=>{window.refreshResult=Cloud.freshToken()}')
 assert page.evaluate('window.refreshResult')=='access-2';assert other.evaluate('window.refreshResult')=='access-2';assert state['refreshes']==2
 other.close()
 print('PASS legacy sessions migrate, expired access renews silently and concurrent tabs share one token refresh')
 # A temporary server outage should not discard the remembered session.
 state['outage']=True;page.reload();page.get_by_text('Could not reconnect.',exact=False).wait_for();assert page.evaluate('localStorage.getItem(SESSION_KEY)') is not None;assert not page.locator('main').is_visible()
 state['outage']=False;page.reload();page.locator('#cloud-signout').wait_for();assert state['emails']==1
 # Explicit logout clears every tab and prevents a fresh tab from auto-signing in.
 other=c.new_page();other.goto(url);other.locator('#cloud-signout').wait_for();page.locator('#cloud-signout').click();page.locator('#cloud-login-form').wait_for();other.locator('#cloud-login-form').wait_for()
 assert other.evaluate('localStorage.getItem(SESSION_KEY)===null && sessionStorage.getItem(SESSION_KEY)===null && Cloud.member===null')
 other.reload();other.locator('#cloud-login-form').wait_for();assert not other.locator('main').is_visible();other.close()
 print('PASS a transient outage preserves remembered auth, while explicit sign-out clears all tabs and prevents automatic reentry')
 # A late refresh must not restore a session after the user signs out.
 page.evaluate('Cloud.acceptSession({access_token:"test-access",refresh_token:"test-refresh",expires_in:3600})');page.reload();page.locator('#cloud-signout').wait_for()
 state['hold_refresh']=True
 page.evaluate('()=>{const s=JSON.parse(localStorage.getItem(SESSION_KEY));s.expiresAt=Date.now()-1000;localStorage.setItem(SESSION_KEY,JSON.stringify(s));window.pendingRefresh=Cloud.freshToken().catch(e=>e.message)}')
 page.wait_for_timeout(100);assert state['held'] is not None
 page.locator('#cloud-signout').click();route,headers=state['held'];route.fulfill(status=200,headers=headers,body=json.dumps({'access_token':'late-token','refresh_token':'late-refresh','expires_in':3600}));page.evaluate('window.pendingRefresh')
 assert page.evaluate('localStorage.getItem(SESSION_KEY)===null && Cloud.session===null')
 state['hold_refresh']=False
 # Revoked server sessions still require verification.
 page.evaluate('Cloud.acceptSession({access_token:"expired",refresh_token:"revoked",expires_in:-1})');state['reject_refresh']=True;page.reload();page.locator('#cloud-login-form').wait_for();assert page.evaluate('localStorage.getItem(SESSION_KEY)') is None
 assert not page.locator('main').is_visible();assert not errors,errors;c.close()
 print('PASS revoked sessions are denied and a refresh completing after sign-out cannot restore access')
server.shutdown()
