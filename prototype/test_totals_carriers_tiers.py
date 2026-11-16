"""Filtered list totals, carrier ranking and end-of-year metal-tier cohorts."""
from pathlib import Path
import functools,http.server,threading,math
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
 const row=(group,email,lives,carrier,tier,premium=500,state='NY',status='ENROLLED')=>({group,email,name:'Example',status,lives,carrier,tier,fullPremium:premium,erAllowance:100,age:40,state,effective:'01/01/2026',termination:'',consent:''});
 uploads.base=[row('Employer A','a1@example.test',2,'Zeta','silver',500),row('Employer A','a2@example.test',3,'Zeta','bronze',600),row('Employer B','b1@example.test',1,'Beta','gold',700,'TX'),row('Leaving One','c1@example.test',4,'Zeta','silver',800),row('Leaving Two','c2@example.test',6,'Beta','gold',900),{...row('Leaving One','terminated@example.test',9,'Alpha','platinum',10000,'NY','TERMINATED'),termination:'08/01/2026'}];
 uploads.current=[row('Employer A','a1@example.test',3,'Zeta','gold'),row('Employer A','new-a@example.test',4,'Zeta','gold',500,'TX','APPLICATION_READY'),row('Employer B','b1@example.test',2,'Zeta','silver',500,'TX'),row('Employer B','new-b@example.test',5,'Beta','silver',500,'NY','PAYMENT_READY'),row('Leaving One','c1@example.test',7,'Beta','bronze',500,'NY','STUCK'),row('New Group','new@example.test',6,'Alpha','gold')].map(r=>({...r,effective:'01/01/2027'}));
 mode='uploads';page='managers';filters={};assignment={'Employer A':'Jordan','Employer B':'Jordan','Leaving One':'Taylor','Leaving Two':'Taylor','New Group':'Taylor'};parents={'Employer A':'Shared Parent','Employer B':'Shared Parent'};nonRenewals={'Leaving One':true,'Leaving Two':true};render();
 }''')
 cells=page.locator('#nonrenewal-accounts tfoot td').all_inner_texts();assert cells==['2 employees\n10 lives','1 employee\n7 lives'],cells
 assert 'Total · 2 groups' in page.locator('#nonrenewal-accounts tfoot').inner_text()
 cells=page.locator('#renewal-employer-lives tfoot td').all_inner_texts();assert cells==['3 employees\n6 lives','4 employees\n14 lives','2 employees\n9 lives','+8'],cells
 assert 'Total · 2 groups' in page.locator('#renewal-employer-lives tfoot').inner_text()
 page.locator('[data-filter=manager]').select_option('Jordan');assert 'Total · 0 groups' in page.locator('#nonrenewal-accounts tfoot').inner_text();assert page.locator('#renewal-employer-lives tfoot td').all_inner_texts()==['3 employees\n6 lives','4 employees\n14 lives','2 employees\n9 lives','+8']
 page.locator('#reset').click();page.locator('[data-page=groups]').click()
 assert 'Total · 4 groups' in page.locator('#app tfoot').inner_text(),'Parent rows must count employer locations, not parent names'
 assert '2027 total: 6 employees 27 lives' in ' '.join(page.locator('#app tfoot').inner_text().split())
 assert page.locator('#app tfoot td').all_inner_texts()==['4 employees\n10 lives','3 employees\n12 lives','3 employees\n15 lives','25.0%','110.0%']
 page.locator('[data-parent="Shared Parent"]').click();assert 'Total · 2 groups' in page.locator('.dialog tfoot').inner_text();assert page.locator('.dialog tfoot td').all_inner_texts()==['3 employees\n6 lives','2 employees\n5 lives','2 employees\n9 lives'];assert '2027 total: 4 employees 14 lives' in ' '.join(page.locator('.dialog tfoot').inner_text().split());page.locator('#close').click()
 page.locator('#account-view').select_option('child');page.locator('#group-search').fill('Employer A');assert 'Total · 1 group' in page.locator('#app tfoot').inner_text();assert '2027 total: 2 employees 7 lives' in ' '.join(page.locator('#app tfoot').inner_text().split());assert page.locator('#app tfoot td').all_inner_texts()==['2 employees\n5 lives','1 employee\n3 lives','1 employee\n4 lives','0.0%','40.0%']
 page.locator('#reset').click();page.locator('[data-tab=missing]').click();assert 'Total · 1 group' in page.locator('#app tfoot').inner_text();assert page.locator('#app tfoot td').all_inner_texts()==['1 employee\n6 lives','0 employees\n0 lives','0 employees\n0 lives','—','—']
 page.evaluate("groupTab='active';accountView='parent';page='overview';render();document.querySelector('#app').insertAdjacentHTML('beforeend','<div id=limited>'+table(model(),1)+'</div>')")
 assert page.locator('#limited tbody tr').count()==1;assert 'Total · 4 groups' in page.locator('#limited tfoot').inner_text();assert 'beyond this preview' in page.locator('#limited tfoot').inner_text()
 print('PASS renewal/nonrenewal totals, both years, child-location counts, combined current enrollment, weighted total growth, filters, missing groups and limited previews')
 page.evaluate("page='insights';render()")
 page.get_by_text('Carrier retention, movement & state breakdowns',exact=True).click()
 assert page.locator('#carrier-share-table tbody tr td:first-child').all_inner_texts()==['Zeta','Beta','Alpha']
 assert page.locator('#carrier-share-table tbody tr td:nth-child(4)').all_inner_texts()==['3','2','1']
 page.locator('[data-filter=state]').select_option('NY');page.get_by_text('Carrier retention, movement & state breakdowns',exact=True).click();ordered=page.locator('#carrier-share-table tbody tr td:first-child').all_inner_texts();assert ordered==['Beta','Alpha','Zeta'],ordered
 page.locator('#reset').click()
 assert page.evaluate('tierComparison(model()).before.length')==5;assert page.evaluate('funFactStats(model()).before.length')==6
 assert page.evaluate('funFactStats(model()).metrics.find(r=>r.id==="premium").a.value')==2250
 dist=page.evaluate('tierDistribution(tierComparison(model()).before)');counts={r['key']:r['count'] for r in dist};assert counts['silver']==2 and counts['gold']==2 and counts['bronze']==1 and counts['platinum']==0;assert math.isclose(sum(r['percentage'] for r in dist),100)
 assert '2026 end-of-year' in page.locator('#plan-tier-panel').inner_text()
 tier_rows=page.locator('#plan-tier-panel tbody tr');platinum=tier_rows.filter(has=page.get_by_text('Platinum',exact=True));assert platinum.locator('td').all_inner_texts()[1:3]==['0','0.0%']
 page.evaluate("tvPrefs.slides=['tiers'];tvPrefs.fullscreen=false;tvStart()")
 assert '2026 uses active/end-of-year enrollment' in page.locator('#tv-content').inner_text();assert 'January 1 benchmark' not in page.locator('#tv-content').inner_text();page.keyboard.press('Escape')
 page.evaluate('uploads.current=null;render()');assert page.evaluate('carrierShareOrder(model(),[])')==['Zeta','Beta','Alpha']
 page.evaluate("page='groups';render()");assert '2027 total:' not in page.locator('#app tfoot').inner_text();assert page.locator('#app tfoot td').all_inner_texts()[1:]==['—','—','—','—']
 page.set_viewport_size({'width':390,'height':844});assert not page.evaluate('document.documentElement.scrollWidth>innerWidth');assert not errors,errors;b.close()
 print('PASS carrier ordering uses current filtered enrollment, metal tiers use active/end-of-year rows on page and TV, cost averages retain Jan 1, and baseline-only totals stay honest')
server.shutdown()
