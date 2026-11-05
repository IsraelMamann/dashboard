"""Exercise performance exclusions against synthetic employer portfolios."""
from pathlib import Path
import http.server, threading, functools
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]/'app'
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(root)))
threading.Thread(target=server.serve_forever,daemon=True).start()
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
 page=b.new_page(viewport={'width':1440,'height':1100});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(f'http://127.0.0.1:{server.server_port}/core.html')
 page.evaluate('''()=>{
 const row=(group,email,lives=2)=>({group,email,name:email,phone:'',status:'ENROLLED',lives,state:'NY',carrier:'Aetna',effective:'01/01/2026',termination:'',consent:'11/01/2025'});
 uploads.base=[row('Expected A','a@example.com'),row('Leaving B','b@example.com',10),row('Leaving C','c@example.com',20),row('Expected D','d@example.com',4),{...row('Inactive E','e@example.com'),status:'TERMINATED'}];
 uploads.current=[{...uploads.base[0],lives:3},uploads.base[1],{...uploads.base[3],lives:5}].map(r=>({...r,effective:'01/01/2027'}));
 assignment={'Expected A':'Jordan','Leaving B':'Jordan','Leaving C':'Taylor','Expected D':'Taylor','Inactive E':'Taylor'};parents={'Expected A':'Parent','Leaving B':'Parent'};nonRenewals={};mode='uploads';page='admin';render();
 }''')
 page.locator('#employer-settings > summary').click()
 for group in ['Leaving B','Leaving C','Inactive E']:
  page.locator(f'[data-nonrenew="{group}"]').check()
 page.evaluate("page='managers';render()")
 stats=page.evaluate('(()=>{const s=managerStats(model());return {denominator:s.denominator,rows:s.rows.map(r=>({name:r.name,starting:r.starting,current:r.current,delta:r.delta,portfolio:r.portfolio.length,waiting:r.waiting.length}))}})()')
 assert stats=={'denominator':6,'rows':[{'name':'Jordan','starting':2,'current':3,'delta':1,'portfolio':1,'waiting':0},{'name':'Taylor','starting':4,'current':5,'delta':1,'portfolio':1,'waiting':0}]},stats
 assert page.locator('#manager-enrollment-context tbody tr').all_inner_texts()==['Total enrolled · includes known non-renewals\t4 / 36\t3 / 18','Chosen not to renew · excluded from expectations\t2 / 30\t1 / 10','Included in manager expectations\t2 / 6\t2 / 8']
 assert page.locator('#nonrenewal-accounts tbody tr').count()==3
 assert page.locator('#renewal-employer-lives tbody tr').count()==2
 assert page.locator('#growth-ranking tbody tr').count()==2
 assert page.locator('#retention-opportunity tbody tr').count()==2
 page.locator('[data-followup="Jordan"]').click();assert page.locator('.dialog tbody tr').count()==0;page.locator('#close').click()
 page.locator('[data-filter=renewalDecision]').select_option('expected')
 assert page.locator('#nonrenewal-accounts tbody tr').count()==3
 assert '4 / 36' in page.locator('#manager-enrollment-context tbody tr').first.inner_text()
 page.locator('[data-filter=manager]').select_option('Jordan')
 assert page.locator('#nonrenewal-accounts tbody tr').count()==1
 assert page.evaluate('managerStats(model()).denominator')==6
 assert '2 / 12' in page.locator('#manager-enrollment-context tbody tr').first.inner_text()
 page.locator('[data-filter=renewalDecision]').select_option('excluded')
 assert page.locator('#growth-ranking tbody tr').count()==0
 assert page.locator('#nonrenewal-accounts tbody tr').count()==1
 page.locator('#reset').click()
 page.evaluate("page='overview';render()")
 assert page.evaluate('model().now.filter(r=>match(r,model())).length')==3
 assert page.locator('.cards .num').first.inner_text()=='3'
 page.locator('[data-filter=renewalDecision]').select_option('expected');assert page.locator('.cards .num').first.inner_text()=='2'
 page.locator('#reset').click()
 page.evaluate("page='admin';render()")
 page.locator('[data-nonrenew="Leaving B"]').uncheck()
 assert page.evaluate('managerStats(model()).denominator')==16
 assert page.evaluate('managerStats(model()).rows.find(r=>r.name==="Jordan").current')==13
 page.locator('#role').select_option('Viewer');assert page.locator('[data-nonrenew]').count()==0
 page.evaluate("page='managers';render()")
 assert page.locator('#nonrenewal-accounts tbody tr').count()==2
 page.set_viewport_size({'width':390,'height':844});assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
 assert not errors,errors;b.close()
 print('PASS manager target/current/weighted exclusions, not-started and inactive groups, visible total context, manager and decision filters, company totals, restoration, viewer visibility and responsive layout')
server.shutdown()
