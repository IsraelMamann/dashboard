"""Screen Wake Lock lifecycle, including browser refusal and late async results."""
from pathlib import Path
import functools,http.server,json,threading
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]/'app'
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(root)))
threading.Thread(target=server.serve_forever,daemon=True).start()
url=f'http://127.0.0.1:{server.server_port}/core.html'
mock='''()=>{
 window.fakeWake={calls:0,releases:0,locks:[],waiting:[],hidden:false,hold:false,deny:false};
 Object.defineProperty(document,'hidden',{configurable:true,get:()=>fakeWake.hidden});
 class Lock extends EventTarget{
  constructor(){super();this.released=false}
  release(){if(!this.released){this.released=true;fakeWake.releases++;this.dispatchEvent(new Event('release'))}return Promise.resolve()}
 }
 Object.defineProperty(navigator,'wakeLock',{configurable:true,value:{request:async(type)=>{
  fakeWake.calls++;fakeWake.type=type;
  if(fakeWake.deny)throw new DOMException('Blocked by device','NotAllowedError');
  const lock=new Lock();fakeWake.locks.push(lock);
  if(fakeWake.hold)return new Promise(resolve=>fakeWake.waiting.push(()=>resolve(lock)));
  return lock;
 }}});
}'''
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);errors=[]
 def new_page():
  page=b.new_page(viewport={'width':1280,'height':720});page.on('pageerror',lambda e:errors.append(str(e)));page.add_init_script('('+mock+')()');page.goto(url);page.clock.install();return page
 def start(page):
  page.locator('#launch-tv').click();page.locator('#tv-fullscreen').uncheck();page.locator('#tv-start').click();assert page.locator('#tv-screen').is_visible()
 page=new_page();start(page);page.get_by_text('Screen awake',exact=True).wait_for()
 assert page.evaluate('fakeWake.calls===1 && fakeWake.type==="screen"')
 # Several full rotations must keep the original screen lock, even when paused.
 for _ in range(page.evaluate('tvTypes.length')*3):page.clock.fast_forward(15001)
 assert page.evaluate('fakeWake.calls===1 && !fakeWake.locks[0].released')
 page.locator('#tv-pause').click();assert page.evaluate('tvPaused && !fakeWake.locks[0].released')
 page.locator('#tv-pause').click()
 # Browser/OS drops a lock while visible: make one delayed attempt to reacquire.
 page.evaluate('fakeWake.locks[0].release()');page.get_by_text('Reconnecting keep-awake…',exact=True).wait_for();page.clock.fast_forward(5001)
 page.get_by_text('Screen awake',exact=True).wait_for();assert page.evaluate('fakeWake.calls===2 && !fakeWake.locks[1].released')
 # Background tabs cannot hold screen locks; restore automatically when visible again.
 page.evaluate('fakeWake.hidden=true;document.dispatchEvent(new Event("visibilitychange"))')
 assert page.evaluate('fakeWake.locks[1].released')
 page.evaluate('fakeWake.hidden=false;document.dispatchEvent(new Event("visibilitychange"))');page.get_by_text('Screen awake',exact=True).wait_for();assert page.evaluate('fakeWake.calls')==3
 page.locator('#tv-exit').click();assert page.evaluate('fakeWake.locks[2].released && tvWakeLock===null && tvWakeRetry===null');page.clock.fast_forward(10001);assert page.evaluate('fakeWake.calls')==3
 page.close();print('PASS screen stays requested over repeated slideshow rounds and pause; visible releases retry, tab return reacquires, and exit releases/cleans up')
 # A browser without the API should still run every slide and show actionable feedback.
 page=new_page();page.evaluate('Object.defineProperty(navigator,"wakeLock",{configurable:true,value:undefined})');start(page);page.get_by_text('Keep-awake unavailable',exact=True).wait_for();page.clock.fast_forward(15001);assert page.evaluate('tvActive && tvIndex===1');page.locator('#tv-exit').click();page.close()
 # A policy or device refusal must not interrupt the slideshow or create a retry loop.
 page=new_page();page.evaluate('fakeWake.deny=true');start(page);page.get_by_text('Keep-awake unavailable',exact=True).wait_for();page.clock.fast_forward(60001);assert page.evaluate('tvActive && fakeWake.calls===1');page.locator('#tv-exit').click();page.close()
 print('PASS unsupported and denied keep-awake requests leave the slideshow running with a clear status and no request loop')
 # Exiting before a browser request finishes must not leak a screen lock.
 page=new_page();page.evaluate('fakeWake.hold=true');start(page);page.wait_for_function('fakeWake.waiting.length===1');page.locator('#tv-exit').click();page.evaluate('fakeWake.waiting.shift()()');page.wait_for_function('fakeWake.locks[0].released');assert page.evaluate('tvWakeLock===null && !tvActive');page.close()
 # Rapid restart: an old pending request is released without clearing the new lock.
 page=new_page();page.evaluate('fakeWake.hold=true');start(page);page.wait_for_function('fakeWake.waiting.length===1');page.locator('#tv-exit').click();page.evaluate('fakeWake.hold=false');start(page);page.get_by_text('Screen awake',exact=True).wait_for();page.evaluate('fakeWake.waiting.shift()()');page.wait_for_function('fakeWake.locks[0].released');assert page.evaluate('!fakeWake.locks[1].released && tvWakeLock===fakeWake.locks[1]');page.locator('#tv-exit').click();assert page.evaluate('fakeWake.locks[1].released');page.close()
 assert not errors,errors;b.close();print('PASS exit and rapid restart safely release late requests without leaking or cancelling the current screen lock')
server.shutdown()
