from datetime import datetime, timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parent
import http.server,threading,functools
from playwright.sync_api import sync_playwright
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
threading.Thread(target=server.serve_forever,daemon=True).start()
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=b.new_page(viewport={'width':1440,'height':1100});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.clock.install(time=datetime(2026,11,4,17,tzinfo=timezone.utc));page.goto(f'http://127.0.0.1:{server.server_port}/index.html');page.locator('#pace-comparison').wait_for()
 page.evaluate('''()=>{
 const r=(group,email,lives,consent,status='ENROLLED')=>({group,email,lives,consent,status,name:'Test Employee',phone:'202-555-0100',state:'NY',carrier:'Aetna',effective:'01/01/2026',termination:status==='TERMINATED'?'08/01/2026':''});
 uploads.base=[r('A','deletea@example.com',1000,'11/04/2025 11:59:59 PM'),r('B','b@example.com',600,'11/05/2025 12:00:00 AM'),r('C','c@example.com',100,''),r('A','d@example.com',50,'10/15/2025 1:00:00 PM','TERMINATED')];
 uploads.current=[r('A','a@example.com',1400,'11/04/2026 11:59:59 PM','PAYMENT_READY'),r('B','b@example.com',1000,'11/05/2026 12:00:00 AM','APPLICATION_READY'),r('New','new@example.com',200,'11/01/2026 1:00:00 PM','STUCK')];
 assignment={A:'Manager A',B:'Manager B',C:'Manager A',New:'Manager B'};mode='uploads';filters={manager:'',type:'',state:'',carrier:'',search:''};growthBasis='lives';render();
 }''')
 stats=page.evaluate('''()=>{let m=model(),s=managerStats(m),p=paceStats(m);return {den:s.denominator,weighted:s.rows.filter(r=>r.gs.size).map(r=>r.weighted),own:s.rows.filter(r=>r.gs.size).map(r=>growth(r.current,r.starting)),missing:s.rows.find(r=>r.name==='Manager A').outstanding.length,prior:p.baseline,current:p.current,fullPrior:m.bench.length,fullCurrent:m.now.length}}''')
 assert stats['den']==1600,stats
 assert stats['weighted']==[.25,.25],stats
 assert stats['own']==['40.0%','66.7%'],stats
 assert stats['missing']==1
 assert stats['prior']['employees']==2 and stats['prior']['lives']==1050 and stats['prior']['missing']==1,stats
 assert stats['current']['employees']==2 and stats['current']['lives']==1600,stats
 assert stats['fullPrior']==4 and stats['fullCurrent']==3
 print('Weighted/unweighted example, all-groups retention, January terminated baseline, full-company comparison, end-of-day consent cutoffs: passed')
 assert page.locator('#pace-date').count()==0
 page.clock.set_system_time(datetime(2026,11,5,17,tzinfo=timezone.utc));page.evaluate('refreshForNewDay()')
 assert page.evaluate('paceStats(model()).baseline.employees')==3
 assert page.evaluate('paceStats(model()).current.employees')==3
 assert page.evaluate('priorCutoff("2028-02-29")')=='2027-02-28'
 assert page.evaluate('consentDay("02/30/2026")') is None
 assert page.evaluate('consentDay("2026-11-04T23:59:59Z")')=='2026-11-04'
 print('Automatic today cutoff, next-day refresh, leap-day alignment, ISO/US timestamps and invalid dates: passed')
 page.locator('[data-page="managers"]').click();page.locator('#growth-ranking').wait_for()
 assert '25.00%' in page.locator('#growth-ranking').inner_text()
 page.locator('[data-filter="manager"]').select_option('Manager A')
 assert page.evaluate('managerStats(model()).denominator')==1600
 assert '25.00%' in page.locator('#growth-ranking').inner_text()
 page.locator('[data-followup="Manager A"]').click();assert page.locator('.dialog tbody tr').count()==1
 assert 'c@example.com' in page.locator('.dialog').inner_text()
 page.locator('#close').click()
 page.evaluate('uploads.current[0].group="B"; filters.manager=""; render()')
 assert page.evaluate('managerStats(model()).rows.find(r=>r.name==="Manager A").outstanding.length')==1
 print('Stable denominator under manager filter, employee follow-up, cross-group retention: passed')
 page.evaluate('uploads.base.forEach(r=>r.consent="");page="overview";render()')
 assert page.locator('#pace-comparison').get_by_text('Unavailable',exact=True).count()==2
 page.reload();page.locator('#pace-comparison').wait_for();page.evaluate('window.scrollTo(0,0)')
 page.screenshot(path=str(ROOT/'preview.png'),full_page=True,animations='disabled')
 page.locator('[data-page="managers"]').click();page.locator('#growth-ranking tbody tr').first.wait_for();page.evaluate('window.scrollTo(0,0)');page.screenshot(path=str(ROOT/'managers-preview.png'),full_page=True,animations='disabled')
 page.set_viewport_size({'width':390,'height':844});assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
 page.locator('[data-page="overview"]').click();page.locator('#pace-comparison').wait_for();assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
 assert not errors,errors
 print('Missing consent exclusion, both responsive layouts, no browser errors: passed');b.close()
