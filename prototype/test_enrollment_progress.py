"""Progress charts use baseline cohorts, never an invented eligibility denominator."""
from pathlib import Path
import functools,http.server,threading
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]/'app'
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(root)))
threading.Thread(target=server.serve_forever,daemon=True).start()
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=b.new_page(viewport={'width':1440,'height':1100});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(f'http://127.0.0.1:{server.server_port}/core.html')
 page.evaluate('''()=>{
 const row=(group,email,lives=2,status='ENROLLED')=>({group,email,name:'Example Employee',status,lives,state:'NY',carrier:'Example',effective:'01/01/2026',termination:'',consent:'11/01/2025'});
 uploads.base=[row('A','a1@example.test'),row('A','a2@example.test'),row('A','deletea3@example.test'),row('B','b1@example.test',1),row('C','c1@example.test',8),{...row('D','d1@example.test',2,'TERMINATED'),termination:'03/01/2026'},{...row('E','e-old@example.test',1,'TERMINATED'),termination:'05/01/2026'}];
 uploads.current=[row('A','a1@example.test'),row('A','a4@example.test',4,'APPLICATION_READY'),row('A','a5@example.test',2,'PAYMENT_READY'),row('New','a3@example.test',3),row('New','n1@example.test',4,'STUCK'),row('C','c1@example.test',8),row('E','e-new@example.test',1),row('A','ignored@example.test',99,'TERMINATED')].map(r=>({...r,effective:'01/01/2027'}));
 mode='uploads';filters={};nonRenewals={C:true};assignment={A:'Jordan',E:'Jordan',B:'Taylor',C:'Taylor',New:'Taylor'};parents={A:'Parent Example',E:'Parent Example'};page='overview';render();
 }''')
 stats=page.evaluate('(()=>{const s=enrollmentProgressStats(model());return {groups:s.groups.length,started:s.started.length,waiting:s.notStarted.length,notRenewing:s.notRenewing.length,prior:s.prior.length,returned:s.returned.length,outstanding:s.outstanding.length,added:s.added.length,addedLives:lives(s.added),newGroups:s.newGroups}})()')
 assert stats=={'groups':4,'started':2,'waiting':1,'notRenewing':1,'prior':3,'returned':2,'outstanding':1,'added':3,'addedLives':7,'newGroups':1},stats
 assert page.evaluate('document.querySelector(".enrollment-charts").previousElementSibling.classList.contains("cards")')
 assert page.locator('#renewal-group-progress .enrollment-donut-value b').all_inner_texts()==['2','1','1']
 assert page.locator('#renewal-group-progress .enrollment-donut-value small').all_inner_texts()==['50.0%','25.0%','25.0%']
 assert page.locator('#renewal-employee-progress .enrollment-donut-value b').all_inner_texts()==['2','1']
 assert page.locator('#renewal-employee-progress .enrollment-donut-number').text_content()=='66.7%'
 assert '3 employees / 7 lives' in page.locator('#renewal-employee-progress').inner_text()
 assert '@example.test' not in page.locator('.enrollment-charts').inner_text()
 assert 'Returned: 2 (66.7%)' in page.locator('#renewal-employees-desc').text_content()
 # The group comparison intentionally uses active baseline rows, not the Jan 1 cohort.
 assert page.evaluate('model().active.length')==5;assert page.evaluate('model().bench.length')==7
 assert page.locator('.annual-comparison tbody tr').first.locator('td').nth(1).inner_text()=='7'
 row=page.locator('[data-parent="Parent Example"]')
 assert row.locator('td').all_inner_texts()[2:5]==['3 / 6','1 / 2','3 / 7']
 assert row.locator('.enrolled-count').all_inner_texts()==['3','1','3']
 row.click();assert page.locator('.dialog [data-group="A"] td').all_inner_texts()[3:]==['3 / 6','1 / 2','2 / 6'];page.locator('#close').click()
 page.evaluate("page='groups';accountView='child';render()")
 assert page.locator('#app [data-group="A"] td').all_inner_texts()[2:5]==['3 / 6','1 / 2','2 / 6']
 page.evaluate("page='overview';render()")
 page.locator('[data-filter=manager]').select_option('Jordan')
 assert page.locator('#renewal-group-progress .enrollment-donut-value b').all_inner_texts()==['2','0','0']
 assert page.locator('#renewal-employee-progress .enrollment-donut-value b').all_inner_texts()==['2','1'],'A transfer to another manager still counts as returned company-wide'
 page.locator('#reset').click()
 for width,height in [(1920,1080),(1280,900),(768,1000),(390,844)]:
  page.set_viewport_size({'width':width,'height':height});assert not page.evaluate('document.documentElement.scrollWidth>innerWidth'),width
  assert not page.locator('.enrollment-donut-legend').evaluate_all('(nodes)=>nodes.some(e=>e.scrollWidth>e.clientWidth+1)'),width
 page.locator('[data-filter=type]').select_option('New');assert page.locator('.enrollment-charts svg').count()==0;assert '1 new group with enrollment' in page.locator('#renewal-group-progress').inner_text()
 page.locator('#reset').click();page.locator('[data-filter=renewalDecision]').select_option('excluded');assert page.locator('#renewal-group-progress .enrollment-donut-value b').all_inner_texts()==['0','0','1'];assert page.locator('#renewal-employee-progress svg').count()==0
 page.locator('#reset').click()
 page.evaluate('uploads.current=null;render()');assert page.locator('.enrollment-charts svg').count()==0;assert 'Upload the baseline and current reports' in page.locator('.enrollment-charts').inner_text()
 page.evaluate('uploads.current=[];render()');assert page.locator('#renewal-group-progress .enrollment-donut-value b').all_inner_texts()==['0','2','1'];assert page.locator('#renewal-employee-progress svg').count()==0
 assert 'NaN' not in page.locator('.enrollment-charts').inner_text();assert not errors,errors;b.close()
print('PASS group activity, started-group return denominator, new enrollments kept separate, transfers, nonrenewals, Jan 1 vs active baseline distinction, compact employee/life cells, filters and responsive/empty states')
server.shutdown()
