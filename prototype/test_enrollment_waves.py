"""Fixed renewal wave cohorts, employee-return denominators and filtered chart behavior."""
from pathlib import Path
from datetime import datetime,timezone
import functools,http.server,threading
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]/'app'
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(root)));threading.Thread(target=server.serve_forever,daemon=True).start()
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=b.new_page(viewport={'width':1440,'height':1100});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.clock.install(time=datetime(2026,11,24,17,tzinfo=timezone.utc));page.goto(f'http://127.0.0.1:{server.server_port}/core.html')
 page.evaluate('''()=>{
 const row=(group,email,consent='',status='ENROLLED',state='NY')=>({group,email,name:'PRIVATE EMPLOYEE',phone:'PRIVATE PHONE',lives:3,consent,status,state,carrier:'Example',effective:'01/01/2026',termination:status==='TERMINATED'?'12/01/2026':''});
 uploads.base=[...['a1','a2','deletea3','a4'].map(e=>row('A',e+'@example.test')),...['b1','b2','b3'].map(e=>row('B',e+'@example.test')),row('C','c1@example.test'),row('D','d1@example.test'),row('D','d2@example.test'),row('T','t1@example.test'),row('U','u1@example.test'),row('U','u2@example.test'),row('Future','f1@example.test'),row('Leaving','l1@example.test'),row('Not Started','q1@example.test'),row('Zero Baseline','r-old@example.test','','TERMINATED')];
 uploads.current=[row('A','a1@example.test','11/17/2026','APPLICATION_READY','TX'),row('A','new-a@example.test','11/18/2026','STUCK'),row('A','first-consent@example.test','11/15/2026 11:59:59 PM','TERMINATED'),row('New Group','a2@example.test','11/16/2026'),row('New Group','new@example.test','11/14/2026'),row('B','b1@example.test','11/16/2026 12:00:00 AM','PAYMENT_READY'),row('B','b2@example.test','11/17/2026'),row('C','c1@example.test','11/22/2026 11:59:59 PM'),row('D','d1@example.test','11/23/2026 12:00:00 AM'),row('T','t1@example.test','11/15/2026','TERMINATED'),row('U','u1@example.test','bad-date'),row('Future','f1@example.test','12/01/2026'),row('Leaving','l1@example.test','11/14/2026'),row('Zero Baseline','r-new@example.test','11/16/2026'),row('Not Started','q1@example.test','11/16/2026','APPLICATION_STARTED')].map(r=>({...r,effective:'01/01/2027'}));
 mode='uploads';filters={};nonRenewals={Leaving:true};parents={A:'Shared Parent',B:'Shared Parent'};assignment={A:'Jordan',T:'Jordan',U:'Jordan',B:'Taylor',C:'Taylor','Zero Baseline':'Taylor',D:'Zoe',Future:'Zoe'};page='overview';render();
 }''')
 def stats():return page.evaluate('renewalWaveStats(model()).map(w=>({key:w.key,groups:w.groups,prior:w.prior.length,returned:w.returned.length,outstanding:w.outstanding.length,added:w.added.length,start:w.start,end:w.end}))')
 waves=stats();assert [w['key'] for w in waves]==['1','2','3','unassigned'],waves
 assert waves[0]=={'key':'1','groups':['A','T'],'prior':5,'returned':2,'outstanding':3,'added':1,'start':None,'end':'2026-11-15'},waves[0]
 assert waves[1]=={'key':'2','groups':['B','C','Zero Baseline'],'prior':4,'returned':3,'outstanding':1,'added':1,'start':'2026-11-16','end':'2026-11-22'},waves[1]
 assert waves[2]['prior']==2 and waves[2]['returned']==1 and waves[2]['outstanding']==1
 assert waves[3]['groups']==['Future','U'] and waves[3]['prior']==3 and waves[3]['returned']==2
 assert page.locator('#renewal-wave-1 .enrollment-donut-number').text_content()=='40.0%';assert page.locator('#renewal-wave-2 .enrollment-donut-number').text_content()=='75.0%'
 assert page.locator('#renewal-wave-1 .enrollment-donut-value b').all_inner_texts()==['2','3'];assert page.locator('#renewal-wave-1 .enrollment-donut-value small').all_inner_texts()==['40.0%','60.0%']
 assert page.evaluate('document.querySelector("#renewal-wave-progress").previousElementSibling.id')=='enrollment-progress-charts'
 assert page.evaluate('document.querySelector("#renewal-wave-progress").nextElementSibling.id')=='pace-comparison'
 text=page.locator('#renewal-wave-progress').inner_text();assert '@example.test' not in text and 'PRIVATE' not in text
 assert 'Not Started' not in text and 'New Group' not in text and 'Leaving' not in text
 page.locator('#renewal-wave-1 summary').click();assert page.locator('#renewal-wave-1 details li').all_inner_texts()==['A · Jordan','T · Jordan']
 # A former enrollee keeps the original start date; filter changes do not move groups to a later wave.
 page.locator('[data-filter=state]').select_option('TX');waves=stats();assert len(waves)==1 and waves[0]['key']=='1' and waves[0]['groups']==['A'];assert waves[0]['prior']==1 and waves[0]['returned']==1
 page.locator('#reset').click();page.locator('[data-filter=manager]').select_option('Taylor');waves=stats();assert len(waves)==1 and waves[0]['key']=='2' and waves[0]['groups']==['B','C','Zero Baseline']
 page.locator('#reset').click();page.locator('[data-filter=parent]').select_option('Shared Parent');assert [w['groups'] for w in stats()]==[['A'],['B']]
 page.locator('#reset').click();page.locator('[data-filter=type]').select_option('New');assert page.locator('.renewal-wave-card').count()==0;assert 'renewal groups only' in page.locator('#renewal-wave-progress').inner_text()
 page.locator('#reset').click();page.locator('[data-filter=renewalDecision]').select_option('excluded');assert page.locator('.renewal-wave-card').count()==0;page.locator('#reset').click()
 # Later enrollments improve the original wave, rather than creating or moving its cohort.
 page.evaluate("uploads.current.push({...uploads.current[0],email:'a3@example.test',consent:'11/24/2026',state:'NY'});render()")
 assert stats()[0]['returned']==3 and stats()[0]['groups']==['A','T'];assert page.locator('#renewal-wave-1 .enrollment-donut-number').text_content()=='60.0%'
 for day,key in [('2026-11-15','1'),('2026-11-16','2'),('2026-11-22','2'),('2026-11-23','3'),('2026-11-29','3'),('2026-11-30','4'),('2026-12-06','4'),('2026-12-07','5')]:assert page.evaluate('(day)=>renewalWavePeriod(day).key',day)==key
 page.clock.set_system_time(datetime(2026,12,2,17,tzinfo=timezone.utc));page.evaluate('refreshForNewDay()');assert stats()[0]['end']=='2026-11-15';assert [w['key'] for w in stats()]==['1','2','3','4','unassigned']
 page.locator('#renewal-wave-progress').screenshot(path='/tmp/renewal-waves.png')
 for width in [1920,1280,768,390]:
  page.set_viewport_size({'width':width,'height':1000});assert not page.evaluate('document.documentElement.scrollWidth>innerWidth'),width
  assert not page.locator('#renewal-wave-progress .enrollment-donut-legend').evaluate_all('(els)=>els.some(e=>e.scrollWidth>e.clientWidth+1)'),width
 page.evaluate('uploads.current=null;render()');assert page.locator('.renewal-wave-card').count()==0;assert 'Upload the baseline and current reports' in page.locator('#renewal-wave-progress').inner_text()
 page.evaluate('uploads.current=[];render()');assert page.locator('.renewal-wave-card').count()==0
 page.evaluate("uploads.current=[{...uploads.base[0],group:'Zero Baseline',email:'r-new@example.test',consent:'11/16/2026',effective:'01/01/2027'}];render()")
 assert page.locator('#renewal-wave-2 svg').count()==0;assert 'percentage is unavailable' in page.locator('#renewal-wave-2').inner_text()
 assert not errors,errors;b.close()
server.shutdown()
print('PASS fixed weekly waves, Sunday/Monday boundaries, cumulative reenrollment, transfers, former enrollee dates, new-group/nonrenewal exclusions, unassigned dates, filters, group lists, placement, zero-baseline and responsive layouts.')
