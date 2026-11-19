"""Employee-only carrier gains/losses, state origins, filters and accessible drilldowns."""
from pathlib import Path
import functools,http.server,threading
from playwright.sync_api import sync_playwright
root=Path(__file__).resolve().parents[1]/'app'
class Quiet(http.server.SimpleHTTPRequestHandler):
 def log_message(self,*args):pass
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(root)));threading.Thread(target=server.serve_forever,daemon=True).start()
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=b.new_page(viewport={'width':1440,'height':1100});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(f'http://127.0.0.1:{server.server_port}/core.html')
 page.evaluate('''()=>{
 const row=(email,carrier,state='NY',status='ENROLLED',group='Original')=>({group,email:email+'@example.test',carrier,state,status,name:'PRIVATE EMPLOYEE',phone:'PRIVATE PHONE',lives:50,effective:'01/01/2026',termination:status==='TERMINATED'?'08/01/2026':''});
 uploads.base=[...['a1','a2','a3','a4','a5'].map(e=>row(e,'Aetna')),row('b1','Beta','FL'),row('deleteb2','Beta'),row('b3','Beta'),row('c1','Cedar','TX'),row('c2','Cedar'),row('c3','Cedar'),row('u',''),row('t','Excluded','','TERMINATED'),{...row('d','Delta'),effective:'06/01/2026'}];
 uploads.current=[row('a1','Aetna'),row('a2','Beta','TX'),row('a3','Cedar'),row('a4','Beta','NY','TERMINATED'),row('a5',''),row('b1','Aetna','FL','APPLICATION_READY'),row('b2','Aetna','NY','PAYMENT_READY','Receiving'),row('b3','Beta'),row('c1','Aetna','TX','STUCK'),row('c2','Cedar'),row('c3','Beta',''),row('u','Aetna'),row('new','Aetna','NY','ENROLLED','New Employer'),row('t','Aetna'),row('d','Aetna')].map(r=>({...r,effective:'01/01/2027'}));
 assignment={Original:'Taylor',Receiving:'Jordan','New Employer':'Jordan'};parents={};nonRenewals={};filters={};mode='uploads';page='insights';render();
 }''')
 page.get_by_text('Carrier retention, movement & state breakdowns',exact=True).click()
 stats=page.evaluate('(()=>{const s=carrierMovementStats(model());return {kept:s.kept,switched:s.switched.length,missing:s.missing,rows:s.rows}})()');assert (stats['kept'],stats['switched'],stats['missing'])==(3,7,2),stats
 a=next(r for r in stats['rows'] if r['name']=='Aetna');assert a=={'name':'Aetna','gained':4,'lost':2,'net':2,'stayed':1,'current':8},a
 assert page.locator('#carrier-movement-summary tbody tr').first.locator('td').all_inner_texts()==['Aetna','1','4','2','+2']
 page.locator('#carrier-movement-summary [data-open-carrier=Aetna]').click();assert page.locator('.carrier-dialog .cards .num').all_inner_texts()==['4','2','+2','1']
 assert page.locator('#carrier-state-movement tbody tr').all_inner_texts()==['NY\t2\t1\t+1','TX\t1\t1\t0','FL\t1\t0\t+1'];assert page.locator('#carrier-state-movement tfoot td').all_inner_texts()==['4','2','+2']
 assert '@example.test' not in page.locator('.carrier-dialog').inner_text() and 'PRIVATE' not in page.locator('.carrier-dialog').inner_text()
 routes=page.locator('#carrier-switch-routes tbody tr').all_inner_texts();assert 'Aetna\tBeta\tNY\tTX\t1' in routes;assert 'Beta\tAetna\tNY\tNY\t1' in routes,'Canonical email transfer must count';assert sum(int(v) for v in page.locator('#carrier-switch-routes tbody td:last-child').all_inner_texts())==6
 page.locator('[data-carrier-direction=lost]').click();assert page.locator('#carrier-state-movement tfoot td').all_inner_texts()==['0','2','-2'];assert page.locator('.carrier-dialog .cards .num').all_inner_texts()==['4','2','+2','1']
 page.locator('[data-carrier-direction=gained]').click();assert page.locator('#carrier-state-movement tfoot td').all_inner_texts()==['4','0','+4'];assert page.locator('#carrier-switch-routes tbody tr').count()==4
 # Keyboard-accessible carrier buttons, including counterparty drilldowns.
 button=page.locator('#carrier-switch-routes [data-open-carrier=Delta]');button.focus();page.keyboard.press('Enter');assert page.locator('.carrier-dialog h1').text_content()=='Delta';assert page.locator('.carrier-dialog .cards .num').all_inner_texts()==['0','1','-1','0'];page.keyboard.press('Escape')
 # Carrier filtering includes both directions, so choosing Aetna does not hide its losses.
 page.locator('[data-filter=carrier]').select_option('Aetna');page.get_by_text('Carrier retention, movement & state breakdowns',exact=True).click();assert page.locator('#carrier-movement-summary tbody tr').count()==1
 assert page.locator('#carrier-movement-summary tbody td').all_inner_texts()==['Aetna','1','4','2','+2']
 page.locator('#carrier-share-table [data-open-carrier=Beta]').click();assert page.locator('.carrier-dialog .cards .num').all_inner_texts()==['2','2','0','1'],'Clicked carrier overrides carrier dropdown while retaining other filters';page.locator('#close').click()
 # Other filters use the current employee state and current account manager, including transfers.
 page.locator('[data-filter=state]').select_option('TX');page.get_by_text('Carrier retention, movement & state breakdowns',exact=True).click();assert page.locator('#carrier-movement-summary tbody td').all_inner_texts()==['Aetna','0','1','1','0']
 page.locator('#carrier-movement-summary [data-open-carrier=Aetna]').click();assert page.locator('#carrier-state-movement tbody tr').all_inner_texts()==['TX\t1\t1\t0'];page.locator('#close').click()
 page.locator('#reset').click();page.locator('[data-filter=manager]').select_option('Jordan');page.get_by_text('Carrier retention, movement & state breakdowns',exact=True).click();page.locator('#carrier-movement-summary [data-open-carrier=Aetna]').click();assert page.locator('.carrier-dialog .cards .num').all_inner_texts()==['1','0','+1','0'];page.locator('#close').click()
 page.locator('#reset').click();page.get_by_text('Carrier retention, movement & state breakdowns',exact=True).click();page.locator('#carrier-movement-summary [data-open-carrier=Beta]').click();assert 'Unknown' in page.locator('#carrier-state-movement').inner_text();page.locator('#close').click()
 page.locator('#role').select_option('Viewer');page.get_by_text('Carrier retention, movement & state breakdowns',exact=True).click();page.locator('#carrier-share-table [data-open-carrier=Aetna]').click();assert page.locator('.carrier-dialog').is_visible();assert page.locator('.carrier-dialog [id*=export]').count()==0
 page.locator('[data-carrier-direction=lost]').click();page.screenshot(path='/tmp/carrier-drilldown.png',full_page=True)
 for width in [1280,768,390]:
  page.set_viewport_size({'width':width,'height':1000});assert not page.evaluate('document.documentElement.scrollWidth>innerWidth');assert not page.locator('.carrier-dialog').evaluate('(el)=>el.scrollWidth>el.clientWidth+1')
 page.locator('#close').click();page.evaluate('uploads.current=null;render()');page.get_by_text('Carrier retention, movement & state breakdowns',exact=True).click();assert 'Upload the current report' in page.locator('#carrier-gains-losses').inner_text();page.locator('#carrier-share-table [data-open-carrier=Aetna]').click();assert 'Upload the current report' in page.locator('.carrier-dialog').inner_text();assert page.locator('.carrier-dialog .cards .num').all_inner_texts()==['—','—','—','—']
 assert not errors,errors;b.close()
server.shutdown()
print('PASS carrier switch gains/losses/net, state origin and current state, active baseline matching, transfers, unknown data exclusion, new employees/unreturned exclusions, filter semantics, keyboard, viewers, mobile and missing report states.')
