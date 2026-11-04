from pathlib import Path
from datetime import datetime,timezone
import http.server,threading,functools
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parent
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
threading.Thread(target=server.serve_forever,daemon=True).start()
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=b.new_page(viewport={'width':1440,'height':1100});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.clock.install(time=datetime(2026,11,5,4,59,50,tzinfo=timezone.utc)) # Nov 4, 11:59:50 PM New York.
 page.goto(f'http://127.0.0.1:{server.server_port}/index.html')
 assert page.evaluate('paceStats(model()).cutoff')=='2026-11-04'
 assert page.locator('#pace-date').count()==0
 assert 'Nov 4, 2026' in page.locator('#pace-today').inner_text()
 page.clock.fast_forward(40000)
 assert page.evaluate('paceStats(model()).cutoff')=='2026-11-05'
 assert 'Nov 5, 2026' in page.locator('#pace-today').inner_text()
 assert page.evaluate('paceStats(model()).previous')=='2025-11-05'
 page.locator('#launch-tv').click();assert page.locator('#tv-pace-date').count()==0
 assert 'Nov 5, 2026' in page.locator('#tv-cutoff').inner_text()
 page.locator('#tv-fullscreen').uncheck();page.get_by_role('button',name='Start slideshow').click()
 page.evaluate('tvIndex=2;tvPaused=true;tvPaint();tvSchedule()')
 assert 'Nov 5, 2026' in page.locator('#tv-content').inner_text()
 page.clock.set_system_time(datetime(2026,11,6,5,0,1,tzinfo=timezone.utc));page.clock.fast_forward(30001)
 assert 'Nov 6, 2026' in page.locator('#tv-content').inner_text()
 page.locator('#tv-exit').click()
 print('New York calendar day, no editable cutoff, automatic overnight dashboard/TV refresh, same date last year: passed')
 page.evaluate('''()=>{
 const r=(g,e,l)=>({group:g,email:e,name:'Example Employee',phone:'202-555-0100',lives:l,status:'ENROLLED',state:'NY',carrier:'Aetna',effective:'01/01/2026',termination:'',consent:'11/01/2025'});
 uploads.base=[r('A','a@example.com',2),r('B','b@example.com',3),r('C','deletec@example.com',4)];
 uploads.current=[r('A','a@example.com',3),r('A','new@example.com',5),r('B','b@example.com',3),r('B','c@example.com',4)];
 assignment={A:'Manager A',B:'Manager A',C:'Manager A'};parents={A:'Parent account',B:'Parent account',C:'Parent account'};mode='uploads';filters={manager:'',type:'',state:'',carrier:'',search:''};page='managers';render();
 }''')
 stats=page.evaluate('managerStats(model()).rows[0]')
 assert stats['netLives']==10 and stats['newEnrolleeLives']==9 and stats['livesPerEmployer']==5,stats
 rows=page.locator('#renewal-employer-lives tbody tr');assert rows.count()==2
 a=page.locator('#renewal-employer-lives [data-group=A]').inner_text();assert '5' in a and '+6' in a
 b_row=page.locator('#renewal-employer-lives [data-group=B]').inner_text();assert '4' in b_row and '+4' in b_row
 assert '+5.0' in page.locator('#growth-ranking').inner_text()
 page.locator('#growth-basis').select_option('employees');assert '+5.0' in page.locator('#growth-ranking').inner_text()
 assert page.evaluate('managerStats(model()).rows[0].outstanding.length')==0
 page.locator('#renewal-employer-lives [data-group=A]').click();assert page.locator('.dialog').is_visible();page.locator('#close').click()
 print('Per-employer gross new-enrollee lives, net changes, average net lives, family-size changes, cross-employer moves and drill-down: passed')
 page.set_viewport_size({'width':390,'height':844});assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
 page.reload();page.set_viewport_size({'width':1440,'height':1100});page.locator('[data-page=managers]').click();page.locator('#renewal-employer-lives').wait_for();page.evaluate('scrollTo(0,0)');page.screenshot(path=str(ROOT/'managers-preview.png'),full_page=True,animations='disabled')
 assert not errors,errors;print('Responsive manager page and no browser errors: passed');b.close()
