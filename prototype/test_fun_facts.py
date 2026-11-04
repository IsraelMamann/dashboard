from pathlib import Path
import http.server,threading,functools,csv,io,math,json,re
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parent
server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT)))
threading.Thread(target=server.serve_forever,daemon=True).start()
FIELDS=['company_name','employee_email','first_name','last_name','phone_number','enrollment_status','total_lives_on_plan','address_permanent_state','current_plan_carrier','plan_effective_date','termination_date','consent_granted_date','ichra_allotted','ichra_consumed','full_premium','level','age','ssn','birthday','dependent_1_first_name','dependent_1_ssn','address_permanent_street','address_permanent_city','address_permanent_zip','income','gender','smoker']
def record(email,er,premium,age,lives,tier,state='NY',status='ENROLLED',year=2026,allowance=None):
 return dict(company_name='Employer A' if state=='NY' else 'Employer B',employee_email=email,first_name='Test',last_name='Employee',phone_number='202-555-0100',enrollment_status=status,total_lives_on_plan=lives,address_permanent_state=state,current_plan_carrier='Aetna',plan_effective_date=f'01/01/{year}',termination_date='08/01/2026' if status=='TERMINATED' else '',consent_granted_date=f'11/01/{year-1} 3:00:00 PM',ichra_allotted=allowance,ichra_consumed=er,full_premium=premium,level=tier,age=age,ssn='SECRET-SSN-123',birthday='SECRET-BIRTHDAY-456',dependent_1_first_name='SECRET-CHILD-NAME',dependent_1_ssn='SECRET-CHILD-SSN',address_permanent_street='SECRET-STREET',address_permanent_city='SECRET-CITY',address_permanent_zip='SECRET-ZIP',income='SECRET-INCOME',gender='SECRET-UNUSED-GENDER',smoker='SECRET-UNUSED-SMOKER')
def csv_bytes(rows):
 out=io.StringIO();writer=csv.DictWriter(out,fieldnames=FIELDS);writer.writeheader();writer.writerows(rows);return out.getvalue().encode()
base=[record('a@example.com',100,400,20,1,'gold',allowance=150),record('b@example.com',300,800,40,3,'silver',state='TX',allowance=350),record('c@example.com',0,'','',2,'',status='TERMINATED',allowance=0),record('waived@example.com',9999,9999,99,9,'gold',status='WAIVED_COVERAGE',allowance=9999)]
current=[record('a@example.com',200,500,21,2,'gold',status='PAYMENT_READY',year=2027,allowance=250),record('b@example.com',400,900,41,4,'expanded bronze',state='TX',status='APPLICATION_READY',year=2027,allowance=450),record('new@example.com','',0,31,1,'unexpected',status='STUCK',year=2027,allowance='')]
allowed={'group','email','name','phone','status','lives','state','carrier','effective','termination','consent','erAllowance','erApplied','fullPremium','tier','age'}
embedded=json.loads(re.search(r'<script id="sample" type="application/json">(.*?)</script>',(ROOT/'index.html').read_text(),re.S)[1]);assert all(set(r)==allowed for r in embedded)
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);page=b.new_page(viewport={'width':1440,'height':1100});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(f'http://127.0.0.1:{server.server_port}/index.html');page.locator('[data-page=admin]').click()
 for key,rows in [('base',base),('current',current)]:
  page.locator(f'[data-upload={key}]').set_input_files({'name':key+'.csv','mimeType':'text/csv','buffer':csv_bytes(rows)})
  page.wait_for_function(f'uploads.{key} !== null')
 stored=page.evaluate('({base:uploads.base,current:uploads.current})');assert all(set(r)==allowed for rows in stored.values() for r in rows)
 assert 'SECRET-' not in json.dumps(stored)
 parsed=page.evaluate('(text)=>parseCSV(text)',csv_bytes(base).decode());assert 'SECRET-' not in json.dumps(parsed)
 assert stored['base'][0]['state']=='NY' and stored['base'][0]['age']==20
 print('Import allowlist discards SSNs, dependent data, full addresses, birth dates, income and unused fields; state and numeric age retained: passed')
 page.locator('[data-page=insights]').click();page.get_by_role('heading',name='Fun Facts',exact=True).wait_for();assert 'Fun Facts' in page.locator('[data-page=insights]').inner_text()
 def facts():return page.evaluate('funFactStats(model()).metrics')
 metrics=facts();expected=[(400/3,300),(600,1400/3),(30,31),(2,7/3)]
 for row,(a,c) in zip(metrics,expected):assert math.isclose(row['a']['value'],a) and math.isclose(row['b']['value'],c),(row,a,c)
 assert metrics[0]['a']['count']==3 and metrics[0]['b']['count']==2
 assert metrics[1]['a']['count']==2 and metrics[1]['b']['count']==3
 assert metrics[2]['a']['count']==2
 print('2026/2027 ER contribution, full premium, employee age and application size; valid zeroes count and blanks excluded: passed')
 tiers=page.evaluate('(()=>{let s=funFactStats(model());return [tierDistribution(s.before),tierDistribution(s.after)]})()')
 for dist in tiers:assert math.isclose(sum(r['percentage'] or 0 for r in dist),100)
 assert next(x for x in tiers[0] if x['key']=='unknown')['count']==1
 assert next(x for x in tiers[1] if x['key']=='expanded_bronze')['count']==1
 assert next(x for x in tiers[1] if x['key']=='unknown')['count']==1
 page.locator('#contribution-basis').select_option('allowance');metrics=facts();assert math.isclose(metrics[0]['a']['value'],500/3) and metrics[0]['b']['value']==350
 page.locator('#contribution-basis').select_option('applied');page.locator('[data-filter=state]').select_option('NY');metrics=facts();assert metrics[0]['a']['value']==50 and metrics[0]['b']['value']==200;assert metrics[2]['b']['value']==26
 print('Tier shares include unknowns and sum to 100%; contribution-basis switch and state filters recalculate averages: passed')
 page.locator('#mode').select_option('sample');assert page.get_by_text('Awaiting report',exact=True).count()>=4
 assert page.evaluate('funFactStats(model()).metrics[0].b.value') is None
 page.locator('#mode').select_option('demo');page.evaluate('window.scrollTo(0,0)');page.screenshot(path=str(ROOT/'fun-facts-preview.png'),full_page=True,animations='disabled')
 page.set_viewport_size({'width':390,'height':844});assert not page.evaluate('document.documentElement.scrollWidth>innerWidth')
 assert not errors,errors
 print('Sample-only state does not invent 2027 values, responsive layout and no browser errors: passed');b.close()
